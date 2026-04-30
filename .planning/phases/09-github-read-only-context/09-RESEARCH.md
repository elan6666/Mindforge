---
phase: 09-github-read-only-context
status: planned
---

# Phase 9 Research

## Problem Framing

当前 Mindforge 已具备：

- preset 与多阶段编排
- repo analysis 与上下文注入
- 模型中心与规则模板
- 审批、任务历史和阶段历史

但外部上下文仍局限于本地仓库。对于代码评审、需求跟踪和任务协作场景，还缺少来自 GitHub 的只读上下文，例如：

- 仓库描述、默认分支、Stars/Forks、主要语言
- Issue 标题、状态、标签、正文摘要
- Pull Request 标题、状态、作者、变更摘要

Phase 9 的目标是把这些 GitHub 只读信息纳入任务和结果链路。

## Constraints

- 项目当前保持单用户本地原型，不适合引入复杂 OAuth、多租户或后台同步
- 当前前端已有 workspace shell、历史详情和 metadata 面板，应尽量复用
- 当前执行链的最佳落点是 task metadata，而不是另起独立上下文层

## Recommended Shape

### Backend

- 新增 GitHub context schema
- 新增 GitHub read-only service
- 任务请求允许传 GitHub 引用信息
- 在 TaskService 中读取 GitHub 上下文，并写入 metadata

### Frontend

- 在任务输入区增加可选 GitHub 仓库/Issue/PR 输入
- 在结果区与历史详情中增加 GitHub Context 展示卡片
- 历史详情继续复用现有 `metadata` + detail panel

## Proposed Input Shape

建议使用显式 request 字段，而不是只塞进自由 metadata：

- `github_repo`
- `github_issue_number`
- `github_pr_number`

这样前端和后端都更稳定，错误提示也更明确。

## API Strategy

推荐两层：

1. 任务时按需读取
   - `/api/tasks` 接受 GitHub 引用字段
2. 只读查询接口
   - `/api/github/repository`
   - `/api/github/issues/{number}`
   - `/api/github/pulls/{number}`

第一层解决执行链上下文注入，第二层解决前端预览和独立展示。

## Risks

- 如果直接依赖 GitHub 认证，可能阻塞本地演示
- 如果把 GitHub 返回原样塞进 metadata，会让历史记录膨胀

## Mitigations

- 优先做摘要化对象，不持久化整份原始 API 响应
- 本阶段只需要“可读、可展示、可注入”，不追求全字段覆盖

## Plan Split Rationale

- `09-01`：后端 GitHub 只读读取、摘要化、任务集成
- `09-02`：前端输入与展示增强，历史详情卡片化结果展示
