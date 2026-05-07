# 会话模型移除与状态转移设计

## 背景

当前系统同时存在数据库侧 Assistant/Terminal session 概念与运行时终端连接状态，造成职责重复：

- [`src/app/db/repositories/assistant.py`](src/app/db/repositories/assistant.py) 维护 assistant session 记录。
- [`src/app/db/repositories/terminal.py`](src/app/db/repositories/terminal.py) 暴露 terminal session / output event 查询接口，但当前实现已接近占位。
- [`src/app/core/engine/task_orchestrator.py`](src/app/core/engine/task_orchestrator.py) 仍把任务运行依赖绑定到数据库 session 记录与 terminal session 查询。
- [`src/app/services/terminal_service.py`](src/app/services/terminal_service.py) 已经实际承担终端连接生命周期管理，但未成为唯一事实来源。

本次重构目标是移除数据库中的会话模型与其后端依赖，将会话状态收敛到前端或后端内存，同时保留任务、审批、执行审计能力。

## 目标

1. 删除数据库中的 AssistantSession / TerminalSession 相关模型语义与仓储依赖。
2. 保留 [`src/app/api/terminal.py`](src/app/api/terminal.py) 的 open / ws / close 能力，但其状态仅存在于内存。
3. 前端持有 `conversationId`、`terminalId`、消息列表等 UI 会话态。
4. 后端任务编排不再依赖数据库会话恢复，而是直接依赖运行中的内存终端连接。
5. 本轮直接完成数据库字段重命名，避免继续保留 `session_id` / `terminal_session_id` 之类命名。

## 非目标

1. 不补测试文件。
2. 不保留数据库会话兼容层。
3. 不新增额外的持久化会话恢复机制。

## 设计决策

### 1. 状态边界

后端仅保留两类状态：

- 持久化状态：任务、步骤、审批、执行、模型使用等审计信息。
- 内存状态：terminal 连接实例、terminal 输出缓冲、短生命周期运行上下文。

前端保留两类状态：

- 当前 UI 会话状态：`conversationId`、`terminalId`、消息流、当前资产、待审批 `runId`。
- 可在刷新后丢失的临时视图状态。

### 2. terminal service 成为唯一事实来源

[`src/app/services/terminal_service.py`](src/app/services/terminal_service.py) 成为 terminal 连接与输出的唯一状态源：

- `open_session()` 生成内存态 `terminalId`。
- `stream_session()` 负责 websocket 双向转发。
- `close_session()` 负责销毁连接。
- 新增内存输出缓冲能力，用于替代数据库 terminal event 轮询。
- [`src/app/core/engine/task_orchestrator.py`](src/app/core/engine/task_orchestrator.py) 通过 service 直接读取 recent output，并在命令执行阶段从内存缓冲收集增量输出。

### 3. 去除数据库会话概念

删除或停止使用以下职责：

- [`src/app/db/repositories/assistant.py`](src/app/db/repositories/assistant.py)
- [`src/app/db/repositories/terminal.py`](src/app/db/repositories/terminal.py)
- [`src/app/api/schemas.py`](src/app/api/schemas.py) 中的 `AssistantSessionView`、`TerminalSessionSummaryView`、`AssetContextView.assistant_sessions`、`AssetContextView.terminal_session`

[`src/app/core/engine/task_orchestrator.py`](src/app/core/engine/task_orchestrator.py) 不再：

- 调用 `get_or_create_assistant_session()`
- 调用 `_find_terminal_session_id()`
- 调用数据库 output event 查询接口
- 基于数据库记录尝试恢复 terminal session

## 数据库与命名重构

本轮直接重命名数据库字段，不保留旧命名：

- task 表中的 `session_id` -> `conversation_id`
- task 表中的 `terminal_session_id` -> `terminal_id`
- approval 表中的 `terminal_session_id` -> `terminal_id`
- command execution 表中的 `terminal_session_id` -> `terminal_id`
- 其他表/视图/DTO 中所有 `session_id`，若语义为会话上下文，统一改为 `conversation_id`
- 若语义为 terminal 连接标识，统一改为 `terminal_id`

对应影响范围：

- [`database/schema.sql`](database/schema.sql)
- [`src/app/db/models.py`](src/app/db/models.py)
- [`src/app/db/repositories/tasks.py`](src/app/db/repositories/tasks.py)
- [`src/app/api/schemas.py`](src/app/api/schemas.py)
- [`web/src/types/api.ts`](web/src/types/api.ts)
- [`web/src/types/ops.ts`](web/src/types/ops.ts)

## 后端改动方案

### 1. 编排器

[`src/app/core/engine/task_orchestrator.py`](src/app/core/engine/task_orchestrator.py) 调整为：

- `stream_run()` 从请求参数或调用上下文接收当前 `terminalId`。
- 创建任务时直接写入 `conversation_id` 与 `terminal_id`。
- recent output 通过 [`TerminalService.read_recent_output()`](src/app/services/terminal_service.py:121) 获取。
- 审批执行阶段通过 [`TerminalService.send_input()`](src/app/services/terminal_service.py:115) 发命令。
- 命令输出收集改为从 terminal service 的内存 ring buffer 增量读取。
- 若 `terminalId` 对应连接不存在，则直接失败返回，不再自动数据库恢复。

### 2. terminal service

[`src/app/services/terminal_service.py`](src/app/services/terminal_service.py) 新增：

- 每个 `terminalId` 对应输出 ring buffer。
- buffer sequence / cursor 机制，供 orchestrator 读取增量输出。
- websocket 输出时同步写入 buffer。
- `close_session()` 时清理连接与缓冲。

### 3. API schema

[`src/app/api/schemas.py`](src/app/api/schemas.py) 中：

- 删除 assistant / terminal session summary 相关 view。
- `ChatRunResponse.session_id` 改为 `conversation_id`。
- `TaskDetailView.session_id` 改为 `conversation_id`。
- `TaskDetailView.terminal_session_id` 改为 `terminal_id`。
- `ApprovalRecordView.terminal_session_id` 改为 `terminal_id`。
- `CommandExecutionView.terminal_session_id` 改为 `terminal_id`。
- 其他带 `session_id` 的 API 结构按语义统一重命名。

### 4. terminal API

[`src/app/api/terminal.py`](src/app/api/terminal.py) 保留：

- `POST /api/terminal/sessions`
- `WS /api/terminal/sessions/{terminal_session_id}/ws`
- `DELETE /api/terminal/sessions/{terminal_session_id}`

但其语义调整为“内存 terminal 连接 API”，后续代码层建议逐步将变量名从 `terminal_session_id` 收敛为 `terminal_id`。

## 前端改动方案

前端统一负责持有会话态：

- 当前 `conversationId`
- 当前 `terminalId`
- 当前消息列表
- 当前审批中的 `runId`

主要改动位置：

- [`web/src/hooks/useConsoleData.ts`](web/src/hooks/useConsoleData.ts)
- [`web/src/components/assistant/AssistantPanel.tsx`](web/src/components/assistant/AssistantPanel.tsx)
- [`web/src/components/assistant/ConversationView.tsx`](web/src/components/assistant/ConversationView.tsx)
- [`web/src/components/terminal/TerminalHeader.tsx`](web/src/components/terminal/TerminalHeader.tsx)
- [`web/src/api/terminal.ts`](web/src/api/terminal.ts)
- [`web/src/api/console.ts`](web/src/api/console.ts)

前端请求后端时显式传递 `conversationId` 与 `terminalId`，不再依赖后端从数据库推断当前会话。

## 落地顺序

1. 修改 [`database/schema.sql`](database/schema.sql) 与 [`src/app/db/models.py`](src/app/db/models.py) 完成字段重命名。
2. 修改 [`src/app/db/repositories/tasks.py`](src/app/db/repositories/tasks.py) 与相关持久化调用。
3. 删除 [`src/app/db/repositories/assistant.py`](src/app/db/repositories/assistant.py) / [`src/app/db/repositories/terminal.py`](src/app/db/repositories/terminal.py) 的会话职责。
4. 重构 [`src/app/services/terminal_service.py`](src/app/services/terminal_service.py) 输出缓冲与内存态读取接口。
5. 重构 [`src/app/core/engine/task_orchestrator.py`](src/app/core/engine/task_orchestrator.py) 以 terminal service 为唯一依赖。
6. 调整 [`src/app/api/schemas.py`](src/app/api/schemas.py) 与 API 层命名。
7. 调整前端类型、API 封装与组件消费。

## 风险与处理

### 1. 页面刷新后 terminal 丢失

这是设计接受的结果。terminal 连接是内存态，刷新后若连接不存在，前端应重新 open。

### 2. 编排执行中 terminal 失效

本轮不再自动恢复，直接返回明确错误，让前端重新建立 terminal 并重新发起运行。

### 3. 数据库重命名波及面大

通过先统一模型与 repository，再收敛 API schema 与前端类型，降低编译错误排查成本。

## 实施完成判定

满足以下条件即视为完成：

1. 代码中不再存在 AssistantSession / TerminalSession 数据库模型依赖。
2. 后端任务编排不再通过数据库查找或恢复 terminal session。
3. terminal 输出采集完全来自 [`src/app/services/terminal_service.py`](src/app/services/terminal_service.py) 内存缓冲。
4. API 与前端类型中不再暴露旧 `session_id` / `terminal_session_id` 命名。
5. open / ws / close terminal API 仍可工作。
