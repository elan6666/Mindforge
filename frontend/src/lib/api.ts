import type {
  ApprovalRecord,
  ArtifactFormat,
  ArtifactSummary,
  GitHubIssueSummary,
  GitHubPullRequestSummary,
  GitHubRepositorySummary,
  MCPServerSummary,
  MCPServerUpsert,
  MCPToolAuditRecord,
  MCPToolListResult,
  ModelCreateRequest,
  ModelControlUpdate,
  ModelSummary,
  PresetSummary,
  ProjectSpaceSummary,
  ProjectSpaceUpsert,
  ProviderConnectionTestResult,
  ProviderCreateRequest,
  ProviderControlUpdate,
  ProviderSummary,
  RuleTemplateSummary,
  RuleTemplateUpsert,
  SkillSettingsUpdate,
  SkillSummary,
  TaskHistoryDetail,
  TaskHistorySummary,
  TaskResult,
  UploadedFileSummary,
} from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || "http://127.0.0.1:8000/api";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    ...init,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(
      payload.error_message || payload.message || payload.detail || "请求失败。",
    );
  }
  return payload as T;
}

async function requestForm<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(
      payload.error_message || payload.message || payload.detail || "请求失败。",
    );
  }
  return payload as T;
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

export function fetchPresets(): Promise<PresetSummary[]> {
  return requestJson<PresetSummary[]>("/presets");
}

export function fetchProviders(): Promise<ProviderSummary[]> {
  return requestJson<ProviderSummary[]>("/control/providers");
}

export function fetchUserProviders(): Promise<ProviderSummary[]> {
  return requestJson<ProviderSummary[]>("/control/user-providers");
}

export function createProviderControl(
  payload: ProviderCreateRequest,
): Promise<ProviderSummary> {
  return requestJson<ProviderSummary>("/control/providers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateProviderControl(
  providerId: string,
  payload: ProviderControlUpdate,
): Promise<ProviderSummary> {
  return requestJson<ProviderSummary>(`/control/providers/${providerId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteProviderControl(providerId: string): Promise<void> {
  return requestJson<void>(`/control/providers/${providerId}`, {
    method: "DELETE",
  });
}

export function testProviderConnection(
  providerId: string,
): Promise<ProviderConnectionTestResult> {
  return requestJson<ProviderConnectionTestResult>(
    `/control/providers/${providerId}/test`,
    {
      method: "POST",
    },
  );
}

export function fetchModels(): Promise<ModelSummary[]> {
  return requestJson<ModelSummary[]>("/models");
}

export function fetchEditableModels(): Promise<ModelSummary[]> {
  return requestJson<ModelSummary[]>("/control/user-models");
}

export function createModelControl(
  payload: ModelCreateRequest,
): Promise<ModelSummary> {
  return requestJson<ModelSummary>("/control/models", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateModelControl(
  modelId: string,
  payload: ModelControlUpdate,
): Promise<ModelSummary> {
  return requestJson<ModelSummary>(`/control/models/${modelId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteModelControl(modelId: string): Promise<void> {
  return requestJson<void>(`/control/models/${modelId}`, {
    method: "DELETE",
  });
}

export function fetchRuleTemplates(): Promise<RuleTemplateSummary[]> {
  return requestJson<RuleTemplateSummary[]>("/control/rule-templates");
}

export function createRuleTemplate(
  payload: RuleTemplateUpsert,
): Promise<RuleTemplateSummary> {
  return requestJson<RuleTemplateSummary>("/control/rule-templates", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateRuleTemplate(
  templateId: string,
  payload: RuleTemplateUpsert,
): Promise<RuleTemplateSummary> {
  return requestJson<RuleTemplateSummary>(`/control/rule-templates/${templateId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteRuleTemplate(templateId: string): Promise<void> {
  return requestJson<void>(`/control/rule-templates/${templateId}`, {
    method: "DELETE",
  });
}

export function fetchHistoryTasks(status?: string): Promise<TaskHistorySummary[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return requestJson<TaskHistorySummary[]>(`/history/tasks${query}`);
}

export function fetchTaskHistoryDetail(taskId: string): Promise<TaskHistoryDetail> {
  return requestJson<TaskHistoryDetail>(`/history/tasks/${taskId}`);
}

export function deleteHistoryTask(taskId: string): Promise<void> {
  return requestJson<void>(`/history/tasks/${encodeURIComponent(taskId)}`, {
    method: "DELETE",
  });
}

export function updateCanvasArtifact(
  taskId: string,
  artifactId: string,
  payload: { title?: string | null; content: unknown },
): Promise<TaskHistoryDetail> {
  return requestJson<TaskHistoryDetail>(
    `/history/tasks/${encodeURIComponent(taskId)}/canvas-artifacts/${encodeURIComponent(
      artifactId,
    )}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
}

export function fetchConversationHistory(
  conversationId: string,
): Promise<TaskHistoryDetail[]> {
  return requestJson<TaskHistoryDetail[]>(
    `/history/conversations/${encodeURIComponent(conversationId)}/tasks`,
  );
}

export function deleteConversationHistory(conversationId: string): Promise<void> {
  return requestJson<void>(
    `/history/conversations/${encodeURIComponent(conversationId)}`,
    {
      method: "DELETE",
    },
  );
}

export function fetchPendingApprovals(): Promise<ApprovalRecord[]> {
  return requestJson<ApprovalRecord[]>("/approvals/pending");
}

export function fetchSkills(): Promise<SkillSummary[]> {
  return requestJson<SkillSummary[]>("/skills");
}

export function updateSkillSettings(
  skillId: string,
  payload: SkillSettingsUpdate,
): Promise<SkillSummary> {
  return requestJson<SkillSummary>(`/skills/${encodeURIComponent(skillId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function fetchProjectSpaces(): Promise<ProjectSpaceSummary[]> {
  return requestJson<ProjectSpaceSummary[]>("/projects");
}

export function createProjectSpace(
  payload: ProjectSpaceUpsert,
): Promise<ProjectSpaceSummary> {
  return requestJson<ProjectSpaceSummary>("/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteProjectSpace(projectId: string): Promise<void> {
  return requestJson<void>(`/projects/${encodeURIComponent(projectId)}`, {
    method: "DELETE",
  });
}

export function fetchMcpServers(): Promise<MCPServerSummary[]> {
  return requestJson<MCPServerSummary[]>("/mcp/servers");
}

export function fetchMcpAudit(): Promise<MCPToolAuditRecord[]> {
  return requestJson<MCPToolAuditRecord[]>("/mcp/audit");
}

export function createMcpServer(
  payload: MCPServerUpsert,
): Promise<MCPServerSummary> {
  return requestJson<MCPServerSummary>("/mcp/servers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteMcpServer(serverId: string): Promise<void> {
  return requestJson<void>(`/mcp/servers/${encodeURIComponent(serverId)}`, {
    method: "DELETE",
  });
}

export function fetchMcpTools(serverId: string): Promise<MCPToolListResult> {
  return requestJson<MCPToolListResult>(
    `/mcp/servers/${encodeURIComponent(serverId)}/tools`,
  );
}

export function uploadFile(file: File): Promise<UploadedFileSummary> {
  const formData = new FormData();
  formData.append("file", file);
  return requestForm<UploadedFileSummary>("/files", formData);
}

export function exportArtifact(payload: {
  title: string;
  content: string;
  format: ArtifactFormat;
  source_task_id?: string | null;
}): Promise<ArtifactSummary> {
  return requestJson<ArtifactSummary>("/artifacts/export", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function approveTask(taskId: string, comment?: string): Promise<TaskResult> {
  return requestJson<TaskResult>(`/approvals/${taskId}/approve`, {
    method: "POST",
    body: JSON.stringify({ comment }),
  });
}

export function rejectTask(taskId: string, comment?: string): Promise<TaskResult> {
  return requestJson<TaskResult>(`/approvals/${taskId}/reject`, {
    method: "POST",
    body: JSON.stringify({ comment }),
  });
}

export function fetchGitHubRepository(
  owner: string,
  repo: string,
): Promise<GitHubRepositorySummary> {
  return requestJson<GitHubRepositorySummary>(`/github/repositories/${owner}/${repo}`);
}

export function fetchGitHubIssue(
  owner: string,
  repo: string,
  issueNumber: number,
): Promise<GitHubIssueSummary> {
  return requestJson<GitHubIssueSummary>(
    `/github/repositories/${owner}/${repo}/issues/${issueNumber}`,
  );
}

export function fetchGitHubPullRequest(
  owner: string,
  repo: string,
  prNumber: number,
): Promise<GitHubPullRequestSummary> {
  return requestJson<GitHubPullRequestSummary>(
    `/github/repositories/${owner}/${repo}/pulls/${prNumber}`,
  );
}

export function submitTask(payload: {
  prompt: string;
  preset_mode: string;
  repo_path?: string | null;
  task_type?: string | null;
  model_override?: string | null;
  rule_template_id?: string | null;
  project_id?: string | null;
  github_repo?: string | null;
  github_issue_number?: number | null;
  github_pr_number?: number | null;
  conversation_id?: string | null;
  conversation_history?: Array<{
    role: "user" | "assistant" | "system" | string;
    content: string;
    task_id?: string | null;
    created_at?: string | null;
    metadata?: Record<string, unknown>;
  }>;
  skills?: string[];
  mcp_server_ids?: string[];
  journal_name?: string | null;
  journal_url?: string | null;
  reference_paper_urls?: string[];
  role_model_overrides?: Record<string, string>;
  attachments?: Array<{
    id?: string | null;
    file_id?: string | null;
    name?: string | null;
    mime_type?: string | null;
    size_bytes?: number | null;
    text_excerpt?: string | null;
    parsed_status?: string | null;
    chunk_count?: number | null;
    metadata?: Record<string, unknown>;
  }>;
  tool_flags?: {
    web_search?: boolean | null;
    deep_analysis?: boolean | null;
    code_execution?: boolean | null;
    canvas?: boolean | null;
  };
  metadata?: Record<string, unknown>;
}): Promise<TaskResult> {
  return requestJson<TaskResult>("/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
