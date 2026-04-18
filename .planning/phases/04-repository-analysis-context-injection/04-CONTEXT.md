---
phase: 04-repository-analysis-context-injection
created: 2026-04-19T09:20:00+08:00
status: locked
---

# Phase 4 Context

## Goal

为现有任务链补齐本地仓库扫描、关键文件识别、结构化 `Repo Summary` 生成与上下文注入。

## Locked Decisions

1. 只做本地仓库轻量扫描，不拉取远程仓库，不做深层语义分析。
2. 关键文件识别以文件名规则为主，不引入复杂分类算法。
3. 仓库摘要采用结构化对象输出，同时附带可注入 prompt 的简短文本摘要。
4. 上下文注入发生在任务开始前，所有后续角色共享同一份仓库摘要。
5. 仓库分析失败或路径不可用时降级，不直接让整任务失败。

## Non-Goals

- 不在本阶段实现 GitHub 外部上下文
- 不在本阶段实现模型路由
- 不在本阶段实现 worktree 或并行扫描
- 不在本阶段实现论文模式的文献或期刊规范分析

## Expected Outcome

- `repo_path` 不再只是占位字段
- `code-engineering` 模式会携带仓库摘要进入多阶段编排
- 响应 metadata 会包含 `repo_analysis`
