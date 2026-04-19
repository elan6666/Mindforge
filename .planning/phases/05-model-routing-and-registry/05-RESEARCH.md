---
phase: 05-model-routing-and-registry
researched: 2026-04-19T14:40:00+08:00
status: complete
---

# Phase 5 Research

## Scope

Phase 5 需要在不破坏 Phase 1-4 主链路的前提下，补上后端模型注册和路由能力。

## Findings

1. 当前系统已有稳定的 `preset -> task service -> adapter` 链路，最适合插入 model routing service，而不是重写任务入口。
2. `code-engineering` 已有固定四阶段链，适合在 stage definition 生成时解析每个角色的模型。
3. 当前 preset 已携带 `default_models`，但值还是产品层默认值，需要一个真实 registry 去验证、回退和解释这些值。
4. 用户后续明确需要模型优先级和不同角色绑定不同模型，因此 Phase 5 应先把后端静态规则打底。

## Chosen Shape

- `app/model_registry/catalog.yaml`: provider/model/routing 单一事实源
- `model_registry_service`: 负责列举和校验
- `model_routing_service`: 负责执行时解析
- `/api/providers` 和 `/api/models`: 提供前端 Phase 6/7 的查询基座
- `TaskRequest` 增加 `task_type`、`model_override`、`role_model_overrides`

## Deferred

- 用户可视化模型中心 -> Phase 7
- 规则模板 authoring -> Phase 7
- 复杂路由策略与成本优化 -> future
