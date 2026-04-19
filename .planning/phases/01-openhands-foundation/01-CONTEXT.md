# Phase 1: OpenHands Foundation - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

本阶段只交付 OpenHands 二次开发所需的工程骨架与基础接入能力：项目目录、运行配置、FastAPI 扩展入口、OpenHands 适配层、统一任务请求与响应。模板中心、多 Agent 实例化、仓库分析、模型路由和审批历史都不在本阶段实现。

</domain>

<decisions>
## Implementation Decisions

### 运行入口
- **D-01:** 采用 `API-first` 路线，优先把 FastAPI 服务和统一任务入口跑通。
- **D-02:** CLI 和 GUI 在 Phase 1 只保留接入占位，不要求完成完整交互层。

### OpenHands 集成边界
- **D-03:** 以外部适配层优先，尽量不直接修改 OpenHands 核心逻辑。
- **D-04:** 所有 Phase 1 的请求转发都经过 `adapter/service/router` 分层，避免后续功能直接绑定底座内部实现。

### 工程骨架
- **D-05:** Phase 1 先建立后端主骨架，包含 `api`、`core`、`integration`、`schemas`、`services`、`storage` 目录。
- **D-06:** 前端只保留 OpenHands GUI 扩展目录或说明文件占位，不在本阶段实现页面功能。

### 运行形态
- **D-07:** Phase 1 的目标运行形态是本地单用户服务，不做远程部署、多用户和权限管理。
- **D-08:** “Phase 1 完成”定义为一次端到端任务转发演示可用，并返回统一响应，同时记录基础日志。

### the agent's Discretion
- Python 包布局和命名细节
- 配置文件采用 `pydantic-settings` 还是等价轻量实现
- 本地日志落盘的具体格式

</decisions>

<specifics>
## Specific Ideas

- 目录结构要能直接支撑后续模板中心、Agent 调度、仓库分析等模块插入。
- 请求链路要体现“你们的系统入口 -> 适配层 -> OpenHands”，而不是直接暴露 OpenHands 原生接口。
- Phase 1 保持简单，但一定要能演示“收到任务 -> 转发 -> 返回规范化结果”。

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning Baseline
- `.planning/PROJECT.md` - 项目定位、范围边界、MVP 和技术基线
- `.planning/REQUIREMENTS.md` - 可追踪需求与 Phase 1 对应的 `FOUND-*` 需求
- `.planning/ROADMAP.md` - Phase 1 目标、成功标准和计划占位

### Design Background
- `output/doc/多Agent软件研发助手_可行性分析报告_OpenHands版.docx` - OpenHands 二开方向的可行性说明
- `output/doc/多Agent智能软件研发辅助平台_概要设计说明书_OpenHands版.docx` - 模块划分与系统流程背景
- `output/doc/多Agent智能软件研发辅助平台_详细设计说明书_OpenHands版.docx` - 模块职责、数据对象和接口背景

### OpenHands Reference Areas
- `E:/CODE/OpenHands-main/OpenHands-main/README.md` - OpenHands 产品入口划分，帮助区分 SDK、CLI、Local GUI 和 Cloud
- `E:/CODE/OpenHands-main/OpenHands-main/openhands/agenthub/README.md` - agent / state / action / observation 的上游抽象方向
- `E:/CODE/OpenHands-main/OpenHands-main/openhands/runtime/plugins/agent_skills/README.md` - 运行时工具能力应如何与提示型技能分层

### Reuse Guidance
- Phase 1 先学习 OpenHands 的边界划分方式，不要试图在本阶段复制完整运行时
- 适配层优先参考上游 runtime handoff 思路，不要发明长期独立的 Mindforge 内部传输协议
- 明确排除 `enterprise/` 代码和云端多租户逻辑

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.planning/*.md`: 已经包含项目目标、需求、阶段路线，可直接作为计划输入。
- `tmp/docs/update_docs_with_features.py`: 展示了你们目前文档中的核心模块命名，可作为工程目录命名参考。

### Established Patterns
- 当前仓库尚无实际应用代码，Phase 1 需要先建立代码目录和最小运行骨架。
- 现有设计已经收敛到 `OpenHands + FastAPI + SQLite + 模板中心` 路线，Phase 1 不应偏离。

### Integration Points
- 后续执行代码建议挂在新的应用目录中，由 FastAPI 入口承接任务请求。
- OpenHands 集成点应位于独立 `integration` 层，避免将来模板和调度模块直接耦合到服务入口。

</code_context>

<deferred>
## Deferred Ideas

- 模板中心与预设模式 -> Phase 2
- 角色化 Agent 实例化与串行调度 -> Phase 3
- 仓库分析与上下文注入 -> Phase 4
- 模型路由 -> Phase 5
- 审批与历史记录 -> Phase 6
- GitHub 只读集成 -> Phase 7

</deferred>

---

*Phase: 01-openhands-foundation*
*Context gathered: 2026-04-18*
