---
phase: 08-approval-and-history
researched: 2026-04-19T09:40:00-05:00
status: complete
---

# Phase 8 Research

## Scope

Phase 8 负责把审批、执行日志和历史记录从“暂时只在响应中可见”的状态，升级成可持久化、可查询、可在 UI 中浏览的产品能力。

## Findings

1. 当前任务历史只保存在前端会话内存中，刷新后即丢失。
2. 当前后端已经具备丰富 metadata：`task_model_selection`、`rule_template_selection`、`effective_role_model_overrides`、`orchestration`、`repo_analysis`，这些都适合直接落库。
3. 当前执行链没有“等待审批”的状态，也没有审批记录 schema。
4. 审批和历史如果继续走 JSON 文件会很快变脆弱；Phase 8 是切入 SQLite 的合适时点。

## Chosen Shape

- Phase 8 拆成两个 plan：
  - `08-01`: 审批 schema、触发规则、阻塞式审批 API
  - `08-02`: 任务/阶段日志持久化、历史查询 API、前端历史页
- 数据层优先引入 SQLite 表：
  - `task_run`
  - `stage_run`
  - `approval_record`
- 高风险动作的最小触发策略：
  - 明确请求写操作
  - 将来接入真实 shell/file write/git write 时触发
  - 当前用 `metadata`/preset/rule 的风险标记做最小演示接入

## Deferred

- 审批消息推送
- 多审批人、多状态流转
- 全文搜索、标签、排序系统
- 复杂审计面板和跨项目聚合
