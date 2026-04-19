---
phase: 07-model-control-center-and-rule-templates
researched: 2026-04-19T16:25:00+08:00
status: complete
---

# Phase 7 Research

## Scope

Phase 7 负责把 Phase 5 的只读 model registry 升级成用户可配置的模型中心，并把你前面明确提出的“不同职责绑定不同模型”的规则模板正式做成产品能力。

## Findings

1. 当前后端只支持只读的 `/api/providers` 与 `/api/models`，且 registry 完全来自静态 `catalog.yaml`。
2. 当前前端已具备可运行的 workspace shell，但 `frontend/src/App.tsx` 仍是单页面实现，还没有 settings/control center 的页面结构。
3. 当前任务执行链只支持 `model_override` 和 `role_model_overrides` 这种请求级覆写，还没有“规则模板 -> 角色映射 -> 协调模型选择”的持久化系统。
4. OpenHands 前端在 settings 区已经把布局、导航、输入控件拆成稳定的 primitives，适合作为本阶段 UI 参考，而不是重新设计一整套 settings shell。

## Chosen Shape

- Phase 7 拆成两个 plan：
  - `07-01`: 后端可编辑配置层、规则模板 schema、API 与 coordinator selection service
  - `07-02`: 前端模型中心、规则模板页、与工作台联动的选择/展示入口
- 基础 model catalog 继续保留；新增本地可写 override/rules 配置，优先使用轻量 YAML/JSON 持久化
- 规则模板对象至少包含：
  - `template_id`
  - `display_name`
  - `scenario` / `preset_mode`
  - `default_coordinator_model_id`
  - `assignments[]`：`role` / `responsibility` / `model_id`
  - `enabled`
  - `notes`
- 协调模型分析流程优先支持：
  1. 显式模板选择
  2. 按 `preset_mode` / `task_type` 的模板候选筛选
  3. 使用默认协调模型生成结构化模板选择结果或回退默认模板

## Deferred

- 自然语言自由编辑规则直接变成执行事实源
- 多用户共享模板与权限管理
- 真正复杂的成本优化、自动 A/B 路由和实验系统
