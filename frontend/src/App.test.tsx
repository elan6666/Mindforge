import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import * as api from "./lib/api";
import type {
  ApprovalRecord,
  ModelSummary,
  PresetSummary,
  ProviderSummary,
  RuleTemplateSummary,
  TaskHistoryDetail,
  TaskHistorySummary,
  TaskResult,
} from "./types";

vi.mock("./lib/api", () => ({
  approveTask: vi.fn(),
  createRuleTemplate: vi.fn(),
  deleteRuleTemplate: vi.fn(),
  fetchEditableModels: vi.fn(),
  fetchHistoryTasks: vi.fn(),
  fetchPendingApprovals: vi.fn(),
  fetchPresets: vi.fn(),
  fetchProviders: vi.fn(),
  fetchRuleTemplates: vi.fn(),
  fetchTaskHistoryDetail: vi.fn(),
  getApiBaseUrl: vi.fn(() => "http://127.0.0.1:8000/api"),
  rejectTask: vi.fn(),
  submitTask: vi.fn(),
  testProviderConnection: vi.fn(),
  updateModelControl: vi.fn(),
  updateProviderControl: vi.fn(),
  updateRuleTemplate: vi.fn(),
}));

const presets: PresetSummary[] = [
  {
    preset_mode: "code-engineering",
    display_name: "Code Engineering",
    description: "Coordinate planning, backend, frontend, and review.",
    requires_repo_analysis: true,
    requires_approval: false,
  },
];

const providers: ProviderSummary[] = [
  {
    provider_id: "openai",
    display_name: "OpenAI",
    description: "Primary provider",
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

const ruleTemplates: RuleTemplateSummary[] = [
  {
    template_id: "code-engineering-default",
    display_name: "Code Engineering Default",
    description: "Default template",
    preset_mode: "code-engineering",
    task_types: ["planning"],
    default_coordinator_model_id: "gpt-5.4",
    enabled: true,
    is_default: true,
    trigger_keywords: ["login"],
    assignments: [
      {
        role: "frontend",
        responsibility: "UI implementation",
        model_id: "gpt-5.4",
      },
    ],
    notes: "Default template",
  },
];

const approval: ApprovalRecord = {
  approval_id: "approval-1",
  task_id: "task-1",
  status: "pending",
  risk_level: "high",
  summary: "Needs approval before write actions.",
  actions: ["write files", "execute shell"],
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
  message: "Waiting for approval.",
  output: "Staged execution result",
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
          summary: "Created an execution plan.",
          output: "Plan output",
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
        body_excerpt: "Issue context",
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
        body_excerpt: "PR context",
      },
    },
    academic_context: {
      journal: {
        journal_name: "Example Journal",
        journal_url: "https://journal.example/guidelines",
        title: "Author Guidelines",
        excerpt: "Use structured abstracts and concise academic English.",
        status: "fetched",
        error_message: null,
      },
      reference_papers: [
        {
          url: "https://paper.example/reference",
          title: "Reference Paper",
          excerpt: "Contribution-first structure.",
          status: "fetched",
          error_message: null,
        },
      ],
      warnings: [],
    },
    approval,
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
      summary: "Created an execution plan.",
      output: "Plan output",
      metadata: {},
      error_message: null,
      created_at: "2026-04-21T10:00:00+08:00",
    },
  ],
  approval,
};

const approvalResult: TaskResult = {
  status: "completed",
  message: "Approved",
  error_message: null,
  data: {
    output: "Approved output",
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
  vi.mocked(api.fetchEditableModels).mockResolvedValue(models);
  vi.mocked(api.fetchRuleTemplates).mockResolvedValue(ruleTemplates);
  vi.mocked(api.fetchHistoryTasks).mockResolvedValue(historyItems);
  vi.mocked(api.fetchPendingApprovals).mockResolvedValue([approval]);
  vi.mocked(api.fetchTaskHistoryDetail).mockResolvedValue(historyDetail);
  vi.mocked(api.approveTask).mockResolvedValue(approvalResult);
  vi.mocked(api.rejectTask).mockResolvedValue({
    ...approvalResult,
    status: "rejected",
  });
  vi.mocked(api.updateModelControl).mockResolvedValue(models[0]);
  vi.mocked(api.updateProviderControl).mockImplementation(async (providerId, payload) => ({
    ...providers[0],
    ...payload,
    provider_id: providerId,
  }));
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
    message: "Submitted",
    error_message: null,
    data: {
      output: "Submitted output",
      provider: "mock-openhands",
      metadata: {
        task_id: "task-1",
      },
    },
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

    await waitFor(() => {
      expect(api.fetchTaskHistoryDetail).toHaveBeenCalledWith("task-1");
    });

    expect(screen.getByText("Mindforge Control Workspace")).toBeInTheDocument();
    expect(screen.getByText("Task Workspace")).toBeInTheDocument();
    expect(screen.getByText("Pending approvals")).toBeInTheDocument();
    expect(screen.getByText("1 pending")).toBeInTheDocument();
    expect(screen.getByText("OpenAI")).toBeInTheDocument();
    expect(screen.getByText("http://127.0.0.1:8000/api")).toBeInTheDocument();
  });

  it("switches into model control and rule template views", async () => {
    render(<App />);

    await waitFor(() => {
      expect(api.fetchTaskHistoryDetail).toHaveBeenCalledWith("task-1");
    });

    fireEvent.click(screen.getByRole("button", { name: "Models Control" }));
    expect(await screen.findByText("Model Control Center")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save model settings" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Templates Rules" }));
    expect(await screen.findByText("Rule Templates")).toBeInTheDocument();
    expect(screen.getByText("Template Editor")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save template" })).toBeInTheDocument();
  });

  it("edits provider controls and tests a provider connection", async () => {
    render(<App />);

    await waitFor(() => {
      expect(api.fetchTaskHistoryDetail).toHaveBeenCalledWith("task-1");
    });

    fireEvent.click(screen.getByRole("button", { name: "Models Control" }));
    expect(await screen.findByText("Provider/API Management")).toBeInTheDocument();
    expect(screen.getByText("Configured")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("OpenAI enabled"));
    fireEvent.change(screen.getByLabelText("OpenAI base URL"), {
      target: { value: "https://proxy.example/v1" },
    });
    fireEvent.change(screen.getByLabelText("OpenAI protocol"), {
      target: { value: "openai-compatible" },
    });
    fireEvent.change(screen.getByLabelText("OpenAI API key environment variable"), {
      target: { value: "OPENAI_PROXY_KEY" },
    });
    fireEvent.change(screen.getByLabelText("OpenAI Anthropic URL"), {
      target: { value: "https://anthropic.proxy.example" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save OpenAI provider" }));

    await waitFor(() => {
      expect(api.updateProviderControl).toHaveBeenCalledWith("openai", {
        enabled: false,
        api_base_url: "https://proxy.example/v1",
        protocol: "openai-compatible",
        api_key_env: "OPENAI_PROXY_KEY",
        anthropic_api_base_url: "https://anthropic.proxy.example",
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "Test OpenAI connection" }));

    await waitFor(() => {
      expect(api.testProviderConnection).toHaveBeenCalledWith("openai");
    });
    expect(await screen.findByText("connected: Connection OK")).toBeInTheDocument();
  });

  it("renders GitHub and approval panels and can approve a pending task", async () => {
    render(<App />);

    await waitFor(() => {
      expect(api.fetchTaskHistoryDetail).toHaveBeenCalledWith("task-1");
    });

    fireEvent.click(screen.getByRole("button", { name: "github" }));
    expect(await screen.findByText("GitHub Context")).toBeInTheDocument();
    expect(screen.getByText("openai/openai-python")).toBeInTheDocument();
    expect(screen.getByText("Issue #123")).toBeInTheDocument();
    expect(screen.getByText("PR #9")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "academic" }));
    expect(await screen.findByText("Academic Context")).toBeInTheDocument();
    expect(screen.getByText("Example Journal")).toBeInTheDocument();
    expect(screen.getByText("Reference paper 1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "approval" }));
    expect(await screen.findByText("Needs approval before write actions.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Approve and continue" }));

    await waitFor(() => {
      expect(api.approveTask).toHaveBeenCalledWith("task-1", "Approved from workspace");
    });
  });
});
