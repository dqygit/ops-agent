# Ops Agent

Ops Agent 是一个面向运维场景的本地桌面应用原型，用于把资产管理、终端会话、AI 任务规划、审批流和执行结果汇总放到同一个界面中。

当前项目基于 Python、PySide6 和 SQLModel 构建，适合用于 Linux 主机与华为网络设备的巡检、命令执行辅助和会话留痕。

## 功能概览

- 资产管理：新增、编辑、删除运维资产
- 终端会话：为选中的资产建立终端连接并记录事件
- 上下文附加：可将终端选中文本附加给 AI 会话
- AI 任务运行：基于输入生成计划、逐步执行并汇总结果
- 审批流：任务执行前进入审批状态，可批准或拒绝
- 历史会话：按资产查看并重新打开历史助手会话
- 本地持久化：将资产、消息、任务、审批、终端事件保存到 SQLite
- 模型切换：支持 Anthropic 与 OpenAI Compatible 提供方

## 界面结构

应用主界面由三个主要面板组成：

- **Resource Explorer**：管理资产与查看历史会话
- **Terminal Session**：展示当前资产的连接状态和终端输出
- **AI Workspace**：输入任务、查看计划、处理审批与阅读最终结果

入口位于 [src/app/main.py](src/app/main.py)。主窗口定义位于 [src/app/ui/main_window.py](src/app/ui/main_window.py)。

## 技术栈

- Python 3.13
- PySide6
- SQLModel / SQLAlchemy
- Pydantic v2
- Anthropic SDK
- OpenAI SDK
- Netmiko / Paramiko
- pytest
- PyInstaller

## 目录结构

```text
ops-agent/
├─ src/app/
│  ├─ core/                  # 任务规划、运行时、连接器、终端上下文、安全控制
│  ├─ db/                    # 数据模型、仓储、数据库初始化
│  ├─ integrations/llm/      # LLM 抽象、工厂和 provider 实现
│  ├─ services/              # 资产、消息、任务、模型、终端等服务
│  ├─ shared/                # 配置、枚举、共享 schema
│  ├─ ui/                    # 主窗口、资产面板、聊天面板、终端面板、设置对话框
│  └─ main.py                # 应用入口
├─ tests/                    # 单元测试与 UI 流程测试
├─ requirements.txt          # Python 依赖
├─ pytest.ini                # pytest 配置
├─ pyrightconfig.json        # Pyright 配置
└─ main.spec                 # PyInstaller 打包配置
```

## 运行要求

建议环境：

- Python 3.13
- Windows 11 或 Linux
- 可用的图形界面环境

项目的类型检查配置在 [pyrightconfig.json](pyrightconfig.json) 中声明 Python 版本为 3.13。

## 安装依赖

先创建虚拟环境，再安装依赖。

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS / Linux / Git Bash

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 启动方式

### 按模块启动

```bash
PYTHONPATH=src python -m app.main
```

Windows PowerShell：

```powershell
$env:PYTHONPATH = "src"
python -m app.main
```

### 直接运行入口文件

```bash
python src/app/main.py
```

应用启动时会创建本地数据目录并初始化数据库，相关逻辑位于 [src/app/main.py:350-356](src/app/main.py#L350-L356)。

## 数据与配置文件

应用数据目录位于：

```text
~/.ops-agent/
```

当前代码中使用的主要路径定义在 [src/app/shared/config.py](src/app/shared/config.py)：

- `~/.ops-agent/ops_agent.db`：主 SQLite 数据库
- `~/.ops-agent/settings.json`：模型设置文件
- `~/.ops-agent/ops_agent.test.db`：测试数据库路径常量

## 模型配置

模型设置由 [src/app/services/model_service.py](src/app/services/model_service.py) 管理。

默认配置：

- Provider：`anthropic`
- Model：`claude-opus-4-7`
- Base URL：`https://api.anthropic.com`
- API Key：未配置时回退到 `demo-key`
- Temperature：`0.2`
- Max tokens：`256`

当前支持的 provider：

- `anthropic`
- `openai_compatible`

当前内置的模型列表：

- Anthropic：`claude-opus-4-7`、`claude-sonnet-4-6`
- OpenAI Compatible：`gpt-5.5`、`gpt-5.4`

### 环境变量

Anthropic 默认配置会读取：

- `ANTHROPIC_API_KEY`
- `ANTHROPIC_BASE_URL`

资产密文解密会读取：

- `OPS_AGENT_SECRET_KEY`

示例：

```bash
export ANTHROPIC_API_KEY="your-api-key"
export OPS_AGENT_SECRET_KEY="replace-with-a-strong-secret"
```

Windows PowerShell：

```powershell
$env:ANTHROPIC_API_KEY = "your-api-key"
$env:OPS_AGENT_SECRET_KEY = "replace-with-a-strong-secret"
```

### 应用内设置

应用包含设置对话框，可在界面中编辑：

- Provider
- Model
- Base URL
- API Key

相关逻辑见 [src/app/ui/settings_dialog.py](src/app/ui/settings_dialog.py) 和 [src/app/services/model_service.py](src/app/services/model_service.py)。

## 资产类型与连接行为

当前定义的资产类型位于 [src/app/shared/enums.py](src/app/shared/enums.py)：

- `linux`
- `huawei`

连接行为定义在 [src/app/main.py:62-90](src/app/main.py#L62-L90)：

- `linux` 资产使用 `ServerConnector`
- `huawei` 资产使用 `NetworkConnector`
- 当资产没有凭据时，回退到 `DemoConnector`，便于演示和 UI 测试

## 核心模块

### 1. Agent Runtime

- [src/app/core/agent/planner.py](src/app/core/agent/planner.py)
- [src/app/core/agent/runtime.py](src/app/core/agent/runtime.py)

负责计划生成、步骤执行、事件流转和最终摘要。

### 2. Connectors

- [src/app/core/connectors/server.py](src/app/core/connectors/server.py)
- [src/app/core/connectors/network.py](src/app/core/connectors/network.py)

负责不同资产类型的连接封装。

### 3. Executor 与安全控制

- [src/app/core/executor/command_catalog.py](src/app/core/executor/command_catalog.py)
- [src/app/core/executor/safety_guard.py](src/app/core/executor/safety_guard.py)
- [src/app/core/executor/command_executor.py](src/app/core/executor/command_executor.py)

负责命令目录、执行流程与安全检查。

### 4. Services

- [src/app/services/asset_service.py](src/app/services/asset_service.py)
- [src/app/services/chat_service.py](src/app/services/chat_service.py)
- [src/app/services/task_service.py](src/app/services/task_service.py)
- [src/app/services/terminal_service.py](src/app/services/terminal_service.py)

负责资产、会话、消息、任务、终端和模型配置等业务逻辑。

### 5. UI

- [src/app/ui/asset_panel.py](src/app/ui/asset_panel.py)
- [src/app/ui/terminal_panel.py](src/app/ui/terminal_panel.py)
- [src/app/ui/chat_panel.py](src/app/ui/chat_panel.py)

负责桌面界面与交互流程。

## 开发

### 运行测试

```bash
pytest
```

[pytest.ini](pytest.ini) 已配置：

```ini
[pytest]
pythonpath = src
```

通常可以直接在仓库根目录运行测试。

### 类型检查

```bash
pyright
```

### 当前测试覆盖

从现有测试文件看，覆盖点主要包括：

- 任务规划与运行时
- 安全规则与命令目录
- 任务、模型、终端等服务层
- 聊天流程与 UI 主流程
- 主程序初始化与事件联动

## 打包

仓库包含 [main.spec](main.spec)，可使用 PyInstaller 打包：

```bash
pyinstaller main.spec
```

当前 spec 以 `src/app/main.py` 为入口，生成名为 `main` 的产物，且 `console=True`。

## 当前状态

从代码结构和测试覆盖来看，这个项目更接近一个**可运行的桌面原型**，已经具备：

- 完整的 UI 骨架
- 本地数据库持久化
- 资产与会话管理
- AI 任务规划与审批流
- 基础连接器与模型配置
- 一批围绕核心流程的自动化测试

如果要进一步走向生产化，通常还需要继续补强：

- 真实设备接入验证
- 更严格的命令白名单与安全策略
- 更完整的日志、审计和异常处理
- 安装分发与升级机制
- 更明确的部署与配置管理方案

## 许可证

仓库当前未包含明确的 License 文件。

如果计划开源，建议补充 `LICENSE` 并在 README 中说明授权方式。
