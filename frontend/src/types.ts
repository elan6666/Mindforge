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
  description?: string;
  enabled: boolean;
  api_base_url?: string | null;
  protocol?: string | null;
  api_key_env?: string | null;
  api_key_configured?: boolean;
  anthropic_api_base_url?: string | null;
  is_custom?: boolean;
};

export type ProviderControlUpdate = {
  display_name?: string | null;
  description?: string | null;
  enabled?: boolean;
  api_base_url?: string | null;
  protocol?: string | null;
  api_key_env?: string | null;
  api_key?: string | null;
  anthropic_api_base_url?: string | null;
};

export type ProviderCreateRequest = {
  provider_id: string;
  display_name: string;
  description?: string;
  enabled: boolean;
  api_base_url?: string | null;
  protocol?: string | null;
  api_key_env?: string | null;
  api_key?: string | null;
  anthropic_api_base_url?: string | null;
};

export type ProviderConnectionTestResult = {
  provider_id: string;
  ok: boolean;
  status: string;
  detail: string;
  protocol: string;
  api_base_url?: string | null;
  api_key_env?: string | null;
  api_key_configured: boolean;
  upstream_status?: number | null;
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
  is_custom?: boolean;
};

export type ModelControlUpdate = {
  display_name?: string | null;
  provider_id?: string | null;
  upstream_model?: string | null;
  priority?: "high" | "medium" | "low" | "disabled";
  enabled?: boolean;
  supported_preset_modes?: string[];
  supported_task_types?: string[];
  supported_roles?: string[];
};

export type ModelCreateRequest = {
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

export type GitHubRepositorySummary = {
  owner: string;
  name: string;
  full_name: string;
  description?: string | null;
  html_url: string;
  default_branch: string;
  primary_language?: string | null;
  stargazers_count: number;
  forks_count: number;
  open_issues_count: number;
  visibility?: string | null;
};

export type GitHubIssueSummary = {
  number: number;
  title: string;
  state: string;
  html_url: string;
  author?: string | null;
  labels: string[];
  comment_count: number;
  body_excerpt: string;
};

export type GitHubPullRequestSummary = {
  number: number;
  title: string;
  state: string;
  html_url: string;
  author?: string | null;
  labels: string[];
  comment_count: number;
  review_comment_count: number;
  draft: boolean;
  merged: boolean;
  head_ref?: string | null;
  base_ref?: string | null;
  body_excerpt: string;
};

export type GitHubContextSummary = {
  repository?: GitHubRepositorySummary | null;
  issue?: GitHubIssueSummary | null;
  pull_request?: GitHubPullRequestSummary | null;
};

export type JournalGuidelineSummary = {
  journal_name?: string | null;
  journal_url?: string | null;
  title?: string | null;
  excerpt: string;
  status: string;
  error_message?: string | null;
};

export type ReferencePaperSummary = {
  url: string;
  title?: string | null;
  excerpt: string;
  status: string;
  error_message?: string | null;
};

export type AcademicContextSummary = {
  journal?: JournalGuidelineSummary | null;
  reference_papers: ReferencePaperSummary[];
  warnings: string[];
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
      github_context?: GitHubContextSummary | null;
      academic_context?: AcademicContextSummary | null;
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
    github_context?: GitHubContextSummary | null;
    academic_context?: AcademicContextSummary | null;
    approval?: ApprovalRecord | null;
    [key: string]: unknown;
  };
  stages: StageHistoryRecord[];
  approval?: ApprovalRecord | null;
};
