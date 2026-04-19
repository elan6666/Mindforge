---
phase: 06-frontend-workspace-shell
researched: 2026-04-19T15:45:00+08:00
status: complete
---

# Phase 6 Research

## Scope

Phase 6 负责把当前后端能力包装成一个可用的 Web 工作台，为 Phase 7 的模型中心和规则模板提供承载壳。

## Findings

1. 当前仓库的 `frontend/` 仍然只有占位 README，没有真实前端实现。
2. OpenHands 的前端已经把工作台拆成可复用的几类结构：`conversation-main` 负责左右面板布局，`conversation-tabs` 负责右侧 tab，`chat-input-container` 负责任务输入区，`browser.tsx` 提供右侧面板内容样板。
3. 当前后端已经能提供适合 UI 消费的数据：`/api/tasks`、`/api/presets`、`/api/providers`、`/api/models`。
4. 这一阶段不应过早把模型中心和规则模板做进主工作区；它们应该在 Phase 7 独立成 settings/control center。

## Chosen Shape

- 前端技术栈延续项目基线：`React + TypeScript`
- Phase 6 拆成两个 plan：
  - `06-01`: app shell、侧边栏、会话/任务历史布局
  - `06-02`: 聊天工作区、任务参数控件、结果/轨迹面板
- 工作区优先支持：
  - new task
  - presets
  - repo path
  - default coordinator model
  - final output / orchestration trace / repo summary / metadata tabs

## Deferred

- 模型优先级与规则模板 UI -> Phase 7
- 审批与历史完整页 -> Phase 8
- GitHub 上下文展示 -> Phase 9
