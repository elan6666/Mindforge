---
phase: 09-github-read-only-context
created: 2026-04-19T15:05:00-05:00
status: locked
---

# Phase 9 Context

## Goal

在现有任务执行链、审批历史和 Web App 工作台之上，增加 GitHub 只读上下文能力，并增强结果展示，让任务可以携带仓库、Issue、PR 摘要进入执行与回看链路。

## Locked Decisions

1. Phase 9 只做 GitHub 只读能力，不做写操作、自动评论、自动建 PR 或状态回写。
2. GitHub 上下文优先支持三类对象：
   - repository summary
   - issue summary
   - pull request summary
3. GitHub 输入先通过显式参数或 metadata 传入，不做复杂自动发现。
4. GitHub 读取结果要写入 task metadata，并在历史详情和结果面板中可见。
5. 结果展示增强基于现有 Phase 6/8 工作台继续扩展，不新造第二套结果页。

## Non-Goals

- 不在本阶段接入 GitHub 写操作
- 不在本阶段实现 webhook、轮询同步或多仓库后台索引
- 不在本阶段实现复杂搜索、标签系统或跨平台代码托管统一抽象

## Expected Outcome

- 任务可以附带 GitHub repository / issue / PR 摘要
- GitHub 只读上下文可以进入 execution metadata
- 前端结果页和历史详情能展示 GitHub 上下文卡片
- 为 Phase 10 和后续更真实的开发协作场景提供外部上下文底座

## OpenHands Reference Areas

- `E:/CODE/OpenHands-main/OpenHands-main/frontend/src/components/features/conversation/`
- `E:/CODE/OpenHands-main/OpenHands-main/frontend/src/components/features/chat/`
- `E:/CODE/OpenHands-main/OpenHands-main/openhands/memory/memory.py`

## Reuse Guidance

- GitHub 上下文应作为已有 workspace context 的新增来源，而不是单独的任务体系
- 展示层应复用现有结果/历史面板与 metadata 展示机制
- 如果 OpenHands 已有合适的只读上下文组织方式，应优先适配其模式而非新造平行抽象
