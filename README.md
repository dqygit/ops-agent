<div align="center">

# Ops Agent — 面向运维场景的 AI 助手控制台
[功能特性](#-功能特性) · [快速开始](#-快速开始) · [开发指南](#-开发指南) · [构建发布](#-构建与发布) · [文档](#-文档)

</div>

---

Ops Agent 把日常运维中分散在资产台账、终端工具、知识经验与执行记录之间的工作流，整合到一个统一的工作台。AI 提供建议，用户保留最终控制权。

支持 **Web** 与 **桌面端（Tauri）** 两种运行形态，适合本地开发验证与运维流程演练。

```text
选择资产  →  连接终端  →  AI 生成计划  →  人工审批  →  执行回传  →  继续迭代
```

## ✨ 功能特性

- **资产统一管理** — 维护本地终端、Linux 主机、网络设备等资产清单。
- **Web 终端工作台** — 支持本地 PTY、SSH 与网络设备连接，基于 xterm.js。
- **AI 助手对话** — 结合资产与终端上下文生成计划、解释输出、迭代排障。
- **命令审批闭环** — 命令默认需人工确认后执行，全程可追踪。
- **多模型接入** — 支持 Anthropic 与 OpenAI Compatible 协议。
- **跨平台桌面端** — 基于 Tauri 2 的 macOS / Linux / Windows 客户端。

> [!NOTE]
> 设计原则：AI 提供建议，用户保留最终控制权。所有破坏性操作均需人工审批。

## 🧱 技术栈

| 分层 | 技术选型 |
| --- | --- |
| 后端 | Python 3.11 · FastAPI · SQLModel · Uvicorn · SQLite |
| 前端 | React 18 · TypeScript 5 · Vite 5 · Tailwind CSS 3 · xterm.js |
| 桌面端 | Tauri 2 · Rust |
| 包管理 | pip（后端） · pnpm（前端） |

## 🚀 快速开始

### 前置要求

- Python **3.11+**
- Node.js **20+**，pnpm **10+**
- Rust toolchain（仅桌面端构建需要）

### 安装与启动

```bash
# 1. 后端依赖
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. 前端依赖
cd web && pnpm install && cd ..

# 3. 一键启动后端 + 前端
./run.sh
```

启动后访问 `http://localhost:5173`，后端默认监听 `127.0.0.1:8000`。

<details>
<summary>分别启动后端与前端</summary>

```bash
# 后端
PYTHONPATH=src python -m app.main

# 前端
cd web && pnpm dev
```

可通过环境变量覆盖后端监听地址：

```bash
OPS_AGENT_HOST=127.0.0.1 OPS_AGENT_PORT=8000 OPS_AGENT_RELOAD=true \
  PYTHONPATH=src python -m app.main
```

</details>

## 🛠 开发指南

```bash
# 后端测试
pytest

# 前端类型检查 + 生产构建
cd web && pnpm build

# 桌面开发（Tauri）
cd web && pnpm tauri:dev
```

### 目录结构

```text
.
├── src/app/                 # Python 后端
│   ├── api/                 # FastAPI 路由
│   ├── core/                # 终端 / 连接器 / 执行引擎
│   ├── db/                  # 数据模型与仓储
│   ├── integrations/        # LLM / Prompt / Tool 集成
│   ├── services/            # 业务服务层
│   └── shared/              # 配置与共享类型
├── web/                     # React + Vite 前端
│   └── src-tauri/           # Tauri 桌面端工程
├── scripts/                 # 后端二进制与桌面打包脚本
├── docs/                    # 设计与流程文档
└── run.sh                   # 本地联调启动脚本
```

## 📦 构建与发布

### 本地构建桌面包

```bash
./scripts/build_desktop_bundle.sh            # 当前平台
./scripts/build_desktop_bundle.sh macos      # 显式指定
./scripts/build_desktop_bundle.sh linux
./scripts/build_desktop_bundle.sh windows
```

脚本依次执行：安装 Python 依赖与 `pyinstaller` → 构建后端二进制 → `pnpm tauri:build`。

### GitHub Actions 发布

工作流文件：[`.github/workflows/desktop-release.yml`](.github/workflows/desktop-release.yml)

- **触发方式**：手动触发（`workflow_dispatch`）
- **构建平台**：macOS / Linux / Windows
- **自动发布**：推送形如 `v*` 的 tag 时，创建 GitHub Release 并上传产物

## ❓ 常见问题

> [!TIP]
> **前端无法访问后端接口** — 确认后端已运行在 `127.0.0.1:8000`，并检查前端环境变量 `VITE_API_BASE_URL`（留空时使用当前 origin）。

> [!TIP]
> **`pnpm tauri:build` 失败** — 检查 Rust toolchain 是否安装；Linux 需安装 `webkit2gtk` / `gtk` 等系统库；CI 中需配置 `TAURI_*` 与 Apple / Windows 签名相关环境变量。

> [!TIP]
> **启动脚本端口冲突** — `run.sh` 会尝试清理 `8000` 与 `5173` 端口；若仍冲突请手动排查占用进程。

## 📚 文档

- [工作流说明](docs/workflow.md)
