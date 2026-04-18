---
phase: 03-agent-instantiation-orchestration
created: 2026-04-18T14:40:00+08:00
status: locked
---

# Phase 3 Context

## Goal

基于现有 preset 模板体系，实现 `code-engineering` 模式下的角色化 Agent 实例化与串行任务调度。

## Locked Decisions

1. Phase 3 只完整实现 `code-engineering` 模式，不扩展 `paper-revision` 的真实编排。
2. 角色集合固定为：`project-manager -> backend -> frontend -> reviewer`。
3. 执行拓扑固定为严格串行，不做并行执行和回环重试。
4. 角色间通过统一 `stage context` 传递上游摘要和原始请求。
5. 任一关键阶段失败即终止后续链路，并返回阶段化错误摘要。

## Non-Goals

- 不在本阶段实现论文修改模式的标准检索或审稿循环
- 不在本阶段引入 worktree 隔离
- 不在本阶段引入人工审批
- 不在本阶段实现真实多模型路由

## Expected Outcome

- `POST /api/tasks` 在 `preset_mode=code-engineering` 下不再走单次 adapter 调用
- 系统返回结构化阶段结果、阶段摘要和最终汇总
- 其余 preset 保持 Phase 2 行为不变
