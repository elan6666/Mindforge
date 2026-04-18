---
phase: 03-agent-instantiation-orchestration
researched: 2026-04-18T14:45:00+08:00
---

# Phase 3 Research

## Existing Baseline

- `TaskService` 已负责 preset 解析、adapter 调用和结果整形。
- `PresetService` 已能解析 `code-engineering` 的角色定义和默认模型映射。
- `OpenHandsAdapter` 已提供 `mock / http / disabled` 三种执行边界。
- 当前 `/api/tasks` 仍是单次执行链，尚未基于角色拆分阶段。

## Recommended Implementation

### 1. Keep the single API entry

保留现有 `/api/tasks`，由 `TaskService` 根据 `preset_mode` 判断是否进入多阶段编排。

### 2. Add orchestration as a service layer

新增独立编排服务，避免把角色实例化和阶段提示词拼装写死在 `TaskService` 中。

### 3. Reuse the adapter boundary

每个阶段仍通过 `OpenHandsAdapter` 调用，保持后续接真实 OpenHands 运行时的兼容性。

### 4. Return structured stage metadata

除了最终文本输出，还应返回：

- 阶段顺序
- 角色名
- 使用模型
- 阶段摘要
- 失败阶段

## Risks

1. `http` 模式上游未必理解额外 metadata，因此 Phase 3 只保证本地 mock 行为可验证。
2. `code-engineering` 的 `execution_flow` 只有 `plan / implement / review`，但实际角色有四个，因此应以 `agent_roles` 顺序为主。
3. 如果未来要支持并行后端/前端，当前统一 stage context 结构应尽量保持通用。
