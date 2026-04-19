---
phase: 07-model-control-center-and-rule-templates
created: 2026-04-19T16:25:00+08:00
status: locked
---

# Phase 7 Context

## Goal

在 Phase 5 的后端 model registry/routing 和 Phase 6 的 Web App 工作台之上，增加用户可见的模型中心与规则模板中心，使用户可以管理模型优先级、启停状态，并定义“不同职责 -> 不同模型”的结构化分配规则。

## Locked Decisions

1. Phase 7 不重做 Phase 6 的工作台壳；模型中心和规则模板作为 settings/control center 扩展进入现有前端。
2. 当前 `app/model_registry/catalog.yaml` 继续作为基础 seed catalog；用户可编辑部分通过单独的本地 override/config 文件持久化，而不是直接把前端操作写回静态种子文件。
3. 规则模板以结构化字段为准，不以自由文本作为后端单一事实源；可以保留备注文本，但执行必须依赖明确的 role/model 映射。
4. “默认协调模型先分析任务，再选择规则模板” 要落在后端服务层，而不是前端本地拼装；前端只负责配置、选择、展示和覆写。
5. 本阶段优先复用 OpenHands 的 settings layout / navigation / input primitives，不新造一套完全独立的设置页框架。

## Non-Goals

- 不在本阶段实现审批与历史持久化
- 不在本阶段实现 GitHub 只读上下文
- 不在本阶段完成论文修改全流程编排
- 不在本阶段引入复杂数据库迁移；优先用轻量本地配置持久化完成 MVP

## Expected Outcome

- 用户能在前端看到独立的模型中心页
- 用户能调整模型优先级：`high` / `medium` / `low` / `disabled`
- 用户能创建和编辑规则模板，把不同职责映射到不同模型
- 任务执行时可以记录本次命中的规则模板、协调模型和角色模型分配结果

## OpenHands Reference Areas

- `E:/CODE/OpenHands-main/OpenHands-main/frontend/src/components/features/settings/settings-layout.tsx`
- `E:/CODE/OpenHands-main/OpenHands-main/frontend/src/components/features/settings/settings-navigation.tsx`
- `E:/CODE/OpenHands-main/OpenHands-main/frontend/src/components/features/settings/settings-input.tsx`
- `E:/CODE/OpenHands-main/OpenHands-main/frontend/src/components/features/settings/settings-dropdown-input.tsx`
- `E:/CODE/OpenHands-main/OpenHands-main/frontend/src/components/features/settings/settings-switch.tsx`

## Reuse Guidance

- 复用 OpenHands 的 settings layout、左侧 settings navigation 和表单输入组织方式
- 保持 `Mindforge` 的差异化集中在：model priority、rule templates、coordinator-driven assignment
- 规则模板和协调模型选择应建立在 Phase 5 的 registry/routing 基础上，而不是再造第二套模型配置系统
