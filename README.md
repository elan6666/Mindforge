# Mindforge

这是一个参考 `OpenHands` 架构并预留其运行时适配边界的多 Agent 助手项目。当前阶段并不是直接嵌入 `OpenHands` 内核运行，而是在其上先搭建 `Mindforge` 自己的任务入口、preset 中心、编排层和后续 Web App 规划。当前仓库已经完成：

- Phase 1：`FastAPI` 入口、统一任务接口、`OpenHandsAdapter` 适配边界
- Phase 2：文件型 preset 模板中心、`/api/presets` 模式发现、preset-aware 的 `/api/tasks`
- Phase 3：`code-engineering` 模式下的角色实例化与串行调度
- Phase 4：本地仓库扫描、`Repo Summary` 生成与上下文注入
- Phase 5：provider/model registry、`/api/providers`、`/api/models`、执行时模型路由与 override
- Phase 6：Web App 工作台壳、会话历史、任务输入区、结果/轨迹面板、前后端联调
- Phase 7：模型中心、规则模板中心、协调模型选择与动态角色模型分配

当前系统既保留“代码工程模式”主线，也加入了“论文修改模式”的模板占位，后续会在编排阶段补齐多 Agent 协作逻辑。

## 当前与 OpenHands 的关系

当前项目与 `OpenHands` 的关系更准确地说是：

- 已参考其产品和架构方向，而不是从零定义整套 agent 产品形态
- 已预留独立的 `OpenHandsAdapter` 作为运行时适配边界
- 当前默认仍以 `mock` 演示链路为主，`http` 模式只是为后续真实上游集成预留接口
- `preset`、多阶段编排、仓库分析、模型中心和规则模板属于 `Mindforge` 自己的产品层

如果后续接入真实 `OpenHands` 服务，`Mindforge` 会继续保留自己的产品层，同时把更底层的执行能力逐步切到真实运行时。

## 当前内置 Presets

- `default`
- `code-engineering`
- `code-review`
- `doc-organize`
- `paper-revision`

## `paper-revision` 模式说明

`paper-revision` 用于论文修改场景，当前阶段只完成模板定义和发现，不执行真实多 Agent 编排。后续将围绕以下角色实现：

- `standards-editor`
  负责提取论文标准、结构要求和文风要点；如果是期刊论文，还会补充期刊官网投稿规范和同类论文风格摘要。
- `reviser`
  根据标准摘要、原文问题和审稿意见执行正文修改。
- `reviewer`
  以审稿人视角提出问题、风险点和修改建议，并驱动多轮修订。

## `code-engineering` 当前行为

从 Phase 3 开始，`code-engineering` 不再是单次 adapter 调用，而是固定走 4 个串行阶段：

1. `project-manager`
2. `backend`
3. `frontend`
4. `reviewer`

系统会在响应中返回：

- 最终汇总输出
- 每个阶段的原始输出
- 阶段摘要
- 当前执行策略、完成阶段数和失败阶段信息

如果传入 `repo_path`，系统还会在任务开始前做一次轻量仓库扫描，并把 `repo_analysis` 放入响应 metadata。

这条多阶段链路当前是 `Mindforge` 侧的 MVP 编排实现，目的是先验证角色分工和结果组织方式。后续阶段会尽量向 `OpenHands` 更成熟的 agent/state/action 抽象靠拢，而不是长期维护完全独立的轻量协议。

## `repo_analysis` 当前行为

Phase 4 增加了本地仓库分析，当前规则是轻量和可预测的：

- 扫描顶层目录
- 识别关键文件，如 `README.md`、`pyproject.toml`、`package.json`、`Dockerfile`
- 识别可能的入口文件，如 `main.py`、`app.py`、`index.tsx`
- 推断技术栈并生成简短 `Repo Summary`

降级策略如下：

- 没传 `repo_path`：`status=skipped`
- 路径不存在或不可解析：`status=failed`
- 扫描成功：`status=analyzed`

无论哪种情况，主任务链都不会因为仓库分析失败而直接中断。

当前这套仓库分析是刻意保持轻量的产品层能力。后续如果引入 `skills`、仓库私有 instructions 或更完整的 workspace context，会在这套基础上继续合并，而不是推倒重做。

## 项目结构

```text
app/backend/
├── api/          # HTTP routes
├── core/         # settings and logging
├── integration/  # OpenHands adapter boundary
├── schemas/      # request and response models
├── services/     # task orchestration and preset loading
└── storage/      # placeholder for future persistence

app/presets/      # YAML preset templates
frontend/         # React + Vite Web App workspace shell
scripts/          # local demo helpers
```

## 本地启动

安装依赖：

```powershell
python -m pip install -e .
```

启动本地演示服务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local_demo.ps1
```

启动前端工作台：

```powershell
cd .\frontend
npm install
npm run dev
```

前端默认地址：

```text
http://127.0.0.1:5173
```

检查健康接口：

```powershell
Invoke-RestMethod -Method Get http://127.0.0.1:8000/api/health
```

查看可用 preset：

```powershell
Invoke-RestMethod -Method Get http://127.0.0.1:8000/api/presets
```

查看可用 provider：

```powershell
Invoke-RestMethod -Method Get http://127.0.0.1:8000/api/providers
```

查看可用 model：

```powershell
Invoke-RestMethod -Method Get http://127.0.0.1:8000/api/models
```

查看可编辑模型控制状态：

```powershell
Invoke-RestMethod -Method Get http://127.0.0.1:8000/api/control/models
```

查看规则模板：

```powershell
Invoke-RestMethod -Method Get http://127.0.0.1:8000/api/control/rule-templates
```

提交一个代码审查任务：

```powershell
$body = @{
  prompt = "Review the current backend structure."
  preset_mode = "code-review"
  repo_path = "E:\\CODE\\Mindforge"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/tasks `
  -ContentType "application/json" `
  -Body $body
```

提交一个论文修改任务：

```powershell
$body = @{
  prompt = "Revise this journal paper abstract to match a formal academic tone."
  preset_mode = "paper-revision"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/tasks `
  -ContentType "application/json" `
  -Body $body
```

## OpenHands Adapter Modes

通过环境变量 `OPENHANDS_MODE` 控制适配器模式：

- `mock`：默认模式，用于本地演示
- `http`：当 `OPENHANDS_BASE_URL` 已配置时，转发到上游 HTTP 任务接口；后续会逐步向真实 `OpenHands` 服务契约收敛
- `disabled`：禁用适配层，接口返回明确错误

## Phase 5 模型路由

当前后端已经提供文件型 model registry，并支持：

- provider 查询：`GET /api/providers`
- model 查询：`GET /api/models`
- 单次任务默认模型选择
- `code-engineering` 多阶段 role 级模型选择
- 显式 override：
  - `model_override`
  - `role_model_overrides`

当前默认优先级顺序为：

1. 显式 override
2. role 默认
3. `task_type` 默认
4. `preset_mode` 默认
5. global 默认
6. priority fallback

## Phase 7 模型中心与规则模板

当前系统已经支持：

- 前端模型中心：调整模型优先级 `high / medium / low / disabled`
- 前端规则模板中心：按 `preset_mode`、职责和模型创建结构化模板
- 后端协调模型选择：根据显式模板或 prompt/preset/task type 命中模板
- 执行元数据回写：
  - `rule_template_selection`
  - `effective_role_model_overrides`

当前模板和模型可编辑状态使用本地配置文件持久化：

- `app/model_control/model_overrides.json`
- `app/model_control/rule_templates.json`

## Preset 行为

- 当 `preset_mode` 为空或未提供时，系统回退到 `default` 模板，并在响应 metadata 中标明 `used_default_preset = true`
- 当 `preset_mode` 明确给出但不存在时，接口返回 `400`，同时附带当前可用 preset 列表
- 当前只有 `code-engineering` 已接入真实串行多阶段编排；其余 preset 仍是单次执行链

## 后续重点

- Phase 8-9：审批历史、GitHub 只读集成
- Phase 10：论文修改模式的标准分析、改写与审稿循环
## Phase 8 审批与历史

当前系统已经支持：

- 高风险任务进入 `pending_approval`，并在当前工作台内批准或拒绝
- `SQLite` 持久化 `task_run / stage_run / approval`
- 审批接口：
  - `GET /api/approvals/pending`
  - `POST /api/approvals/{task_id}/approve`
  - `POST /api/approvals/{task_id}/reject`
- 历史接口：
  - `GET /api/history/tasks`
  - `GET /api/history/tasks/{task_id}`
- 前端工作台历史列表、状态筛选、详情面板和审批标签页

当前审批触发规则保持轻量：

- 只在请求 metadata 中出现高风险信号时触发，例如：
  - `requires_approval = true`
  - `approval_actions`
  - `high_risk_actions`
  - `execution_mode = write/shell/batch-write`
- 普通只读分析和默认 mock 链路不会自动拦截

后续重点：

- Phase 9：GitHub 只读集成与结果展示增强
- Phase 10：论文修改模式的标准分析、改写与审稿循环
