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

## OpenHands Reference Areas

- `E:/CODE/OpenHands-main/OpenHands-main/openhands/agenthub/README.md` - 上游对 agent、state、action、observation 以及 delegation 的抽象说明
- `E:/CODE/OpenHands-main/OpenHands-main/openhands/memory/memory.py` - workspace context 和 instructions 如何在执行前被组织并注入

## Reuse Guidance

- 当前串行 orchestration 是 Mindforge 的 MVP，不必返工，但后续扩展时要优先向 OpenHands 的 agent/state/action 语义收敛
- 不要继续膨胀一套完全平行的自定义执行协议；新增字段和阶段语义时先检查上游是否已有对应概念
- Phase 3 的目标是验证角色分工和结果结构，不是从零定义长期 agent runtime
