---
phase: 04-repository-analysis-context-injection
researched: 2026-04-19T09:25:00+08:00
---

# Phase 4 Research

## Existing Baseline

- `TaskRequest` 已包含 `repo_path`
- `PresetDefinition` 已包含 `requires_repo_analysis`
- `code-engineering` preset 已声明 `requires_repo_analysis: true`
- 当前系统尚未真正读取本地仓库内容

## Recommended Implementation

### 1. Add a dedicated repository analysis service

仓库分析应独立成服务，避免目录扫描逻辑散落在 `TaskService` 或编排服务中。

### 2. Keep scanning lightweight and deterministic

首轮只做：

- 顶层目录结构
- 关键文件规则识别
- 可能入口文件识别
- 技术栈推断

### 3. Return both structured data and prompt-ready summary

下游需要两种形态：

- 结构化对象：用于 API metadata 和后续 UI
- 文本摘要：用于注入多 Agent prompt

### 4. Inject once, reuse everywhere

在任务开始前得到仓库分析结果，再注入 `TaskService` 和 `SerialOrchestrationService`。

## Risks

1. 本地仓库过大时，递归扫描要受限，避免遍历过深。
2. 仅靠文件名规则会有误判，但适合当前 MVP。
3. Windows 路径和权限异常要显式降级处理，避免影响主任务流。
