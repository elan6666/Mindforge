---
phase: 06-frontend-workspace-shell
created: 2026-04-19T15:40:00+08:00
status: locked
---

# Phase 6 Context

## Goal

实现 `Mindforge` 的 Web App 工作台壳，采用类似 Codex / OpenHands 的主工作区结构：左侧导航、聊天式任务区、会话历史和右侧结果面板。

## Locked Decisions

1. Phase 6 只做通用工作台壳，不做模型中心和规则模板页的详细交互。
2. 产品形态固定为 Web App，不做桌面端壳。
3. 主页面布局采用三块核心区域：左侧边栏、中央聊天/任务区、右侧结果或标签面板。
4. 当前阶段优先接现有后端接口：`/api/tasks`、`/api/presets`、`/api/providers`、`/api/models`。
5. 视觉和布局优先参考 OpenHands 的 `conversation/chat/tabs/browser` 组织方式，而不是从零设计一套完全不同的前端框架。

## Non-Goals

- 不在本阶段实现模型优先级管理页
- 不在本阶段实现规则模板 authoring
- 不在本阶段实现审批页和历史归档页
- 不在本阶段实现 GitHub 外部上下文 UI

## Expected Outcome

- 前端具备一个可演示的 Web 工作台壳
- 用户可以在聊天式主区发起任务并看到结果
- 用户可以看到 preset 选择、仓库输入、默认协调模型等常见控件占位或真实接入
- 右侧面板至少能展示最终结果、阶段轨迹、仓库摘要或任务元数据

## OpenHands Reference Areas

- `E:/CODE/OpenHands-main/OpenHands-main/frontend/src/components/features/conversation/conversation-main/conversation-main.tsx`
- `E:/CODE/OpenHands-main/OpenHands-main/frontend/src/components/features/conversation/conversation-tabs/conversation-tabs.tsx`
- `E:/CODE/OpenHands-main/OpenHands-main/frontend/src/components/features/chat/components/chat-input-container.tsx`
- `E:/CODE/OpenHands-main/OpenHands-main/frontend/src/components/features/browser/browser.tsx`

## Reuse Guidance

- 优先借鉴 OpenHands 的工作区分栏和 tab/panel 组织方式
- 聊天输入区、右侧标签面板、browser/changes/terminal 的结构优先复用其成熟模式
- `Mindforge` 自己的差异化应落在 preset、execution panels、model control 入口和规则模板入口，不是重写整套 workspace 壳
