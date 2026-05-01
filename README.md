<p align="center">
  <img src="assets/social-preview.png" alt="Mindforge social preview" width="100%" />
</p>

# Mindforge

> A multi-agent workspace for coding, research writing, model routing, and controllable task orchestration.

Mindforge is an open-source multi-agent assistant workspace. It gives users a web app for running role-based AI teams, managing model providers, routing tasks across models, reviewing execution history, and keeping human approval in the loop.

Mindforge is inspired by OpenHands-style agent architecture, but it focuses on the product orchestration layer: presets, role assignment, provider/model control, conversation threads, approval history, and task-specific workflows such as code engineering and academic paper revision.

## Highlights

- **Chat-first task workspace**: start a task like a normal conversation, continue with follow-up turns, and keep context inside one conversation thread.
- **Preset-based multi-agent teams**: instantiate workflows such as code engineering or paper revision, with different agents responsible for planning, backend, frontend, review, style, or content quality.
- **Model control center**: add your own providers and models, configure priority levels, disable models, and route different roles to different models.
- **OpenAI-compatible provider support**: use OpenAI-compatible endpoints, including custom providers and self-managed API keys.
- **Execution visibility**: inspect task history, orchestration stages, approvals, outputs, metadata, GitHub context, and attached files.
- **Human approval gates**: mark risky tasks for approval before execution.
- **Research and paper workflows**: support journal guidelines, reference papers, revision, reviewer-style feedback, and iterative improvement.

## Screenshots

Mindforge uses a web workspace with a chat composer, task configuration drawer, provider/model settings, rule templates, and task history.

```text
User request
   ↓
Preset + model routing
   ↓
Role-based agent orchestration
   ↓
Execution trace + review + history
   ↓
Follow-up conversation with context
```

## When To Use Mindforge

- You want AI agents to work as a configurable team instead of a single chatbot.
- You need different models for different roles, such as a coordinator, coder, reviewer, or writing editor.
- You want a web app that makes agent work inspectable: history, logs, approvals, outputs, and task metadata.
- You are building coding workflows, document workflows, or academic paper revision workflows.
- You want an OpenHands-inspired runtime boundary without locking the product layer to one execution backend.

## Architecture

Mindforge is intentionally split into a product layer and an execution boundary.

- **Frontend**: React + TypeScript workspace for conversations, task configuration, model management, templates, history, and approvals.
- **Backend**: FastAPI service for task submission, provider/model registry, orchestration, GitHub context, approval gates, and history persistence.
- **Runtime boundary**: `OpenHandsAdapter` keeps execution replaceable. The current modes support local mock execution, OpenAI-compatible model API calls, and an HTTP runtime bridge.
- **Persistence**: SQLite-backed task and conversation history for local development.

## Quick Start

### Backend

```powershell
python -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open:

- Frontend: `http://127.0.0.1:5173`
- Backend health check: `http://127.0.0.1:8000/api/health`

## Configuration

For local mock execution:

```powershell
$env:OPENHANDS_MODE = "mock"
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000/api"
```

For OpenAI-compatible model API execution:

```powershell
$env:OPENHANDS_MODE = "model-api"
$env:ARK_API_KEY = "your-local-secret"
```

Do not commit real API keys. Use environment variables or the local provider secret store.

## Verification

```powershell
python -m pytest

cd frontend
npm run test
npm run build
```

## Suggested GitHub Topics

`multi-agent`, `ai-agents`, `llm`, `agent-orchestration`, `developer-tools`, `coding-agent`, `openhands`, `model-routing`, `fastapi`, `react`, `typescript`, `openai-compatible`, `academic-writing`, `workflow-automation`

## Roadmap

- Real OpenHands runtime integration.
- Richer skills and repository instruction support.
- Safer long-running task recovery.
- More visual diff, approval, and execution review tools.
- Team/workspace sharing and deployment hardening.

## License

License information has not been finalized yet.

---

# Mindforge 中文说明

> 面向代码工程、论文修改、多模型路由和可控编排的多 Agent 工作台。

Mindforge 是一个开源多 Agent 助手工作台。它提供一个 Web App，让用户可以创建角色化 AI 团队、管理模型服务商、为不同 Agent 分配不同模型、查看执行历史，并在高风险任务前加入人工审批。

Mindforge 参考了 OpenHands 这类 Agent 系统的架构思路，但重点不是照搬底层运行时，而是构建产品编排层：预设模式、角色分工、模型路由、Provider/API 管理、连续对话、审批历史，以及代码工程和论文修改等场景化工作流。

## 主要能力

- **对话式任务工作台**：像聊天一样提交任务，也可以在同一个对话里连续追问，并保留上下文。
- **预设式多 Agent 团队**：例如代码工程、论文修改等模式，不同 Agent 负责规划、后端、前端、审查、文风或内容质量。
- **模型控制中心**：用户可以添加自己的模型和服务商，设置高/中/低/禁用优先级，并把不同角色路由到不同模型。
- **兼容 OpenAI 协议的 Provider**：支持自定义 OpenAI-compatible 接口和本地 API key 管理。
- **执行过程可观察**：查看任务历史、编排阶段、审批、输出、元数据、GitHub 上下文和附件信息。
- **人工审批机制**：高风险任务可以先进入审批，再继续执行。
- **论文修改工作流**：支持期刊投稿指南、参考论文、内容修改、审稿人式反馈和迭代润色。

## 适合谁使用

- 你希望 AI 不是单个聊天机器人，而是一个可配置的 Agent 团队。
- 你需要让不同角色使用不同模型，例如协调者、程序员、审查者、论文修改者。
- 你希望 Agent 的工作过程可追踪、可审查、可回看。
- 你在构建代码工程、文档整理、论文修改或研究辅助工作流。
- 你想参考 OpenHands 的架构方向，但保留自己的产品层和编排层。

## 架构概览

Mindforge 被拆成产品层和运行时边界。

- **前端**：React + TypeScript，用于对话、任务配置、模型管理、规则模板、历史和审批。
- **后端**：FastAPI，用于任务提交、模型注册、Provider 管理、多 Agent 编排、GitHub 上下文、审批和历史持久化。
- **运行时边界**：`OpenHandsAdapter` 保持底层执行可替换，目前支持 mock、本地模型 API 调用和 HTTP runtime bridge。
- **本地持久化**：使用 SQLite 保存任务和对话历史。

## 快速启动

### 后端

```powershell
python -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
```

### 前端

```powershell
cd frontend
npm install
npm run dev
```

访问：

- 前端：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8000/api/health`

## 配置

本地 mock 模式：

```powershell
$env:OPENHANDS_MODE = "mock"
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000/api"
```

调用 OpenAI-compatible 模型接口：

```powershell
$env:OPENHANDS_MODE = "model-api"
$env:ARK_API_KEY = "你的本地密钥"
```

不要把真实 API key 提交到仓库。请使用环境变量或本地 Provider secret 存储。

## 验证

```powershell
python -m pytest

cd frontend
npm run test
npm run build
```

## 建议的 GitHub Topics

`multi-agent`, `ai-agents`, `llm`, `agent-orchestration`, `developer-tools`, `coding-agent`, `openhands`, `model-routing`, `fastapi`, `react`, `typescript`, `openai-compatible`, `academic-writing`, `workflow-automation`

## 后续方向

- 接入真实 OpenHands runtime。
- 增强 skills 和 repository instructions。
- 强化长任务恢复和失败处理。
- 增加 diff、审批和执行审查工具。
- 支持团队协作、部署和生产化安全加固。

## License

许可证尚未最终确定。
