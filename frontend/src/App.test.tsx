import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import * as api from "./lib/api";
import type {
  ApprovalRecord,
  ArtifactSummary,
  MCPServerSummary,
  MCPToolAuditRecord,
  MCPToolListResult,
  ModelSummary,
  PresetSummary,
  ProjectSpaceSummary,
  ProviderSummary,
  RuleTemplateSummary,
  SkillSummary,
  TaskHistoryDetail,
  TaskHistorySummary,
  TaskResult,
} from "./types";

vi.mock("./lib/api", () => ({
  approveTask: vi.fn(),
  createMcpServer: vi.fn(),
  createModelControl: vi.fn(),
  createProjectSpace: vi.fn(),
  createProviderControl: vi.fn(),
  createRuleTemplate: vi.fn(),
  deleteConversationHistory: vi.fn(),
  deleteHistoryTask: vi.fn(),
  deleteMcpServer: vi.fn(),
  deleteModelControl: vi.fn(),
  deleteProjectSpace: vi.fn(),
  deleteProviderControl: vi.fn(),
  deleteRuleTemplate: vi.fn(),
  fetchConversationHistory: vi.fn(),
  fetchEditableModels: vi.fn(),
  fetchHistoryTasks: vi.fn(),
  fetchMcpAudit: vi.fn(),
  fetchMcpServers: vi.fn(),
  fetchMcpTools: vi.fn(),
  fetchModels: vi.fn(),
  fetchPendingApprovals: vi.fn(),
  fetchPresets: vi.fn(),
  fetchProjectSpaces: vi.fn(),
  fetchProviders: vi.fn(),
  fetchUserProviders: vi.fn(),
  fetchRuleTemplates: vi.fn(),
  fetchSkills: vi.fn(),
  fetchTaskHistoryDetail: vi.fn(),
  getApiBaseUrl: vi.fn(() => "http://127.0.0.1:8000/api"),
  rejectTask: vi.fn(),
  submitTask: vi.fn(),
  testProviderConnection: vi.fn(),
  updateSkillSettings: vi.fn(),
  uploadFile: vi.fn(),
  exportArtifact: vi.fn(),
  updateCanvasArtifact: vi.fn(),
  updateModelControl: vi.fn(),
  updateProviderControl: vi.fn(),
  updateRuleTemplate: vi.fn(),
}));

const presets: PresetSummary[] = [
  {
    preset_mode: "code-engineering",
    display_name: "代码工程",
    description: "协调规划、后端、前端和审查。",
    requires_repo_analysis: true,
    requires_approval: false,
  },
  {
    preset_mode: "paper-revision",
    display_name: "论文修改",
    description: "协调期刊标准分析、论文改写和审稿人式反馈。",
    requires_repo_analysis: false,
    requires_approval: false,
  },
];

const providers: ProviderSummary[] = [
  {
    provider_id: "openai",
    display_name: "OpenAI",
    description: "主力 Provider",
    enabled: true,
    api_base_url: "https://api.openai.com/v1",
    protocol: "openai",
    api_key_env: "OPENAI_API_KEY",
    api_key_configured: true,
    anthropic_api_base_url: null,
  },
];

const models: ModelSummary[] = [
  {
    model_id: "gpt-5.4",
    display_name: "GPT-5.4",
    provider_id: "openai",
    upstream_model: "gpt-5.4",
    priority: "high",
    enabled: true,
    supported_preset_modes: ["code-engineering"],
    supported_task_types: ["planning", "review"],
    supported_roles: ["project-manager", "backend"],
  },
];

const deepseekModel: ModelSummary = {
  model_id: "deepseek-v3.2",
  display_name: "deepseek-v3.2",
  provider_id: "playwright-ark",
  upstream_model: "deepseek-v3.2",
  priority: "high",
  enabled: true,
  supported_preset_modes: [],
  supported_task_types: [],
  supported_roles: [],
  is_custom: true,
};

const ruleTemplates: RuleTemplateSummary[] = [
  {
    template_id: "code-engineering-default",
    display_name: "代码工程默认模板",
    description: "默认模板",
    preset_mode: "code-engineering",
    task_types: ["planning"],
    default_coordinator_model_id: "gpt-5.4",
    enabled: true,
    is_default: true,
    trigger_keywords: ["login"],
    assignments: [
      {
        role: "frontend",
        responsibility: "界面实现",
        model_id: "gpt-5.4",
      },
    ],
    notes: "默认模板",
  },
];

const skills: SkillSummary[] = [
  {
    skill_id: "frontend-design",
    name: "frontend-design",
    description: "Polish frontend UI.",
    path: "C:/Users/16523/.codex/skills/frontend-design/SKILL.md",
    source_root: "C:/Users/16523/.codex/skills",
    enabled: true,
    trust_level: "local",
    notes: "",
  },
];

const mcpServers: MCPServerSummary[] = [
  {
    server_id: "filesystem",
    display_name: "Filesystem",
    transport: "http-jsonrpc",
    endpoint_url: "http://127.0.0.1:8765/mcp",
    command: null,
    args: [],
    env: {},
    working_directory: null,
    enabled: true,
    headers: {},
    headers_configured: false,
    env_configured: false,
    allowed_tools: ["read_file"],
    blocked_tools: ["delete_file"],
    tool_call_requires_approval: true,
    notes: "Local file tools",
    status: "configured",
    tool_count: null,
  },
];

const projectSpaces: ProjectSpaceSummary[] = [
  {
    project_id: "mindforge-dev",
    display_name: "Mindforge Dev",
    description: "Build Mindforge.",
    instructions: "Use concise Chinese.",
    memory: "MCP calls require approval.",
    default_preset_mode: "code-engineering",
    repo_path: "E:/CODE/agent助手",
    github_repo: "elan6666/Mindforge",
    skill_ids: ["frontend-design"],
    mcp_server_ids: ["filesystem"],
    file_ids: ["file-brief.md"],
    tags: ["dev"],
    enabled: true,
    file_count: 1,
    created_at: "2026-05-02T00:00:00+00:00",
    updated_at: "2026-05-02T00:00:00+00:00",
  },
];

const mcpToolResult: MCPToolListResult = {
  server_id: "filesystem",
  status: "ok",
  tools: [
    {
      name: "read_file",
      description: "Read a file",
      input_schema: { type: "object" },
    },
  ],
};

const mcpAuditRecords: MCPToolAuditRecord[] = [
  {
    audit_id: "audit-1",
    server_id: "filesystem",
    tool_name: "read_file",
    status: "approval_required",
    approved: false,
    blocked_reason: "tool_call_requires_approval",
    arguments_preview: '{"path":"README.md"}',
    error_message: null,
    duration_ms: 2,
    created_at: "2026-05-02T00:00:00+00:00",
  },
];

const exportedArtifact: ArtifactSummary = {
  artifact_id: "artifact-1",
  title: "Mindforge output",
  format: "md",
  filename: "mindforge-output.md",
  mime_type: "text/markdown; charset=utf-8",
  size_bytes: 24,
  created_at: "2026-05-01T00:00:00+00:00",
  source_task_id: "task-1",
  download_url: "/api/artifacts/artifact-1/download",
};

const approval: ApprovalRecord = {
  approval_id: "approval-1",
  task_id: "task-1",
  status: "pending",
  risk_level: "high",
  summary: "写入操作前需要审批。",
  actions: ["写入文件", "执行命令"],
  decision_comment: null,
  created_at: "2026-04-21T10:00:00+08:00",
  updated_at: "2026-04-21T10:01:00+08:00",
};

const historyItems: TaskHistorySummary[] = [
  {
    task_id: "task-1",
    prompt: "Implement login flow",
    preset_mode: "code-engineering",
    task_type: "planning",
    status: "pending_approval",
    provider: "mindforge-approval-gate",
    created_at: "2026-04-21T10:00:00+08:00",
    updated_at: "2026-04-21T10:01:00+08:00",
    requires_approval: true,
    approval_status: "pending",
  },
];

const historyDetail: TaskHistoryDetail = {
  ...historyItems[0],
  repo_path: ".",
  message: "等待审批。",
  output: "阶段执行结果",
  error_message: null,
  request_payload: {
    prompt: "Implement login flow",
  },
  metadata: {
    orchestration: {
      preset_mode: "code-engineering",
      strategy: "serial",
      total_stages: 1,
      completed_stages: 1,
      failed_stage: null,
      stages: [
        {
          order: 1,
          stage_id: "stage-1",
          stage_name: "Project manager",
          role: "project-manager",
          model: "gpt-5.4",
          status: "completed",
          provider: "mock-openhands",
          summary: "已创建执行计划。",
          output: "计划输出",
          metadata: {},
          error_message: null,
        },
      ],
    },
    github_context: {
      repository: {
        owner: "openai",
        name: "openai-python",
        full_name: "openai/openai-python",
        description: "OpenAI Python SDK",
        html_url: "https://github.com/openai/openai-python",
        default_branch: "main",
        primary_language: "Python",
        stargazers_count: 100,
        forks_count: 10,
        open_issues_count: 5,
        visibility: "public",
      },
      issue: {
        number: 123,
        title: "Bug report",
        state: "open",
        html_url: "https://github.com/openai/openai-python/issues/123",
        author: "octocat",
        labels: ["bug"],
        comment_count: 3,
        body_excerpt: "Issue 上下文",
      },
      pull_request: {
        number: 9,
        title: "Fix bug",
        state: "open",
        html_url: "https://github.com/openai/openai-python/pull/9",
        author: "octocat",
        labels: ["enhancement"],
        comment_count: 2,
        review_comment_count: 1,
        draft: false,
        merged: false,
        head_ref: "feature",
        base_ref: "main",
        body_excerpt: "PR 上下文",
      },
    },
    academic_context: {
      journal: {
        journal_name: "Example Journal",
        journal_url: "https://journal.example/guidelines",
        title: "作者指南",
        excerpt: "使用结构化摘要和简洁的学术表达。",
        status: "fetched",
        error_message: null,
      },
      reference_papers: [
        {
          url: "https://paper.example/reference",
          title: "参考论文",
          excerpt: "贡献优先的结构。",
          status: "fetched",
          error_message: null,
        },
      ],
      warnings: [],
    },
    approval,
    tool_flags: {
      deep_analysis: true,
      web_search: true,
      code_execution: false,
      canvas: true,
    },
    tool_context: {
      deep_analysis: { status: "enabled" },
      canvas: { status: "enabled" },
    },
    canvas_artifacts: [
      {
        artifact_id: "canvas-task-1",
        kind: "markdown",
        title: "Mindforge 输出画布",
        editable: true,
        content: "初始画布内容",
        version: 1,
        versions: [
          {
            version: 1,
            title: "Mindforge 输出画布",
            content: "初始画布内容",
            updated_at: "2026-05-02T00:00:00+00:00",
            source: "initial-output",
          },
        ],
      },
    ],
    generated_artifacts: [exportedArtifact],
    execution_report: {
      runtime_boundary: {
        adapter: "OpenHandsAdapter",
        openhands_mode: "mock",
        skills_runtime: "prompt-context",
        mcp_runtime: "catalog/proxy",
        code_execution: "approval-gated-python-snippet",
      },
      steps: [
        {
          id: "context",
          label: "上下文装配",
          status: "completed",
          summary: "已合并任务上下文。",
        },
      ],
      warnings: ["MCP 当前作为 catalog/proxy 能力接入。"],
    },
  },
  stages: [
    {
      order: 1,
      stage_id: "stage-1",
      stage_name: "Project manager",
      role: "project-manager",
      model: "gpt-5.4",
      provider: "mock-openhands",
      status: "completed",
      summary: "已创建执行计划。",
      output: "计划输出",
      metadata: {},
      error_message: null,
      created_at: "2026-04-21T10:00:00+08:00",
    },
  ],
  approval,
};

const approvalResult: TaskResult = {
  status: "completed",
  message: "已批准",
  error_message: null,
  data: {
    output: "批准后的输出",
    provider: "mock-openhands",
    metadata: {
      task_id: "task-1",
      approval: {
        ...approval,
        status: "approved",
      },
    },
  },
};

function setupApiMocks() {
  vi.mocked(api.fetchPresets).mockResolvedValue(presets);
  vi.mocked(api.fetchProviders).mockResolvedValue(providers);
  vi.mocked(api.fetchUserProviders).mockResolvedValue(providers);
  vi.mocked(api.fetchModels).mockResolvedValue(models);
  vi.mocked(api.fetchEditableModels).mockResolvedValue(models);
  vi.mocked(api.fetchRuleTemplates).mockResolvedValue(ruleTemplates);
  vi.mocked(api.fetchSkills).mockResolvedValue(skills);
  vi.mocked(api.fetchProjectSpaces).mockResolvedValue(projectSpaces);
  vi.mocked(api.fetchMcpServers).mockResolvedValue(mcpServers);
  vi.mocked(api.fetchMcpAudit).mockResolvedValue(mcpAuditRecords);
  vi.mocked(api.fetchMcpTools).mockResolvedValue(mcpToolResult);
  vi.mocked(api.fetchHistoryTasks).mockResolvedValue(historyItems);
  vi.mocked(api.fetchPendingApprovals).mockResolvedValue([approval]);
  vi.mocked(api.fetchTaskHistoryDetail).mockResolvedValue(historyDetail);
  vi.mocked(api.fetchConversationHistory).mockResolvedValue([historyDetail]);
  vi.mocked(api.deleteHistoryTask).mockResolvedValue(undefined);
  vi.mocked(api.deleteConversationHistory).mockResolvedValue(undefined);
  vi.mocked(api.createMcpServer).mockImplementation(async (payload) => ({
    ...payload,
    status: "configured",
    tool_count: null,
  }));
  vi.mocked(api.deleteMcpServer).mockResolvedValue(undefined);
  vi.mocked(api.createProjectSpace).mockImplementation(async (payload) => ({
    ...payload,
    file_count: payload.file_ids.length,
    created_at: "2026-05-02T00:00:00+00:00",
    updated_at: "2026-05-02T00:00:00+00:00",
  }));
  vi.mocked(api.deleteProjectSpace).mockResolvedValue(undefined);
  vi.mocked(api.updateSkillSettings).mockImplementation(async (skillId, payload) => ({
    ...skills[0],
    skill_id: skillId,
    enabled: payload.enabled ?? skills[0].enabled,
    trust_level: payload.trust_level || skills[0].trust_level,
    notes: payload.notes || skills[0].notes,
  }));
  vi.mocked(api.exportArtifact).mockResolvedValue(exportedArtifact);
  vi.mocked(api.uploadFile).mockImplementation(async (file) => ({
    file_id: `file-${file.name}`,
    name: file.name,
    mime_type: file.type || "application/octet-stream",
    size_bytes: file.size,
    sha256: "test-sha256",
    status: "parsed",
    parser: "plain-text",
    text_excerpt:
      file.name === "brief.md" ? "structured upload text" : "hello from fixture",
    char_count: file.size,
    chunk_count: 1,
    error_message: null,
    metadata: {},
  }));
  vi.mocked(api.updateCanvasArtifact).mockImplementation(async (_taskId, _artifactId, payload) => ({
    ...historyDetail,
    metadata: {
      ...historyDetail.metadata,
      canvas_artifacts: [
        {
          artifact_id: "canvas-task-1",
          kind: "markdown",
          title: "Mindforge 输出画布",
          editable: true,
          content: payload.content,
          version: 2,
          versions: [
            {
              version: 1,
              title: "Mindforge 输出画布",
              content: "初始画布内容",
              updated_at: "2026-05-02T00:00:00+00:00",
              source: "initial-output",
            },
            {
              version: 2,
              title: "Mindforge 输出画布",
              content: payload.content,
              updated_at: "2026-05-02T00:10:00+00:00",
              source: "manual-edit",
            },
          ],
        },
      ],
    },
  }));
  vi.mocked(api.approveTask).mockResolvedValue(approvalResult);
  vi.mocked(api.rejectTask).mockResolvedValue({
    ...approvalResult,
    status: "rejected",
  });
  vi.mocked(api.updateModelControl).mockResolvedValue(models[0]);
  vi.mocked(api.updateProviderControl).mockImplementation(async (providerId, payload) => ({
    ...providers[0],
    ...payload,
    display_name: payload.display_name || providers[0].display_name,
    description: payload.description || providers[0].description,
    provider_id: providerId,
  }));
  vi.mocked(api.createProviderControl).mockImplementation(async (payload) => ({
    provider_id: payload.provider_id,
    display_name: payload.display_name,
    description: payload.description,
    enabled: payload.enabled,
    api_base_url: payload.api_base_url,
    protocol: payload.protocol,
    api_key_env: payload.api_key_env,
    api_key_configured: Boolean(payload.api_key),
    anthropic_api_base_url: payload.anthropic_api_base_url,
    is_custom: true,
  }));
  vi.mocked(api.deleteProviderControl).mockResolvedValue(undefined);
  vi.mocked(api.createModelControl).mockImplementation(async (payload) => ({
    ...payload,
    is_custom: true,
  }));
  vi.mocked(api.deleteModelControl).mockResolvedValue(undefined);
  vi.mocked(api.testProviderConnection).mockResolvedValue({
    provider_id: "openai",
    ok: true,
    status: "connected",
    detail: "Connection OK",
    protocol: "openai",
    api_base_url: "https://api.openai.com/v1",
    api_key_env: "OPENAI_API_KEY",
    api_key_configured: true,
    upstream_status: 200,
  });
  vi.mocked(api.createRuleTemplate).mockResolvedValue(ruleTemplates[0]);
  vi.mocked(api.updateRuleTemplate).mockResolvedValue(ruleTemplates[0]);
  vi.mocked(api.deleteRuleTemplate).mockResolvedValue(undefined);
  vi.mocked(api.submitTask).mockResolvedValue({
    status: "completed",
    message: "已提交",
    error_message: null,
    data: {
      output: "提交后的输出",
      provider: "mock-openhands",
      metadata: {
        task_id: "task-1",
      },
    },
  });
}

async function waitForWorkspaceData() {
  await waitFor(() => {
    expect(api.fetchHistoryTasks).toHaveBeenCalled();
  });
}

async function openFirstHistoryConversation() {
  fireEvent.click(await screen.findByText("Implement login flow"));
  await waitFor(() => {
    expect(api.fetchTaskHistoryDetail).toHaveBeenCalledWith("task-1");
  });
}

describe("App workspace shell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupApiMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the workspace shell with history and backend context", async () => {
    render(<App />);

    await waitForWorkspaceData();

    expect(screen.getByText("Mindforge 控制工作台")).toBeInTheDocument();
    expect(screen.getByText("任务工作台")).toBeInTheDocument();
    expect(screen.getAllByText("待审批").length).toBeGreaterThan(0);
    expect(screen.getByText("1 个待审批")).toBeInTheDocument();
    expect(screen.getByText("OpenAI")).toBeInTheDocument();
    expect(screen.getByText("http://127.0.0.1:8000/api")).toBeInTheDocument();
  });

  it("shows task fields according to the selected preset", async () => {
    render(<App />);

    await waitForWorkspaceData();

    fireEvent.click(screen.getByRole("button", { name: "打开工具菜单" }));
    fireEvent.click(await screen.findByRole("button", { name: /任务配置/ }));

    expect(screen.queryByText("仓库路径")).not.toBeInTheDocument();
    expect(screen.queryByText("GitHub 仓库")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("预设模式"), {
      target: { value: "code-engineering" },
    });

    expect(screen.getByText("仓库路径")).toBeInTheDocument();
    expect(screen.getByText("GitHub 仓库")).toBeInTheDocument();
    expect(screen.queryByText("期刊名称")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("预设模式"), {
      target: { value: "paper-revision" },
    });

    expect(await screen.findByText("期刊名称")).toBeInTheDocument();
    expect(screen.getByText("期刊投稿指南 URL")).toBeInTheDocument();
    expect(screen.queryByText("仓库路径")).not.toBeInTheDocument();
    expect(screen.queryByText("GitHub 仓库")).not.toBeInTheDocument();
  });

  it("closes composer menus and task config when clicking outside", async () => {
    render(<App />);

    await waitForWorkspaceData();

    fireEvent.click(screen.getByRole("button", { name: "打开工具菜单" }));
    expect(await screen.findByRole("button", { name: /任务配置/ })).toBeInTheDocument();

    fireEvent.pointerDown(document.body);
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /任务配置/ })).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "打开工具菜单" }));
    fireEvent.click(await screen.findByRole("button", { name: /任务配置/ }));
    expect(await screen.findByLabelText("预设模式")).toBeInTheDocument();

    fireEvent.pointerDown(document.body);
    await waitFor(() => {
      expect(screen.queryByLabelText("预设模式")).not.toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /任务配置/ })).not.toBeInTheDocument();
  });

  it("offers quick starts and sends with Enter", async () => {
    render(<App />);

    await waitForWorkspaceData();

    fireEvent.click(screen.getByRole("button", { name: /代码工程/ }));

    expect(screen.getByLabelText("任务描述")).toHaveValue(
      "请帮我分析这个代码任务，并给出可执行的实现方案：",
    );
    expect(screen.getByLabelText("预设模式")).toHaveValue("code-engineering");
    expect(screen.getByLabelText("Skills")).toHaveValue("frontend-design");
    expect(screen.getByRole("button", { name: "深度分析" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    fireEvent.change(screen.getByLabelText("任务描述"), {
      target: { value: "用默认助手打个招呼" },
    });
    fireEvent.keyDown(screen.getByLabelText("任务描述"), {
      key: "Enter",
      code: "Enter",
      shiftKey: false,
    });

    await waitFor(() => {
      expect(api.submitTask).toHaveBeenCalled();
    });
  });

  it("submits selected model as role overrides for multi-agent presets", async () => {
    render(<App />);

    await waitForWorkspaceData();

    fireEvent.click(screen.getByRole("button", { name: "打开工具菜单" }));
    fireEvent.click(await screen.findByRole("button", { name: /任务配置/ }));
    fireEvent.change(screen.getByLabelText("预设模式"), {
      target: { value: "code-engineering" },
    });
    fireEvent.click(screen.getByRole("button", { name: "深度分析" }));
    fireEvent.click(screen.getByRole("button", { name: "联网" }));
    fireEvent.change(screen.getByLabelText("协调模型"), {
      target: { value: "gpt-5.4" },
    });
    fireEvent.change(screen.getByLabelText("Skills"), {
      target: { value: "frontend-design, gsd-do, frontend-design" },
    });
    fireEvent.change(screen.getByLabelText("任务描述"), {
      target: { value: "请验证模型路由" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送任务" }));

    await waitFor(() => {
      expect(api.submitTask).toHaveBeenCalledWith(
        expect.objectContaining({
          model_override: "gpt-5.4",
          role_model_overrides: {
            "project-manager": "gpt-5.4",
            backend: "gpt-5.4",
            frontend: "gpt-5.4",
            reviewer: "gpt-5.4",
          },
          tool_flags: {
            deep_analysis: true,
            web_search: true,
            code_execution: false,
            canvas: false,
          },
          skills: ["frontend-design", "gsd-do"],
          metadata: {},
        }),
      );
    });
  });

  it("keeps follow-up turns in the same conversation", async () => {
    vi.mocked(api.fetchHistoryTasks).mockResolvedValue([]);
    const submittedDetails: Record<string, TaskHistoryDetail> = {};
    vi.mocked(api.fetchTaskHistoryDetail).mockImplementation(async (taskId) => {
      return submittedDetails[taskId] || historyDetail;
    });
    vi.mocked(api.fetchConversationHistory).mockImplementation(async (conversationId) => {
      return Object.values(submittedDetails).filter(
        (detail) => detail.metadata.conversation_id === conversationId,
      );
    });
    let submissionIndex = 0;
    vi.mocked(api.submitTask).mockImplementation(async (payload) => {
      submissionIndex += 1;
      const taskId = `task-followup-${submissionIndex}`;
      const output = `回答 ${submissionIndex}`;
      submittedDetails[taskId] = {
        ...historyDetail,
        task_id: taskId,
        prompt: payload.prompt,
        status: "completed",
        provider: "mock-openhands",
        message: "已完成",
        output,
        error_message: null,
        request_payload: payload,
        metadata: {
          conversation_id: payload.conversation_id,
          conversation_history: payload.conversation_history || [],
        },
        stages: [],
        approval: null,
        requires_approval: false,
        approval_status: null,
      };
      return {
        status: "completed",
        message: "已完成",
        error_message: null,
        data: {
          output,
          provider: "mock-openhands",
          metadata: {
            task_id: taskId,
            conversation_id: payload.conversation_id,
          },
        },
      };
    });

    render(<App />);

    expect(await screen.findByText("GPT-5.4")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("任务描述"), {
      target: { value: "第一轮" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送任务" }));

    await waitFor(() => {
      expect(api.submitTask).toHaveBeenCalledTimes(1);
    });
    const firstPayload = vi.mocked(api.submitTask).mock.calls[0][0];
    expect(firstPayload.conversation_id).toMatch(/^conversation-/);
    expect(firstPayload.conversation_history).toEqual([]);
    expect((await screen.findAllByText("回答 1")).length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("任务描述"), {
      target: { value: "继续说明风险" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送任务" }));

    await waitFor(() => {
      expect(api.submitTask).toHaveBeenCalledTimes(2);
    });
    const secondPayload = vi.mocked(api.submitTask).mock.calls[1][0];
    expect(secondPayload.conversation_id).toBe(firstPayload.conversation_id);
    expect(secondPayload.conversation_history).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ role: "user", content: "第一轮" }),
        expect.objectContaining({ role: "assistant", content: "回答 1" }),
      ]),
    );
    expect((await screen.findAllByText("回答 2")).length).toBeGreaterThan(0);
    expect(screen.getByText("第一轮")).toBeInTheDocument();
    expect(screen.getByText("继续说明风险")).toBeInTheDocument();
  });

  it("uses the plus menu for configuration and uploads, then clears composer state for a new task", async () => {
    render(<App />);

    await waitForWorkspaceData();

    fireEvent.click(screen.getByRole("button", { name: "打开工具菜单" }));
    expect(await screen.findByRole("button", { name: /任务配置/ })).toBeInTheDocument();
    const fileInput = screen.getByLabelText("上传文件") as HTMLInputElement;
    const file = new File(["hello from fixture"], "notes.txt", { type: "text/plain" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(await screen.findByText("notes.txt")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("任务描述"), {
      target: { value: "新的临时任务" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^新任务$/ }));

    expect(screen.getByText(/开启一次新的 Mindforge 对话/)).toBeInTheDocument();
    expect(screen.getByLabelText("任务描述")).toHaveValue("");
    expect(screen.queryByText("notes.txt")).not.toBeInTheDocument();
  });

  it("submits uploaded files as structured attachments", async () => {
    render(<App />);

    await waitForWorkspaceData();

    fireEvent.click(screen.getByRole("button", { name: "打开工具菜单" }));
    const fileInput = await screen.findByLabelText("上传文件");
    const file = new File(["structured upload text"], "brief.md", {
      type: "text/markdown",
    });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(await screen.findByText("brief.md")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("任务描述"), {
      target: { value: "读取附件并总结" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送任务" }));

    await waitFor(() => {
      expect(api.submitTask).toHaveBeenCalledWith(
        expect.objectContaining({
          prompt: "读取附件并总结",
          attachments: [
            expect.objectContaining({
              id: "file-brief.md",
              file_id: "file-brief.md",
              name: "brief.md",
              mime_type: "text/markdown",
              size_bytes: file.size,
              text_excerpt: "structured upload text",
              parsed_status: "parsed",
              chunk_count: 1,
              metadata: expect.objectContaining({
                source: "composer-upload",
                truncated: false,
                has_text_excerpt: true,
                backend_file_id: "file-brief.md",
                parser: "plain-text",
              }),
            }),
          ],
        }),
      );
    });
  });

  it("only exposes user-added models in the coordinator selector", async () => {
    vi.mocked(api.fetchModels).mockResolvedValue([models[0], deepseekModel]);
    vi.mocked(api.fetchEditableModels).mockResolvedValue([deepseekModel]);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "打开工具菜单" }));
    fireEvent.click(await screen.findByRole("button", { name: /任务配置/ }));

    const coordinator = (await screen.findByLabelText(
      "协调模型",
    )) as HTMLSelectElement;

    await waitFor(() => {
      expect(coordinator.value).toBe("deepseek-v3.2");
    });
    expect(Array.from(coordinator.options).map((option) => option.value)).toEqual([
      "deepseek-v3.2",
    ]);
    expect(screen.queryByText("GPT-5.4 / openai")).not.toBeInTheDocument();
  });

  it("guides first-time users to add a model before submitting", async () => {
    vi.mocked(api.fetchModels).mockResolvedValue([]);
    vi.mocked(api.fetchEditableModels).mockResolvedValue([]);

    render(<App />);

    expect(await screen.findByText("先接入一个模型")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("任务描述"), {
      target: { value: "你好" },
    });
    fireEvent.click(screen.getByRole("button", { name: "先添加模型" }));

    expect(api.submitTask).not.toHaveBeenCalled();
    expect(await screen.findByText("模型控制中心")).toBeInTheDocument();
  });

  it("deletes a conversation from the sidebar", async () => {
    vi.mocked(api.fetchHistoryTasks).mockResolvedValue([
      {
        ...historyItems[0],
        conversation_id: "conversation-delete-1",
        conversation_turn_count: 2,
      },
    ]);

    render(<App />);

    expect(await screen.findByText("Implement login flow")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: /删除对话 Implement login flow/ }),
    );
    expect(await screen.findByText(/再次点击/)).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: /删除对话 Implement login flow/ }),
    );

    await waitFor(() => {
      expect(api.deleteConversationHistory).toHaveBeenCalledWith(
        "conversation-delete-1",
      );
    });
    expect(screen.queryByText("Implement login flow")).not.toBeInTheDocument();
  });

  it("edits and saves a canvas artifact", async () => {
    render(<App />);

    await openFirstHistoryConversation();

    fireEvent.click(screen.getByRole("tab", { name: "画布" }));
    const editor = await screen.findByLabelText("Mindforge 输出画布 内容");
    fireEvent.change(editor, { target: { value: "更新后的画布内容" } });
    fireEvent.click(screen.getByRole("button", { name: "保存画布" }));

    await waitFor(() => {
      expect(api.updateCanvasArtifact).toHaveBeenCalledWith(
        "task-1",
        "canvas-task-1",
        {
          title: "Mindforge 输出画布",
          content: "更新后的画布内容",
        },
      );
    });
  });

  it("shows tool center, loads MCP tools, and exports output documents", async () => {
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    render(<App />);

    await waitForWorkspaceData();
    expect(await screen.findByLabelText("底部模型选择")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: /工具/ })[0]);
    expect(await screen.findByText("工具与 Skills 中心")).toBeInTheDocument();
    expect(screen.getAllByText("frontend-design").length).toBeGreaterThan(0);
    expect(screen.getByText("调用需审批")).toBeInTheDocument();
    expect(screen.getByText("允许 1")).toBeInTheDocument();
    expect(screen.getByText("禁用 1")).toBeInTheDocument();
    expect(screen.getByText("MCP 调用审计")).toBeInTheDocument();
    expect(screen.getByText("tool_call_requires_approval")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "读取工具目录" }));

    await waitFor(() => {
      expect(api.fetchMcpTools).toHaveBeenCalledWith("filesystem");
    });
    await waitFor(() => {
      expect(screen.getAllByText("read_file").length).toBeGreaterThan(0);
    });

    fireEvent.change(screen.getByLabelText("Server ID"), {
      target: { value: "browser" },
    });
    fireEvent.change(screen.getByLabelText("显示名称"), {
      target: { value: "Browser MCP" },
    });
    fireEvent.change(screen.getByLabelText("Endpoint URL"), {
      target: { value: "http://127.0.0.1:9000/mcp" },
    });
    fireEvent.change(screen.getByLabelText("允许工具"), {
      target: { value: "search, summarize" },
    });
    fireEvent.change(screen.getByLabelText("禁用工具"), {
      target: { value: "delete_file" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存 MCP Server" }));

    await waitFor(() => {
      expect(api.createMcpServer).toHaveBeenCalledWith(
        expect.objectContaining({
          server_id: "browser",
          display_name: "Browser MCP",
          endpoint_url: "http://127.0.0.1:9000/mcp",
          allowed_tools: ["search", "summarize"],
          blocked_tools: ["delete_file"],
          tool_call_requires_approval: true,
        }),
      );
    });

    await openFirstHistoryConversation();
    expect(await screen.findByText("自动生成的文件")).toBeInTheDocument();
    expect(screen.getByText("mindforge-output.md")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "导出 MD" }));

    await waitFor(() => {
      expect(api.exportArtifact).toHaveBeenCalledWith(
        expect.objectContaining({
          format: "md",
          source_task_id: "task-1",
        }),
      );
    });
    expect(openSpy).toHaveBeenCalled();
    openSpy.mockRestore();
  });

  it("manages project spaces and sends selected project context with tasks", async () => {
    render(<App />);

    await waitForWorkspaceData();
    fireEvent.click(screen.getByRole("button", { name: "项目 空间" }));
    expect(await screen.findByText("项目空间")).toBeInTheDocument();
    expect(screen.getByText("Mindforge Dev")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Project ID"), {
      target: { value: "paper-lab" },
    });
    fireEvent.change(screen.getByLabelText("项目名称"), {
      target: { value: "Paper Lab" },
    });
    fireEvent.change(screen.getByLabelText("项目指令"), {
      target: { value: "按期刊论文标准写作。" },
    });
    fireEvent.change(screen.getByLabelText("项目记忆"), {
      target: { value: "偏好中文解释。" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存项目空间" }));

    await waitFor(() => {
      expect(api.createProjectSpace).toHaveBeenCalledWith(
        expect.objectContaining({
          project_id: "paper-lab",
          display_name: "Paper Lab",
          instructions: "按期刊论文标准写作。",
          memory: "偏好中文解释。",
        }),
      );
    });

    fireEvent.click(screen.getAllByRole("button", { name: "用于新任务" })[0]);
    fireEvent.change(screen.getByLabelText("任务描述"), {
      target: { value: "继续优化这个项目" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送任务" }));

    await waitFor(() => {
      expect(api.submitTask).toHaveBeenCalledWith(
        expect.objectContaining({
          project_id: "paper-lab",
        }),
      );
    });
  });

  it("switches into model control and rule template views", async () => {
    render(<App />);

    await waitForWorkspaceData();

    fireEvent.click(screen.getByRole("button", { name: "模型 控制" }));
    expect(await screen.findByText("模型控制中心")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存模型设置" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "模板 规则" }));
    expect(await screen.findByText("规则模板")).toBeInTheDocument();
    expect(screen.getByText("模板编辑器")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存模板" })).toBeInTheDocument();
  });

  it("edits provider controls and tests a provider connection", async () => {
    render(<App />);

    await waitForWorkspaceData();

    fireEvent.click(screen.getByRole("button", { name: "模型 控制" }));
    expect(await screen.findByText("模型服务商/API 管理")).toBeInTheDocument();
    expect(screen.getByText("已配置")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("OpenAI 启用状态"));
    fireEvent.change(screen.getByLabelText("OpenAI 基础 URL"), {
      target: { value: "https://proxy.example/v1" },
    });
    fireEvent.change(screen.getByLabelText("OpenAI 协议"), {
      target: { value: "openai-compatible" },
    });
    fireEvent.change(screen.getByLabelText("OpenAI API key"), {
      target: { value: "direct-secret" },
    });
    fireEvent.change(screen.getByLabelText("OpenAI API key 环境变量"), {
      target: { value: "OPENAI_PROXY_KEY" },
    });
    fireEvent.change(screen.getByLabelText("OpenAI Anthropic URL"), {
      target: { value: "https://anthropic.proxy.example" },
    });

    fireEvent.click(screen.getByRole("button", { name: "保存 OpenAI 模型服务商" }));

    await waitFor(() => {
      expect(api.updateProviderControl).toHaveBeenCalledWith("openai", {
        display_name: "OpenAI",
        description: "主力 Provider",
        enabled: false,
        api_base_url: "https://proxy.example/v1",
        protocol: "openai-compatible",
        api_key_env: "OPENAI_PROXY_KEY",
        api_key: "direct-secret",
        anthropic_api_base_url: "https://anthropic.proxy.example",
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "测试 OpenAI 连接" }));

    await waitFor(() => {
      expect(api.testProviderConnection).toHaveBeenCalledWith("openai");
    });
    expect(await screen.findByText("已连接：连接正常")).toBeInTheDocument();
  });

  it("renders GitHub and approval panels and can approve a pending task", async () => {
    render(<App />);

    await openFirstHistoryConversation();

    fireEvent.click(screen.getByRole("tab", { name: "GitHub" }));
    expect(await screen.findByText("GitHub 上下文")).toBeInTheDocument();
    expect(screen.getByText("openai/openai-python")).toBeInTheDocument();
    expect(screen.getByText("Issue #123")).toBeInTheDocument();
    expect(screen.getByText("PR #9")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "论文" }));
    expect(await screen.findByText("论文上下文")).toBeInTheDocument();
    expect(screen.getByText("Example Journal")).toBeInTheDocument();
    expect(screen.getByText("参考论文 1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "审批" }));
    expect(await screen.findByText("写入操作前需要审批。")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "批准并继续" }));

    await waitFor(() => {
      expect(api.approveTask).toHaveBeenCalledWith("task-1", "从工作台批准。");
    });
  });
});
