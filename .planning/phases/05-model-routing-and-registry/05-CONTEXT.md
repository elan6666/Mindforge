---
phase: 05-model-routing-and-registry
created: 2026-04-19T14:30:00+08:00
status: locked
---

# Phase 5 Context

## Goal

为现有任务链补齐后端 provider/model registry、静态路由规则，以及执行时模型选择。

## Locked Decisions

1. Phase 5 只做后端 registry 和 routing，不做前端模型中心与规则模板 UI。
2. 模型注册采用文件型 YAML catalog，先不上数据库。
3. 路由优先级固定为：显式 override -> role 默认 -> task_type 默认 -> preset 默认 -> global 默认 -> priority fallback。
4. `code-engineering` 的每个 stage 都要有独立模型解析结果。
5. 当前执行层继续沿用现有任务链，只把模型选择接入 metadata 和 adapter payload。

## Non-Goals

- 不在本阶段实现前端模型管理页面
- 不在本阶段实现用户自定义规则模板
- 不在本阶段实现复杂成本优化、负载均衡或自动 fallback 重试
- 不在本阶段接入真实 OpenHands 多模型运行时

## Expected Outcome

- 后端可以列出 provider 和 model 定义
- 单次任务和 `code-engineering` 多阶段任务都能返回结构化模型选择结果
- 显式模型 override 可用，且无效 override 返回结构化错误

## OpenHands Reference Areas

- `E:/CODE/OpenHands-main/OpenHands-main/openhands/agenthub/README.md`
- `E:/CODE/OpenHands-main/OpenHands-main/openhands/runtime/plugins/agent_skills/README.md`

## Reuse Guidance

- Phase 5 优先学习 OpenHands 对 runtime 边界和 agent 执行语义的划分，不引入第二套长期协议
- registry 和 routing 留在 Mindforge 产品层，但 payload 形状要继续向上游兼容方向收敛
