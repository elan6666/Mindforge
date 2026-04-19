export type PresetSummary = {
  preset_mode: string;
  display_name: string;
  description: string;
  requires_repo_analysis: boolean;
  requires_approval: boolean;
};

export type ProviderSummary = {
  provider_id: string;
  display_name: string;
  description: string;
  enabled: boolean;
};

export type ModelSummary = {
  model_id: string;
  display_name: string;
  provider_id: string;
  upstream_model: string;
  priority: "high" | "medium" | "low" | "disabled";
  enabled: boolean;
  supported_preset_modes: string[];
  supported_task_types: string[];
  supported_roles: string[];
};

export type ModelControlUpdate = {
  priority?: "high" | "medium" | "low" | "disabled";
  enabled?: boolean;
};

export type RuleAssignment = {
  role: string;
  responsibility: string;
  model_id: string;
};

export type RuleTemplateSummary = {
  template_id: string;
  display_name: string;
  description: string;
  preset_mode: string;
  task_types: string[];
  default_coordinator_model_id: string;
  enabled: boolean;
  is_default: boolean;
  trigger_keywords: string[];
  assignments: RuleAssignment[];
  notes: string;
};

export type RuleTemplateUpsert = RuleTemplateSummary;

export type ApprovalRecord = {
  approval_id: string;
  task_id: string;
  status: string;
  risk_level: string;
  summary: string;
  actions: string[];
  decision_comment?: string | null;
  created_at: string;
  updated_at: string;
};

export type StageTrace = {
  order: number;
  stage_id: string;
  stage_name: string;
  role: string;
  model: string;
  status: string;
  provider: string;
  summary: string;
  output: string;
  metadata: Record<string, unknown>;
  error_message?: string | null;
};

export type OrchestrationTrace = {
  preset_mode: string;
  strategy: string;
  total_stages: number;
  completed_stages: number;
  failed_stage?: string | null;
  stages: StageTrace[];
};

export type RepoAnalysis = {
  status: string;
  repo_summary?: {
    summary_text: string;
    entrypoints: string[];
    detected_stack: string[];
    key_files: Array<{ path: string; category: string }>;
  } | null;
  warnings?: string[];
  error_message?: string | null;
};

export type TaskResult = {
  status: string;
  message: string;
  error_message?: string | null;
  data: {
    output: string;
    provider: string;
    metadata: {
      task_id?: string;
      resolved_preset_mode?: string;
      task_model_selection?: {
        model_id: string;
        provider_id: string;
        selection_source: string;
      };
      rule_template_selection?: {
        template_id: string;
        display_name: string;
        preset_mode: string;
        selection_source: string;
        coordinator_model_id: string;
        matched_keywords: string[];
        role_model_overrides: Record<string, string>;
      } | null;
      effective_role_model_overrides?: Record<string, string>;
      orchestration?: OrchestrationTrace;
      repo_analysis?: RepoAnalysis | null;
      approval?: ApprovalRecord | null;
      [key: string]: unknown;
    };
  };
};

export type TaskHistorySummary = {
  task_id: string;
  prompt: string;
  preset_mode: string;
  task_type?: string | null;
  status: string;
  provider?: string | null;
  created_at: string;
  updated_at: string;
  requires_approval: boolean;
  approval_status?: string | null;
};

export type StageHistoryRecord = {
  order: number;
  stage_id: string;
  stage_name: string;
  role: string;
  model: string;
  provider?: string | null;
  status: string;
  summary: string;
  output: string;
  metadata: Record<string, unknown>;
  error_message?: string | null;
  created_at: string;
};

export type TaskHistoryDetail = TaskHistorySummary & {
  repo_path?: string | null;
  message: string;
  output: string;
  error_message?: string | null;
  request_payload: Record<string, unknown>;
  metadata: {
    orchestration?: OrchestrationTrace;
    repo_analysis?: RepoAnalysis | null;
    approval?: ApprovalRecord | null;
    [key: string]: unknown;
  };
  stages: StageHistoryRecord[];
  approval?: ApprovalRecord | null;
};
