import type {
  ApprovalRecord,
  ModelControlUpdate,
  ModelSummary,
  PresetSummary,
  ProviderSummary,
  RuleTemplateSummary,
  RuleTemplateUpsert,
  TaskHistoryDetail,
  TaskHistorySummary,
  TaskResult,
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
      payload.error_message || payload.message || payload.detail || "Request failed.",
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
  return requestJson<ProviderSummary[]>("/providers");
}

export function fetchModels(): Promise<ModelSummary[]> {
  return requestJson<ModelSummary[]>("/models");
}

export function fetchEditableModels(): Promise<ModelSummary[]> {
  return requestJson<ModelSummary[]>("/control/models");
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

export function fetchPendingApprovals(): Promise<ApprovalRecord[]> {
  return requestJson<ApprovalRecord[]>("/approvals/pending");
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

export function submitTask(payload: {
  prompt: string;
  preset_mode: string;
  repo_path?: string | null;
  task_type?: string | null;
  model_override?: string | null;
  rule_template_id?: string | null;
  metadata?: Record<string, unknown>;
}): Promise<TaskResult> {
  return requestJson<TaskResult>("/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
