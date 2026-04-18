# Phase 2: Preset Template Center - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning
**Source:** Direct planning without discuss-phase. Defaults chosen from prior recommendations because the user explicitly invoked plan-phase.

<domain>
## Phase Boundary

本阶段只交付模板中心和预设模式入口：定义模板数据结构、默认模板配置、模板加载机制，以及基于现有 `preset_mode` 字段的模式选择入口。真实多 Agent 实例化、串行调度、仓库分析、模型路由和审批历史不在本阶段实现。

</domain>

<decisions>
## Implementation Decisions

### 模板存储
- **D-01:** Phase 2 采用文件配置优先，默认模板以 `YAML` 文件形式存放，不引入数据库持久化。
- **D-02:** 默认模板至少覆盖 `code-engineering`、`code-review`、`doc-organize` 和 `default`。

### 模板挂载位置
- **D-03:** 模板文件放在独立的 `app/presets` 或等价目录中，不写死在 `TaskService` 里。
- **D-04:** 后端通过独立 loader/service 读取模板，再交给任务服务消费。

### 预设模式入口
- **D-05:** 沿用现有 `TaskRequest.preset_mode` 作为模式入口，不新增复杂提交接口。
- **D-06:** Phase 2 可以增加一个轻量级 preset discovery 入口，例如列出可用预设，但不做 GUI 页面。

### 边界控制
- **D-07:** Phase 2 只解析模板和返回模板元信息，不做角色实例化执行。
- **D-08:** 模板字段至少包括 `preset_mode`、`agent_roles`、`execution_flow`、`default_models`、`requires_repo_analysis`、`requires_approval`。

### 异常与回退策略
- **D-09:** 当 `preset_mode` 为空时，系统回退到 `default` 模板，并在响应元信息中说明。
- **D-10:** 当 `preset_mode` 明确给出但不存在时，返回结构化错误，而不是静默回退。

### the agent's Discretion
- YAML 文件是否按单文件一模板还是多模板聚合
- loader/service 的具体模块命名
- preset discovery 接口的返回字段细节

</decisions>

<specifics>
## Specific Ideas

- 模板中心要与当前 `TaskService` 兼容，不能把现有 Phase 1 接口推翻重来。
- Phase 2 的主要输出是“可被消费的模板对象”，而不是“已经执行的多 Agent 流程”。
- 预设模式应该能在 API 层直接被观察到，方便后续前端和 CLI 复用。

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning Baseline
- `.planning/PROJECT.md` - 项目定位、技术基线和当前状态
- `.planning/REQUIREMENTS.md` - `PRESET-*` 需求和 Traceability
- `.planning/ROADMAP.md` - Phase 2 目标、成功标准和计划占位
- `.planning/STATE.md` - 当前项目状态和 Phase 1 已完成基础

### Existing Phase Output
- `.planning/phases/01-openhands-foundation/01-VERIFICATION.md` - Phase 1 已验证完成的基础能力
- `app/backend/schemas/task.py` - 现有 `preset_mode` 字段定义
- `app/backend/services/task_service.py` - 当前任务提交服务入口
- `app/backend/integration/openhands_adapter.py` - 后续模板消费的适配边界

### Design Background
- `output/doc/多Agent智能软件研发辅助平台_概要设计说明书_OpenHands版.docx` - 模板中心与模式化协作的整体背景
- `output/doc/多Agent智能软件研发辅助平台_详细设计说明书_OpenHands版.docx` - 模板对象和后续 Agent 协作模块的背景设计

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/backend/schemas/task.py`: 已经有 `preset_mode` 字段，可直接承接 Phase 2 的模式入口。
- `app/backend/services/task_service.py`: 是当前任务处理中心，适合插入模板加载与模式解析。
- `app/backend/integration/openhands_adapter.py`: 适合接收已经被模板增强后的任务负载。

### Established Patterns
- Phase 1 已建立 `api -> services -> integration` 分层，Phase 2 应继续沿用。
- 现有接口返回统一 `TaskResponse`，模板信息应通过 metadata 或扩展 schema 暴露，不要破坏主 contract。

### Integration Points
- 模板 loader 可挂在 `services` 或新增 `presets` 模块中。
- `POST /api/tasks` 需要在进入 adapter 前完成 preset 解析。
- 如需 discovery，可新增轻量级 `GET /api/presets` 路由。

</code_context>

<deferred>
## Deferred Ideas

- 基于模板的真实 Agent 实例化 -> Phase 3
- 仓库分析开关真正驱动上下文注入 -> Phase 4
- 基于模板的模型路由执行 -> Phase 5
- 审批开关真正驱动审批节点 -> Phase 6

</deferred>

---

*Phase: 02-preset-template-center*
*Context gathered: 2026-04-18*

