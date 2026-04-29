# Ops Agent

Ops Agent 是一个面向运维场景的 AI 助手控制台。它把资产管理、终端连接、AI 对话、命令审批和执行结果反馈整合到一个 Web 界面中，帮助运维人员在保留人工控制权的前提下，让 AI 参与排障、巡检和操作执行。

## 它解决什么问题

在日常运维中，工程师通常需要在资产台账、终端工具、知识经验和操作记录之间反复切换。Ops Agent 的目标是提供一个统一工作台：

1. 选择要操作的资产。
2. 打开对应终端，查看当前上下文。
3. 向 AI 描述目标或问题。
4. 由 AI 生成操作计划和建议命令。
5. 用户审批后执行命令。
6. 将输出结果回传给 AI，继续分析或生成下一步建议。

这不是一个完全自动化的运维机器人，而是一个以人工审批为边界的 AI 运维助手。

## 核心能力

### 资产统一管理

支持维护本地终端、Linux 主机和网络设备等资产信息。资产可以作为终端连接和助手对话的上下文，让 AI 的建议围绕具体对象展开。

### Web 终端工作台

在浏览器中为资产创建终端会话，支持本地 PTY、Linux SSH 和网络设备连接。终端输出可以作为助手分析上下文的一部分。

### AI 助手对话

助手可以基于资产信息、终端上下文和用户输入生成操作计划，解释每一步的目的、风险和预期结果，并在命令执行后继续分析输出。

### 命令审批闭环

命令默认不会直接执行，需要用户确认后才会下发。系统会记录计划、审批、命令、输出和执行结果，便于追踪操作过程。

### 模型配置

支持配置 Anthropic 或 OpenAI Compatible 模型，并选择默认模型用于助手对话。

### 会话内自动审批

支持为当前助手会话配置低风险命令的自动审批规则。自动审批只在当前会话内生效，高风险操作仍应由用户人工确认。

## 典型使用流程

```text
添加资产 → 打开终端 → 询问助手 → 查看计划 → 审批命令 → 执行命令 → 分析输出 → 继续下一步
```

示例场景：

- 登录一台 Linux 主机，排查服务异常。
- 查看网络设备状态，并让助手解释输出含义。
- 对重复性低风险检查命令启用会话内自动审批。
- 在一个任务中保留 AI 建议、人工审批和执行结果的完整记录。

完整产品工作流见 [docs/workflow.md](docs/workflow.md)。

## 界面模块

- **资产面板**：查看、创建和选择运维资产。
- **终端面板**：连接资产并执行交互式命令。
- **助手面板**：与 AI 对话，生成计划并分析输出。
- **设置面板**：配置模型分组、模型和默认模型。

## 安全原则

Ops Agent 的默认原则是用户保留最终控制权：

- 命令默认需要人工审批后才会执行。
- 自动审批规则只在当前助手会话内生效。
- 高风险命令不应仅凭 LLM 判断自动执行。
- 密码和 API Key 应脱敏展示，不能写入普通日志。
- 命令、审批、输出和执行结果需要可追踪。

## 技术组成

- 后端：Python、FastAPI、SQLModel、SQLite
- 前端：React、TypeScript、Vite、Tailwind CSS、xterm.js
- 连接能力：本地 PTY、SSH、网络设备连接器
- LLM：Anthropic、OpenAI Compatible

## 本地运行

### 1. 安装后端依赖

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

### 2. 启动后端 API

```bash
PYTHONPATH=src python -m app.main
```

默认监听 `127.0.0.1:8000`。可通过环境变量覆盖：

```bash
OPS_AGENT_HOST=127.0.0.1 OPS_AGENT_PORT=8000 PYTHONPATH=src python -m app.main
```

运行数据默认保存在用户目录下的 `.ops-agent` 目录中，包括 SQLite 数据库和设置文件。

### 3. 安装前端依赖

```bash
cd web
npm install
```

### 4. 配置前端环境变量

```bash
cp .env.example .env
```

常用配置：

```env
VITE_CONSOLE_DATA_SOURCE=api
VITE_API_BASE_URL=
```

`VITE_API_BASE_URL` 为空时，前端使用当前 origin 访问 API；开发时可以设置为后端地址，例如 `http://127.0.0.1:8000`。

### 5. 启动 Web 控制台

```bash
npm run dev
```

## 测试与构建

运行后端测试：

```bash
pytest
```

运行前端类型检查和构建：

```bash
cd web
npm run build
```

按当前系统打包发布文件：

```bash
python script/package.py
```

Windows 也可以使用 PowerShell 包装脚本：

```powershell
.\script\package.ps1
```

macOS/Linux 也可以使用 shell 包装脚本：

```bash
./script/package.sh
```

打包产物会输出到 `release/<system>/`，例如 `release/windows/ops-agent-windows-x64.zip` 或 `release/linux/ops-agent-linux-x64.tar.gz`。

## 项目结构

```text
src/app/              后端应用代码
src/app/api/          FastAPI 路由
src/app/core/         Agent、连接器、终端和命令执行核心逻辑
src/app/db/           数据模型、数据库会话和仓储函数
src/app/services/     业务服务
src/app/shared/       配置、枚举和共享 schema
tests/                Python 测试
web/                  React Web 控制台
docs/                 产品和工作流文档
```

## 当前状态

Ops Agent 目前是面向本地开发和功能验证的原型项目。生产使用前需要结合实际环境补充认证授权、审计策略、密钥管理、权限隔离和部署方案。
