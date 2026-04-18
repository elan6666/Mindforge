# 多Agent智能软件研发辅助平台

这是一个基于 `OpenHands` 二次开发的多 Agent 助手项目。当前仓库已经完成：

- Phase 1：`FastAPI` 入口、统一任务接口、`OpenHandsAdapter` 适配边界
- Phase 2：文件型 preset 模板中心、`/api/presets` 模式发现、preset-aware 的 `/api/tasks`
- Phase 3：`code-engineering` 模式下的角色实例化与串行调度
- Phase 4：本地仓库扫描、`Repo Summary` 生成与上下文注入

当前系统既保留“代码工程模式”主线，也加入了“论文修改模式”的模板占位，后续会在编排阶段补齐多 Agent 协作逻辑。

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
frontend/         # GUI extension placeholder
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

检查健康接口：

```powershell
Invoke-RestMethod -Method Get http://127.0.0.1:8000/api/health
```

查看可用 preset：

```powershell
Invoke-RestMethod -Method Get http://127.0.0.1:8000/api/presets
```

提交一个代码审查任务：

```powershell
$body = @{
  prompt = "Review the current backend structure."
  preset_mode = "code-review"
  repo_path = "E:\\CODE\\agent助手"
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
- `http`：当 `OPENHANDS_BASE_URL` 已配置时，转发到上游 HTTP 任务接口
- `disabled`：禁用适配层，接口返回明确错误

## Preset 行为

- 当 `preset_mode` 为空或未提供时，系统回退到 `default` 模板，并在响应 metadata 中标明 `used_default_preset = true`
- 当 `preset_mode` 明确给出但不存在时，接口返回 `400`，同时附带当前可用 preset 列表
- 当前只有 `code-engineering` 已接入真实串行多阶段编排；其余 preset 仍是单次执行链

## 后续重点

- Phase 5-7：模型路由、审批历史、GitHub 只读集成
- Phase 8：论文修改模式的标准分析、改写与审稿循环
