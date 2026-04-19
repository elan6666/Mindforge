---
phase: 08-approval-and-history
created: 2026-04-19T09:40:00-05:00
status: locked
---

# Phase 8 Context

## Goal

在现有任务执行链和 Web App 工作台之上，增加审批、执行日志和历史持久化，使 Mindforge 从“可运行演示”进入“可追踪、可回看、可中断”的状态。

## Locked Decisions

1. Phase 8 先只拦截高风险动作，不拦截普通只读分析或 mock 演示链路。
2. 审批采用任务内阻塞式交互：执行链进入审批节点后暂停，等待前端在当前会话内批准或拒绝。
3. 日志粒度固定为 `task + stage` 双层：
   - task：preset、template、coordinator、状态、时间
   - stage：role、model、status、summary、error
4. 历史和审批持久化使用 `SQLite`，不继续沿用内存或纯 JSON 文件。
5. 前端历史页先做最近任务列表、状态筛选和详情展开，不做复杂搜索系统。

## Non-Goals

- 不在本阶段实现 GitHub 外部上下文
- 不在本阶段实现复杂通知、消息推送或异步审批流
- 不在本阶段引入多用户权限系统
- 不在本阶段重构 OpenHands adapter 协议

## Expected Outcome

- 高风险任务可以进入审批等待态
- 批准和拒绝操作有结构化记录
- task/stage 执行日志可查询
- 前端可以查看最近任务历史和详情

## OpenHands Reference Areas

- `E:/CODE/OpenHands-main/OpenHands-main/frontend/src/components/features/chat/`
- `E:/CODE/OpenHands-main/OpenHands-main/frontend/src/components/features/conversation/`
- `E:/CODE/OpenHands-main/OpenHands-main/frontend/src/components/features/settings/`
- `E:/CODE/OpenHands-main/OpenHands-main/openhands/agenthub/README.md`

## Reuse Guidance

- 继续复用现有 workspace shell，不新造第二套历史/审批工作台
- 审批与历史要建立在 Phase 3/4/5/7 已有 metadata 上，而不是重新定义执行结果结构
- 持久化层保持轻量，优先为后续查询和展示提供稳定 schema
