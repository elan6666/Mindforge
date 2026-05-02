import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
} from "react";
import {
  approveTask,
  createMcpServer,
  createModelControl,
  createProjectSpace,
  createProviderControl,
  createRuleTemplate,
  deleteConversationHistory,
  deleteHistoryTask,
  deleteMcpServer,
  deleteModelControl,
  deleteProjectSpace,
  deleteProviderControl,
  deleteRuleTemplate,
  exportArtifact,
  fetchConversationHistory,
  fetchEditableModels,
  fetchHistoryTasks,
  fetchMcpServers,
  fetchMcpAudit,
  fetchMcpTools,
  fetchModels,
  fetchPendingApprovals,
  fetchPresets,
  fetchProjectSpaces,
  fetchSkills,
  fetchUserProviders,
  fetchRuleTemplates,
  fetchTaskHistoryDetail,
  getApiBaseUrl,
  rejectTask,
  submitTask,
  testProviderConnection,
  updateSkillSettings,
  uploadFile,
  updateCanvasArtifact,
  updateModelControl,
  updateProviderControl,
  updateRuleTemplate,
} from "./lib/api";
import type {
  ApprovalRecord,
  ArtifactFormat,
  ArtifactSummary,
  CanvasArtifact,
  MCPServerSummary,
  MCPServerUpsert,
  MCPToolAuditRecord,
  MCPToolListResult,
  ModelCreateRequest,
  ModelSummary,
  ProjectSpaceSummary,
  ProjectSpaceUpsert,
  ProviderCreateRequest,
  PresetSummary,
  ProviderSummary,
  RuleAssignment,
  RuleTemplateSummary,
  SkillSummary,
  TaskHistoryDetail,
  TaskHistorySummary,
  TaskResult,
  UploadedFileSummary,
} from "./types";

type PanelTab =
  | "output"
  | "stages"
  | "repo"
  | "github"
  | "academic"
  | "approval"
  | "canvas"
  | "metadata";
type AppView = "workspace" | "models" | "rules" | "tools" | "projects";
type HistoryFilter = "all" | "completed" | "pending_approval" | "failed" | "rejected";
type ProviderTestMessage = { status: "success" | "error"; text: string };
type MCPServerDraft = {
  server_id: string;
  display_name: string;
  transport: "http-jsonrpc" | "stdio";
  endpoint_url: string;
  command: string;
  args: string;
  env_json: string;
  working_directory: string;
  enabled: boolean;
  headers_json: string;
  allowed_tools: string;
  blocked_tools: string;
  tool_call_requires_approval: boolean;
  notes: string;
};
type ProjectSpaceDraft = {
  project_id: string;
  display_name: string;
  description: string;
  instructions: string;
  memory: string;
  default_preset_mode: string;
  repo_path: string;
  github_repo: string;
  skill_ids: string;
  mcp_server_ids: string;
  file_ids: string;
  tags: string;
  enabled: boolean;
};
type ChatAttachment = {
  id: string;
  fileId?: string;
  name: string;
  size: number;
  type: string;
  contentExcerpt?: string;
  truncated?: boolean;
  parsedStatus?: string;
  chunkCount?: number;
  parser?: string;
  uploadError?: string;
};
type ChatMessageRole = "user" | "assistant" | "system";
type ChatMessage = {
  id: string;
  role: ChatMessageRole;
  content: string;
  taskId?: string;
  createdAt?: string;
  status?: string;
};
type PresetFieldConfig = {
  showRepoPath: boolean;
  showGitHub: boolean;
  showAcademic: boolean;
  showApproval: boolean;
  taskTypes: string[];
};
type ComposerCapabilityKey =
  | "deep_analysis"
  | "web_search"
  | "code_execution"
  | "canvas";
type QuickStartAction = {
  label: string;
  description: string;
  prompt: string;
  presetMode: string;
  taskType?: string;
  skills?: string;
  flags?: Partial<Record<ComposerCapabilityKey, boolean>>;
};

const COMPOSER_CAPABILITIES: Array<{
  key: ComposerCapabilityKey;
  label: string;
  hint: string;
}> = [
  { key: "deep_analysis", label: "深度分析", hint: "请求更长推理链路" },
  { key: "web_search", label: "联网", hint: "把联网能力作为任务偏好发送" },
  { key: "code_execution", label: "代码执行", hint: "允许执行代码的任务偏好" },
  { key: "canvas", label: "画布", hint: "需要可视化或文档画布" },
];

const DEFAULT_CAPABILITY_FLAGS: Record<ComposerCapabilityKey, boolean> = {
  deep_analysis: false,
  web_search: false,
  code_execution: false,
  canvas: false,
};

const QUICK_START_ACTIONS: QuickStartAction[] = [
  {
    label: "普通对话",
    description: "先问清楚，再决定是否启动多 Agent。",
    prompt: "你好，先帮我梳理一下我接下来应该怎么描述任务。",
    presetMode: "default",
  },
  {
    label: "代码工程",
    description: "适合仓库改造、Bug 修复、功能实现。",
    prompt: "请帮我分析这个代码任务，并给出可执行的实现方案：",
    presetMode: "code-engineering",
    taskType: "planning",
    skills: "frontend-design",
    flags: { deep_analysis: true, code_execution: true },
  },
  {
    label: "论文修改",
    description: "适合期刊规范、文风、审稿人式反馈。",
    prompt: "请按期刊论文标准帮我修改下面这段内容：",
    presetMode: "paper-revision",
    taskType: "writing",
    skills: "academic-paper-reviewer, academic-writing-style",
    flags: { deep_analysis: true, web_search: true },
  },
];

const PRESET_FIELD_CONFIGS: Record<string, PresetFieldConfig> = {
  default: {
    showRepoPath: false,
    showGitHub: false,
    showAcademic: false,
    showApproval: true,
    taskTypes: ["", "planning", "writing", "review"],
  },
  "code-engineering": {
    showRepoPath: true,
    showGitHub: true,
    showAcademic: false,
    showApproval: true,
    taskTypes: ["", "planning", "review"],
  },
  "code-review": {
    showRepoPath: true,
    showGitHub: true,
    showAcademic: false,
    showApproval: true,
    taskTypes: ["", "review"],
  },
  "doc-organize": {
    showRepoPath: true,
    showGitHub: false,
    showAcademic: false,
    showApproval: true,
    taskTypes: ["", "writing", "review"],
  },
  "paper-revision": {
    showRepoPath: false,
    showGitHub: false,
    showAcademic: true,
    showApproval: false,
    taskTypes: ["", "writing", "review"],
  },
};

const PRESET_ROLE_OVERRIDES: Record<string, string[]> = {
  "code-engineering": ["project-manager", "backend", "frontend", "reviewer"],
  "code-review": ["reviewer", "security-reviewer"],
  "doc-organize": ["documenter", "editor"],
  "paper-revision": [
    "standards-editor",
    "reviser",
    "style-reviewer",
    "content-reviewer",
    "final-reviewer",
  ],
};

const NAV_ITEMS: Array<{
  id: string;
  label: string;
  hint: string;
  view: AppView;
}> = [
  { id: "new-task", label: "新任务", hint: "创建", view: "workspace" },
  { id: "history", label: "历史", hint: "最近", view: "workspace" },
  { id: "projects", label: "项目", hint: "空间", view: "projects" },
  { id: "tools", label: "工具", hint: "MCP/Skills", view: "tools" },
  { id: "presets", label: "模板", hint: "规则", view: "rules" },
  { id: "settings", label: "模型", hint: "控制", view: "models" },
];

const TASK_TYPE_OPTIONS = [
  { value: "", label: "自动" },
  { value: "planning", label: "规划" },
  { value: "writing", label: "写作" },
  { value: "review", label: "审查" },
];

const TEXT_ATTACHMENT_LIMIT = 12000;
const TEXT_ATTACHMENT_EXTENSIONS = /\.(txt|md|mdx|json|jsonl|csv|tsv|py|ts|tsx|js|jsx|html|css|scss|xml|yaml|yml|toml|ini|log|sql|rst|tex)$/i;
const CONVERSATION_HISTORY_LIMIT = 16;
const CONVERSATION_MESSAGE_LIMIT = 8000;

const HISTORY_FILTERS: Array<{ value: HistoryFilter; label: string }> = [
  { value: "all", label: "全部" },
  { value: "pending_approval", label: "待审批" },
  { value: "completed", label: "已完成" },
  { value: "failed", label: "失败" },
  { value: "rejected", label: "已拒绝" },
];

const TAB_LABELS: Record<PanelTab, string> = {
  output: "输出",
  stages: "阶段",
  repo: "仓库",
  github: "GitHub",
  academic: "论文",
  approval: "审批",
  canvas: "画布",
  metadata: "元数据",
};

const STATUS_LABELS: Record<string, string> = {
  completed: "已完成",
  pending: "待处理",
  pending_approval: "待审批",
  failed: "失败",
  rejected: "已拒绝",
  approved: "已批准",
  open: "开放",
  closed: "已关闭",
  connected: "已连接",
  missing_api_key: "缺少 API key",
  skipped: "已跳过",
  fetched: "已获取",
  idle: "空闲",
};

const PRIORITY_LABELS: Record<ModelSummary["priority"], string> = {
  high: "高",
  medium: "中",
  low: "低",
  disabled: "禁用",
};

const MODEL_PRIORITY_ORDER: Record<ModelSummary["priority"], number> = {
  high: 0,
  medium: 1,
  low: 2,
  disabled: 3,
};

const RISK_LABELS: Record<string, string> = {
  low: "低风险",
  medium: "中风险",
  high: "高风险",
};

const ROLE_LABELS: Record<string, string> = {
  coordinator: "协调者",
  "project-manager": "项目经理",
  backend: "后端工程师",
  frontend: "前端工程师",
  reviewer: "审查者",
  "security-reviewer": "安全审查者",
  documenter: "文档整理者",
  editor: "编辑",
  "standards-editor": "标准分析员",
  reviser: "论文修改员",
  "style-reviewer": "文风审稿人",
  "content-reviewer": "内容审稿人",
  "final-reviewer": "终审审稿人",
  "new-role": "新角色",
  "Project manager": "项目经理",
};

function formatStatus(value?: string | null): string {
  if (!value) return "-";
  return STATUS_LABELS[value] || value;
}

function formatRisk(value?: string | null): string {
  if (!value) return "-";
  return RISK_LABELS[value] || value;
}

function formatRole(value?: string | null): string {
  if (!value) return "-";
  return ROLE_LABELS[value] || value;
}

function formatChatRole(role: ChatMessageRole): string {
  if (role === "assistant") return "Mindforge";
  if (role === "system") return "系统";
  return "用户";
}

function formatProviderTestText(status: string, detail: string): string {
  const detailLabels: Record<string, string> = {
    "Connection OK": "连接正常",
    "Environment variable 'ARK_API_KEY' is not set.": "环境变量 ARK_API_KEY 未设置。",
  };
  return `${formatStatus(status)}：${detailLabels[detail] || detail}`;
}

function formatTitle(prompt: string): string {
  const trimmed = prompt.trim();
  if (!trimmed) return "未命名任务";
  return trimmed.length > 30 ? `${trimmed.slice(0, 30)}...` : trimmed;
}

function formatTaskType(value: string): string {
  return TASK_TYPE_OPTIONS.find((option) => option.value === value)?.label || value || "自动";
}

function formatAttachmentSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function canReadAsText(file: File): boolean {
  return file.type.startsWith("text/") || TEXT_ATTACHMENT_EXTENSIONS.test(file.name);
}

function readFileText(file: File): Promise<string> {
  if (typeof file.text === "function") {
    return file.text();
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
    reader.onerror = () => reject(reader.error || new Error("Failed to read file"));
    reader.readAsText(file);
  });
}

function createClientId(prefix: string): string {
  const randomId =
    globalThis.crypto?.randomUUID?.() ||
    `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}-${randomId}`;
}

async function createChatAttachment(file: File): Promise<ChatAttachment> {
  let contentExcerpt: string | undefined;
  let truncated = false;
  if (canReadAsText(file)) {
    const content = await readFileText(file);
    contentExcerpt = content.slice(0, TEXT_ATTACHMENT_LIMIT);
    truncated = content.length > TEXT_ATTACHMENT_LIMIT;
  }
  let uploaded: UploadedFileSummary | null = null;
  let uploadError: string | undefined;
  try {
    uploaded = await uploadFile(file);
  } catch (error) {
    uploadError = error instanceof Error ? error.message : "文件上传解析失败。";
  }
  const attachmentId =
    globalThis.crypto?.randomUUID?.() ||
    `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const uploadedExcerpt = uploaded?.text_excerpt || "";
  const effectiveExcerpt = uploadedExcerpt || contentExcerpt;
  return {
    id: uploaded?.file_id || `${file.name}-${file.size}-${file.lastModified}-${attachmentId}`,
    fileId: uploaded?.file_id,
    name: uploaded?.name || file.name,
    size: uploaded?.size_bytes ?? file.size,
    type: uploaded?.mime_type || file.type || "unknown",
    contentExcerpt: effectiveExcerpt,
    truncated: uploaded ? uploaded.char_count > uploadedExcerpt.length : truncated,
    parsedStatus: uploaded?.status,
    chunkCount: uploaded?.chunk_count,
    parser: uploaded?.parser,
    uploadError,
  };
}

function normalizeChatRole(value: unknown): ChatMessageRole {
  return value === "assistant" || value === "system" ? value : "user";
}

function getStringField(record: Record<string, unknown>, key: string): string | undefined {
  const value = record[key];
  return typeof value === "string" && value.trim() ? value : undefined;
}

function normalizeConversationMessage(value: unknown, index: number): ChatMessage | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  const content = getStringField(record, "content");
  if (!content) return null;
  const taskId = getStringField(record, "task_id") || getStringField(record, "taskId");
  const createdAt = getStringField(record, "created_at") || getStringField(record, "createdAt");
  return {
    id: getStringField(record, "id") || `${taskId || "history"}-${index}`,
    role: normalizeChatRole(record.role),
    content,
    taskId,
    createdAt,
  };
}

function responseToAssistantContent(result: TaskResult): string {
  return result.data.output || result.error_message || result.message || "任务已提交。";
}

function buildConversationHistory(messages: ChatMessage[]) {
  return messages.slice(-CONVERSATION_HISTORY_LIMIT).map((message) => {
    const payload: {
      role: ChatMessageRole;
      content: string;
      task_id?: string;
      created_at?: string;
      metadata?: Record<string, unknown>;
    } = {
      role: message.role,
      content:
        message.content.length > CONVERSATION_MESSAGE_LIMIT
          ? `${message.content.slice(0, CONVERSATION_MESSAGE_LIMIT - 3)}...`
          : message.content,
    };
    if (message.taskId) payload.task_id = message.taskId;
    if (message.createdAt) payload.created_at = message.createdAt;
    if (message.status) payload.metadata = { status: message.status };
    return payload;
  });
}

function hydrateConversationFromDetail(detail: TaskHistoryDetail): {
  conversationId: string;
  messages: ChatMessage[];
} {
  const metadata = detail.metadata || {};
  const requestPayload = detail.request_payload || {};
  const rawHistory = Array.isArray(metadata.conversation_history)
    ? metadata.conversation_history
    : Array.isArray(requestPayload.conversation_history)
      ? requestPayload.conversation_history
      : [];
  const messages = rawHistory
    .map((item, index) => normalizeConversationMessage(item, index))
    .filter((item): item is ChatMessage => Boolean(item));
  if (detail.prompt.trim()) {
    messages.push({
      id: `${detail.task_id}-user`,
      role: "user",
      content: detail.prompt,
      taskId: detail.task_id,
      createdAt: detail.created_at,
      status: detail.status,
    });
  }
  const assistantContent = detail.output || detail.error_message || detail.message;
  if (assistantContent.trim()) {
    messages.push({
      id: `${detail.task_id}-assistant`,
      role: "assistant",
      content: assistantContent,
      taskId: detail.task_id,
      createdAt: detail.updated_at,
      status: detail.status,
    });
  }
  const conversationId =
    getStringField(metadata, "conversation_id") ||
    getStringField(requestPayload, "conversation_id") ||
    `history-${detail.task_id}`;
  return { conversationId, messages };
}

function hydrateConversationFromDetails(details: TaskHistoryDetail[]): {
  conversationId: string;
  activeDetail: TaskHistoryDetail | null;
  messages: ChatMessage[];
} {
  const sortedDetails = [...details].sort(
    (left, right) =>
      new Date(left.created_at).getTime() - new Date(right.created_at).getTime(),
  );
  const messages: ChatMessage[] = [];
  const seen = new Set<string>();
  for (const detail of sortedDetails) {
    const userSignature = `user:${detail.task_id}:${detail.prompt}`;
    if (detail.prompt.trim() && !seen.has(userSignature)) {
      seen.add(userSignature);
      messages.push({
        id: `${detail.task_id}-user`,
        role: "user",
        content: detail.prompt,
        taskId: detail.task_id,
        createdAt: detail.created_at,
        status: detail.status,
      });
    }
    const assistantContent = detail.output || detail.error_message || detail.message;
    const assistantSignature = `assistant:${detail.task_id}:${assistantContent}`;
    if (assistantContent.trim() && !seen.has(assistantSignature)) {
      seen.add(assistantSignature);
      messages.push({
        id: `${detail.task_id}-assistant`,
        role: "assistant",
        content: assistantContent,
        taskId: detail.task_id,
        createdAt: detail.updated_at,
        status: detail.status,
      });
    }
  }
  const activeDetail = sortedDetails[sortedDetails.length - 1] || null;
  if (!activeDetail) {
    return {
      conversationId: createClientId("conversation"),
      activeDetail: null,
      messages: [],
    };
  }
  return {
    conversationId: hydrateConversationFromDetail(activeDetail).conversationId,
    activeDetail,
    messages,
  };
}

function groupHistoryConversations(items: TaskHistorySummary[]): TaskHistorySummary[] {
  const grouped = new Map<string, TaskHistorySummary>();
  const sortedItems = [...items].sort(
    (left, right) =>
      new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
  );
  for (const item of sortedItems) {
    const key = item.conversation_id || `task:${item.task_id}`;
    if (!grouped.has(key)) {
      grouped.set(key, item);
    }
  }
  return Array.from(grouped.values());
}

function createEmptyTemplate(presetMode = "code-engineering"): RuleTemplateSummary {
  return {
    template_id: "new-template",
    display_name: "新规则模板",
    description: "说明这个规则模板适合什么任务。",
    preset_mode: presetMode,
    task_types: [],
    default_coordinator_model_id: "",
    enabled: true,
    is_default: false,
    trigger_keywords: [],
    assignments: [
      {
        role: "project-manager",
        responsibility: "负责主要规划和任务拆解",
        model_id: "",
      },
    ],
    notes: "",
  };
}

function formatDate(value?: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleString("zh-CN");
}

function parseUrlList(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseSkillList(value: string): string[] {
  const seen = new Set<string>();
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean)
    .filter((item) => {
      if (seen.has(item)) return false;
      seen.add(item);
      return true;
    });
}

function optionalText(value?: string | null): string | null {
  const trimmed = value?.trim() || "";
  return trimmed ? trimmed : null;
}

function splitCommaList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function sortModelsByPriority(items: ModelSummary[]): ModelSummary[] {
  return [...items].sort(
    (left, right) =>
      MODEL_PRIORITY_ORDER[left.priority] - MODEL_PRIORITY_ORDER[right.priority] ||
      left.display_name.localeCompare(right.display_name),
  );
}

function presetFieldConfig(presetMode: string): PresetFieldConfig {
  return PRESET_FIELD_CONFIGS[presetMode] || PRESET_FIELD_CONFIGS.default;
}

function buildRoleModelOverrides(
  presetMode: string,
  modelId: string,
): Record<string, string> | undefined {
  if (!modelId) return undefined;
  const roles = PRESET_ROLE_OVERRIDES[presetMode] || [];
  if (roles.length === 0) return undefined;
  return Object.fromEntries(roles.map((role) => [role, modelId]));
}

function buildToolFlags(
  flags: Record<ComposerCapabilityKey, boolean>,
): Record<ComposerCapabilityKey, boolean> {
  return {
    deep_analysis: flags.deep_analysis,
    web_search: flags.web_search,
    code_execution: flags.code_execution,
    canvas: flags.canvas,
  };
}

function buildTaskAttachments(attachments: ChatAttachment[]) {
  return attachments.map((attachment) => ({
    id: attachment.id,
    file_id: attachment.fileId,
    name: attachment.name,
    mime_type: attachment.type,
    size_bytes: attachment.size,
    text_excerpt: attachment.contentExcerpt,
    parsed_status: attachment.parsedStatus,
    chunk_count: attachment.chunkCount,
    metadata: {
      source: "composer-upload",
      truncated: Boolean(attachment.truncated),
      has_text_excerpt: Boolean(attachment.contentExcerpt),
      backend_file_id: attachment.fileId,
      parser: attachment.parser,
      upload_error: attachment.uploadError,
    },
  }));
}

function createEmptyProviderDraft(): ProviderCreateRequest {
  return {
    provider_id: "",
    display_name: "",
    description: "",
    enabled: true,
    api_base_url: "",
    protocol: "openai-compatible",
    api_key_env: "",
    api_key: "",
    anthropic_api_base_url: "",
  };
}

function createEmptyMcpServerDraft(): MCPServerDraft {
  return {
    server_id: "",
    display_name: "",
    transport: "http-jsonrpc",
    endpoint_url: "",
    command: "",
    args: "",
    env_json: "{}",
    working_directory: "",
    enabled: true,
    headers_json: "{}",
    allowed_tools: "",
    blocked_tools: "",
    tool_call_requires_approval: true,
    notes: "",
  };
}

function createEmptyProjectSpaceDraft(): ProjectSpaceDraft {
  return {
    project_id: "",
    display_name: "",
    description: "",
    instructions: "",
    memory: "",
    default_preset_mode: "",
    repo_path: "",
    github_repo: "",
    skill_ids: "",
    mcp_server_ids: "",
    file_ids: "",
    tags: "",
    enabled: true,
  };
}

function createEmptyModelDraft(providerId = ""): ModelCreateRequest {
  return {
    model_id: "",
    display_name: "",
    provider_id: providerId,
    upstream_model: "",
    priority: "medium",
    enabled: true,
    supported_preset_modes: [],
    supported_task_types: [],
    supported_roles: [],
  };
}

export function App() {
  const composerRef = useRef<HTMLDivElement | null>(null);
  const [view, setView] = useState<AppView>("workspace");
  const [activeNavId, setActiveNavId] = useState("new-task");
  const [activeTab, setActiveTab] = useState<PanelTab>("output");

  const [presets, setPresets] = useState<PresetSummary[]>([]);
  const [providers, setProviders] = useState<ProviderSummary[]>([]);
  const [models, setModels] = useState<ModelSummary[]>([]);
  const [customModels, setCustomModels] = useState<ModelSummary[]>([]);
  const [ruleTemplates, setRuleTemplates] = useState<RuleTemplateSummary[]>([]);
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [mcpServers, setMcpServers] = useState<MCPServerSummary[]>([]);
  const [mcpAuditRecords, setMcpAuditRecords] = useState<MCPToolAuditRecord[]>([]);
  const [projectSpaces, setProjectSpaces] = useState<ProjectSpaceSummary[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactSummary[]>([]);
  const [historyItems, setHistoryItems] = useState<TaskHistorySummary[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<ApprovalRecord[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [activeTaskDetail, setActiveTaskDetail] = useState<TaskHistoryDetail | null>(null);

  const [prompt, setPrompt] = useState("");
  const [conversationId, setConversationId] = useState(() => createClientId("conversation"));
  const [conversationMessages, setConversationMessages] = useState<ChatMessage[]>([]);
  const [presetMode, setPresetMode] = useState("default");
  const [repoPath, setRepoPath] = useState("");
  const [taskType, setTaskType] = useState("");
  const [modelOverride, setModelOverride] = useState("");
  const [ruleTemplateId, setRuleTemplateId] = useState("");
  const [githubRepo, setGitHubRepo] = useState("");
  const [githubIssueNumber, setGitHubIssueNumber] = useState("");
  const [githubPrNumber, setGitHubPrNumber] = useState("");
  const [journalName, setJournalName] = useState("");
  const [journalUrl, setJournalUrl] = useState("");
  const [referencePaperUrls, setReferencePaperUrls] = useState("");
  const [skillNames, setSkillNames] = useState("");
  const [mcpServerNames, setMcpServerNames] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [requiresApproval, setRequiresApproval] = useState(false);
  const [approvalActions, setApprovalActions] = useState("写入文件");
  const [isToolMenuOpen, setIsToolMenuOpen] = useState(false);
  const [isTaskConfigOpen, setIsTaskConfigOpen] = useState(false);
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [capabilityFlags, setCapabilityFlags] = useState<
    Record<ComposerCapabilityKey, boolean>
  >(DEFAULT_CAPABILITY_FLAGS);
  const [historyFilter, setHistoryFilter] = useState<HistoryFilter>("all");
  const [deletingConversationKey, setDeletingConversationKey] = useState<string | null>(null);
  const [confirmingDeleteKey, setConfirmingDeleteKey] = useState<string | null>(null);
  const [canvasDrafts, setCanvasDrafts] = useState<Record<string, string>>({});
  const [savingCanvasArtifactId, setSavingCanvasArtifactId] = useState<string | null>(null);
  const [exportingArtifactFormat, setExportingArtifactFormat] =
    useState<ArtifactFormat | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploadingAttachments, setIsUploadingAttachments] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [settingsMessage, setSettingsMessage] = useState<string | null>(null);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [providerTestMessages, setProviderTestMessages] = useState<
    Record<string, ProviderTestMessage>
  >({});
  const [testingProviderId, setTestingProviderId] = useState<string | null>(null);
  const [providerApiKeys, setProviderApiKeys] = useState<Record<string, string>>({});
  const [newProvider, setNewProvider] = useState<ProviderCreateRequest>(() =>
    createEmptyProviderDraft(),
  );
  const [newMcpServer, setNewMcpServer] = useState<MCPServerDraft>(() =>
    createEmptyMcpServerDraft(),
  );
  const [newProjectSpace, setNewProjectSpace] = useState<ProjectSpaceDraft>(() =>
    createEmptyProjectSpaceDraft(),
  );
  const [mcpToolResults, setMcpToolResults] = useState<Record<string, MCPToolListResult>>(
    {},
  );
  const [loadingMcpToolsServerId, setLoadingMcpToolsServerId] = useState<string | null>(
    null,
  );
  const [newModel, setNewModel] = useState<ModelCreateRequest>(() =>
    createEmptyModelDraft(),
  );
  const [newModelPresetScope, setNewModelPresetScope] = useState("");
  const [newModelTaskScope, setNewModelTaskScope] = useState("");
  const [newModelRoleScope, setNewModelRoleScope] = useState("");

  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [templateDraft, setTemplateDraft] = useState<RuleTemplateSummary>(() =>
    createEmptyTemplate(),
  );
  const [editingTemplateId, setEditingTemplateId] = useState<string | null>(null);

  const activeResult: TaskResult | null = useMemo(() => {
    if (!activeTaskDetail) return null;
    return {
      status: activeTaskDetail.status,
      message: activeTaskDetail.message,
      error_message: activeTaskDetail.error_message,
      data: {
        output: activeTaskDetail.output,
        provider: activeTaskDetail.provider || "mindforge-history",
        metadata: {
          ...activeTaskDetail.metadata,
          task_id: activeTaskDetail.task_id,
          approval: activeTaskDetail.approval,
        },
      },
    };
  }, [activeTaskDetail]);

  const filteredTemplates = useMemo(
    () =>
      ruleTemplates.filter(
        (template) =>
          template.preset_mode === presetMode &&
          (!taskType ||
            template.task_types.length === 0 ||
            template.task_types.includes(taskType)),
      ),
    [presetMode, ruleTemplates, taskType],
  );
  const selectedPresetFields = presetFieldConfig(presetMode);
  const visibleTaskTypeOptions = TASK_TYPE_OPTIONS.filter((option) =>
    selectedPresetFields.taskTypes.includes(option.value),
  );
  const userModelOptions = useMemo(
    () =>
      sortModelsByPriority(
        customModels.filter((item) => item.enabled && item.priority !== "disabled"),
      ),
    [customModels],
  );
  const userModelIds = useMemo(
    () => new Set(userModelOptions.map((item) => item.model_id)),
    [userModelOptions],
  );
  const defaultUserModelId = userModelOptions[0]?.model_id || "";
  const selectedPresetName =
    presets.find((preset) => preset.preset_mode === presetMode)?.display_name || presetMode;
  const effectiveModelId = modelOverride || defaultUserModelId;
  const selectedModelName =
    userModelOptions.find((model) => model.model_id === effectiveModelId)?.display_name ||
    defaultUserModelId ||
    "未选择模型";
  const selectedRuleTemplateName =
    filteredTemplates.find((template) => template.template_id === ruleTemplateId)?.display_name ||
    "自动选择";
  const selectedSkills = useMemo(() => parseSkillList(skillNames), [skillNames]);
  const selectedMcpServerIds = useMemo(
    () => parseSkillList(mcpServerNames),
    [mcpServerNames],
  );
  const conversationHistoryItems = useMemo(
    () => groupHistoryConversations(historyItems),
    [historyItems],
  );

  async function loadConversationFromTask(taskId: string): Promise<{
    activeDetail: TaskHistoryDetail;
    conversationId: string;
    messages: ChatMessage[];
  }> {
    const detail = await fetchTaskHistoryDetail(taskId);
    const hydratedSingle = hydrateConversationFromDetail(detail);
    try {
      const details = await fetchConversationHistory(hydratedSingle.conversationId);
      const hydratedConversation = hydrateConversationFromDetails(details);
      if (hydratedConversation.activeDetail) {
        return {
          activeDetail: hydratedConversation.activeDetail,
          conversationId: hydratedConversation.conversationId,
          messages: hydratedConversation.messages,
        };
      }
    } catch {
      // Older history rows may not have conversation metadata; fall back to one task.
    }
    return {
      activeDetail: detail,
      conversationId: hydratedSingle.conversationId,
      messages: hydratedSingle.messages,
    };
  }

  async function refreshHistory(nextActiveTaskId?: string | null) {
    const statusQuery = historyFilter === "all" ? undefined : historyFilter;
    const [history, approvals] = await Promise.all([
      fetchHistoryTasks(statusQuery),
      fetchPendingApprovals(),
    ]);
    setHistoryItems(history);
    setPendingApprovals(approvals);
    const targetTaskId = nextActiveTaskId || activeTaskId || null;
    if (targetTaskId) {
      const loadedConversation = await loadConversationFromTask(targetTaskId);
      setActiveTaskId(loadedConversation.activeDetail.task_id);
      setActiveTaskDetail(loadedConversation.activeDetail);
      setConversationId(loadedConversation.conversationId);
      setConversationMessages(loadedConversation.messages);
    } else {
      setActiveTaskId(null);
      setActiveTaskDetail(null);
    }
  }

  async function loadBootstrap() {
    let providerLoadError: string | null = null;
    const providerDataPromise = fetchUserProviders().catch((error) => {
      providerLoadError =
        error instanceof Error ? error.message : "加载模型服务商控制数据失败。";
      return [] as ProviderSummary[];
    });
    const [
      presetData,
      providerData,
      runtimeModelData,
      customModelData,
      templateData,
      skillData,
      mcpServerData,
      mcpAuditData,
      projectSpaceData,
    ] = await Promise.all([
      fetchPresets(),
      providerDataPromise,
      fetchModels(),
      fetchEditableModels(),
      fetchRuleTemplates(),
      fetchSkills().catch(() => [] as SkillSummary[]),
      fetchMcpServers().catch(() => [] as MCPServerSummary[]),
      fetchMcpAudit().catch(() => [] as MCPToolAuditRecord[]),
      fetchProjectSpaces().catch(() => [] as ProjectSpaceSummary[]),
    ]);
    setPresets(presetData);
    setProviders(providerData);
    setModels(runtimeModelData);
    setCustomModels(customModelData);
    setRuleTemplates(templateData);
    setSkills(skillData);
    setMcpServers(mcpServerData);
    setMcpAuditRecords(mcpAuditData);
    setProjectSpaces(projectSpaceData);
    setLoadError(providerLoadError);
    if (!selectedTemplateId && templateData.length > 0) {
      setSelectedTemplateId(templateData[0].template_id);
      setEditingTemplateId(templateData[0].template_id);
      setTemplateDraft(templateData[0]);
    }
    await refreshHistory();
  }

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        await loadBootstrap();
      } catch (error) {
        if (cancelled) return;
        setLoadError(error instanceof Error ? error.message : "加载初始化数据失败。");
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        await refreshHistory();
      } catch (error) {
        if (cancelled) return;
        setLoadError(error instanceof Error ? error.message : "加载历史记录失败。");
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [historyFilter]);

  useEffect(() => {
    if (ruleTemplateId && !filteredTemplates.some((item) => item.template_id === ruleTemplateId)) {
      setRuleTemplateId("");
    }
  }, [filteredTemplates, ruleTemplateId]);

  useEffect(() => {
    if (!defaultUserModelId) {
      if (modelOverride) setModelOverride("");
      return;
    }
    if (!modelOverride || !userModelIds.has(modelOverride)) {
      setModelOverride(defaultUserModelId);
    }
  }, [defaultUserModelId, modelOverride, userModelIds]);

  useEffect(() => {
    if (!defaultUserModelId) return;
    setTemplateDraft((current) => {
      const nextAssignments = current.assignments.map((assignment) =>
        userModelIds.has(assignment.model_id)
          ? assignment
          : { ...assignment, model_id: defaultUserModelId },
      );
      const coordinatorChanged = !userModelIds.has(
        current.default_coordinator_model_id,
      );
      const assignmentsChanged = nextAssignments.some(
        (assignment, index) => assignment.model_id !== current.assignments[index]?.model_id,
      );
      if (!coordinatorChanged && !assignmentsChanged) return current;
      return {
        ...current,
        default_coordinator_model_id: coordinatorChanged
          ? defaultUserModelId
          : current.default_coordinator_model_id,
        assignments: nextAssignments,
      };
    });
  }, [defaultUserModelId, userModelIds]);

  useEffect(() => {
    const config = presetFieldConfig(presetMode);
    if (!config.taskTypes.includes(taskType)) {
      setTaskType("");
    }
    if (!config.showRepoPath) {
      setRepoPath("");
    }
    if (!config.showGitHub) {
      setGitHubRepo("");
      setGitHubIssueNumber("");
      setGitHubPrNumber("");
    }
    if (!config.showAcademic) {
      setJournalName("");
      setJournalUrl("");
      setReferencePaperUrls("");
    }
    if (!config.showApproval) {
      setRequiresApproval(false);
    }
  }, [presetMode, taskType]);

  useEffect(() => {
    if (!isToolMenuOpen && !isTaskConfigOpen) return;

    function closeComposerOverlays() {
      setIsToolMenuOpen(false);
      setIsTaskConfigOpen(false);
    }

    function handleDocumentPointerDown(event: PointerEvent) {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (composerRef.current?.contains(target)) return;
      closeComposerOverlays();
    }

    function handleDocumentKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        closeComposerOverlays();
      }
    }

    document.addEventListener("pointerdown", handleDocumentPointerDown);
    document.addEventListener("keydown", handleDocumentKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handleDocumentPointerDown);
      document.removeEventListener("keydown", handleDocumentKeyDown);
    };
  }, [isToolMenuOpen, isTaskConfigOpen]);

  function handleNavClick(navId: string, targetView: AppView) {
    setActiveNavId(navId);
    setView(targetView);
    setSettingsMessage(null);
    setSettingsError(null);
    if (navId === "new-task") {
      setActiveTaskId(null);
      setActiveTaskDetail(null);
      setActiveTab("output");
      setPrompt("");
      setConversationId(createClientId("conversation"));
      setConversationMessages([]);
      setAttachments([]);
      setSkillNames("");
      setMcpServerNames("");
      setSelectedProjectId("");
      setCapabilityFlags(DEFAULT_CAPABILITY_FLAGS);
      setSubmitError(null);
      setIsToolMenuOpen(false);
      setIsTaskConfigOpen(false);
      setConfirmingDeleteKey(null);
    }
  }

  function handleQuickStart(action: QuickStartAction) {
    setPrompt(action.prompt);
    setPresetMode(action.presetMode);
    setTaskType(action.taskType || "");
    setSkillNames(action.skills || "");
    setCapabilityFlags({
      ...DEFAULT_CAPABILITY_FLAGS,
      ...(action.flags || {}),
    });
    setIsTaskConfigOpen(Boolean(action.skills || action.flags || action.taskType));
    setIsToolMenuOpen(false);
    setSubmitError(null);
  }

  async function handleHistorySelect(taskId: string) {
    const loadedConversation = await loadConversationFromTask(taskId);
    setActiveTaskId(loadedConversation.activeDetail.task_id);
    setActiveTaskDetail(loadedConversation.activeDetail);
    setConversationId(loadedConversation.conversationId);
    setConversationMessages(loadedConversation.messages);
    setActiveTab("output");
    setView("workspace");
    setActiveNavId("history");
  }

  async function handleDeleteHistoryItem(task: TaskHistorySummary) {
    const deleteKey = task.conversation_id || `task:${task.task_id}`;
    if (confirmingDeleteKey !== deleteKey) {
      setConfirmingDeleteKey(deleteKey);
      setSubmitError("再次点击“确认”将删除这段对话。");
      return;
    }
    const deletingActive =
      task.task_id === activeTaskId ||
      (Boolean(task.conversation_id) && task.conversation_id === conversationId);
    setDeletingConversationKey(deleteKey);
    setSubmitError(null);
    try {
      if (task.conversation_id) {
        await deleteConversationHistory(task.conversation_id);
      } else {
        await deleteHistoryTask(task.task_id);
      }
      setHistoryItems((current) =>
        current.filter((item) =>
          task.conversation_id
            ? item.conversation_id !== task.conversation_id
            : item.task_id !== task.task_id,
        ),
      );
      if (deletingActive) {
        handleNavClick("new-task", "workspace");
      } else if (activeTaskId) {
        await refreshHistory(activeTaskId);
      }
      setConfirmingDeleteKey(null);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "删除对话失败。");
    } finally {
      setDeletingConversationKey(null);
    }
  }

  async function handleAttachmentInput(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files || []);
    if (files.length === 0) return;
    setIsUploadingAttachments(true);
    setSubmitError(null);
    try {
      const nextAttachments = await Promise.all(files.map(createChatAttachment));
      setAttachments((current) => [...current, ...nextAttachments]);
      setIsToolMenuOpen(false);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "上传文件失败。");
    } finally {
      setIsUploadingAttachments(false);
      event.target.value = "";
    }
  }

  function removeAttachment(attachmentId: string) {
    setAttachments((current) => current.filter((item) => item.id !== attachmentId));
  }

  function toggleCapabilityFlag(key: ComposerCapabilityKey) {
    setCapabilityFlags((current) => ({
      ...current,
      [key]: !current[key],
    }));
  }

  function openModelSetup() {
    setView("models");
    setActiveNavId("settings");
    setSettingsMessage("先添加模型服务商和模型，然后回到新任务继续对话。");
  }

  function artifactContentToText(content: unknown): string {
    if (typeof content === "string") return content;
    return JSON.stringify(content ?? {}, null, 2);
  }

  function getCanvasDraft(artifact: CanvasArtifact): string {
    const artifactId = String(artifact.artifact_id || "");
    return canvasDrafts[artifactId] ?? artifactContentToText(artifact.content);
  }

  async function handleSaveCanvasArtifact(artifact: CanvasArtifact) {
    if (!activeTaskDetail || !artifact.artifact_id) return;
    const artifactId = String(artifact.artifact_id);
    setSavingCanvasArtifactId(artifactId);
    setSubmitError(null);
    try {
      const updated = await updateCanvasArtifact(
        activeTaskDetail.task_id,
        artifactId,
        {
          title: artifact.title,
          content: getCanvasDraft(artifact),
        },
      );
      setActiveTaskDetail(updated);
      setCanvasDrafts((current) => {
        const next = { ...current };
        delete next[artifactId];
        return next;
      });
      await refreshHistory(updated.task_id);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "保存画布失败。");
    } finally {
      setSavingCanvasArtifactId(null);
    }
  }

  async function handleExportActiveOutput(format: ArtifactFormat) {
    const content = activeResult?.data.output || activeTaskDetail?.output || "";
    if (!content.trim()) {
      setSubmitError("当前没有可导出的内容。");
      return;
    }
    setExportingArtifactFormat(format);
    setSubmitError(null);
    try {
      const artifact = await exportArtifact({
        title: activeTaskDetail?.prompt || "Mindforge 输出",
        content,
        format,
        source_task_id: activeTaskDetail?.task_id || null,
      });
      setArtifacts((current) => [artifact, ...current.filter((item) => item.artifact_id !== artifact.artifact_id)]);
      window.open(`${getApiBaseUrl()}${artifact.download_url.replace(/^\/api/, "")}`, "_blank");
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "导出文档失败。");
    } finally {
      setExportingArtifactFormat(null);
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) {
      return;
    }
    event.preventDefault();
    void handleSubmit();
  }

  async function handleSubmit() {
    const submittedPrompt = prompt.trim();
    if (!submittedPrompt) {
      setSubmitError("请输入任务描述。");
      return;
    }
    if (!modelOverride && !defaultUserModelId) {
      setSubmitError("请先在模型控制中心添加并启用一个用户模型。");
      openModelSetup();
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const priorMessages = conversationMessages;
      const currentConversationId = conversationId || createClientId("conversation");
      const metadata: Record<string, unknown> = {};
      const fieldConfig = presetFieldConfig(presetMode);
      if (fieldConfig.showApproval && requiresApproval) {
        metadata.requires_approval = true;
        metadata.approval_actions = approvalActions
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean);
        metadata.execution_mode = "write";
      }
      const selectedModelId = userModelIds.has(modelOverride)
        ? modelOverride
        : defaultUserModelId;
      const result = await submitTask({
        prompt: submittedPrompt,
        preset_mode: presetMode,
        repo_path: fieldConfig.showRepoPath ? repoPath || undefined : undefined,
        task_type: taskType || undefined,
        model_override: selectedModelId || undefined,
        role_model_overrides: buildRoleModelOverrides(presetMode, selectedModelId),
        rule_template_id: ruleTemplateId || undefined,
        project_id: selectedProjectId || undefined,
        conversation_id: currentConversationId,
        conversation_history: buildConversationHistory(priorMessages),
        skills: selectedSkills,
        mcp_server_ids: selectedMcpServerIds,
        github_repo: fieldConfig.showGitHub ? githubRepo || undefined : undefined,
        github_issue_number:
          fieldConfig.showGitHub && githubIssueNumber
            ? Number(githubIssueNumber)
            : undefined,
        github_pr_number:
          fieldConfig.showGitHub && githubPrNumber
            ? Number(githubPrNumber)
            : undefined,
        journal_name: fieldConfig.showAcademic ? journalName || undefined : undefined,
        journal_url: fieldConfig.showAcademic ? journalUrl || undefined : undefined,
        reference_paper_urls: fieldConfig.showAcademic
          ? parseUrlList(referencePaperUrls)
          : [],
        attachments: buildTaskAttachments(attachments),
        tool_flags: buildToolFlags(capabilityFlags),
        metadata,
      });
      const taskId = result.data.metadata.task_id;
      const timestamp = new Date().toISOString();
      const nextMessages: ChatMessage[] = [
        ...priorMessages,
        {
          id: createClientId("message"),
          role: "user",
          content: submittedPrompt,
          taskId,
          createdAt: timestamp,
          status: result.status,
        },
        {
          id: createClientId("message"),
          role: "assistant",
          content: responseToAssistantContent(result),
          taskId,
          createdAt: timestamp,
          status: result.status,
        },
      ];
      setConversationId(currentConversationId);
      setConversationMessages(nextMessages);
      setPrompt("");
      setAttachments([]);
      await refreshHistory(taskId || null);
      setActiveTab(result.status === "pending_approval" ? "approval" : "output");
      setSubmitError(null);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "任务提交失败。");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleApprovalDecision(action: "approve" | "reject") {
    if (!activeTaskId) return;
    try {
      if (action === "approve") {
        await approveTask(activeTaskId, "从工作台批准。");
      } else {
        await rejectTask(activeTaskId, "从工作台拒绝。");
      }
      await refreshHistory(activeTaskId);
      setActiveTab("approval");
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "审批请求失败。");
    }
  }

  async function handleModelSave(model: ModelSummary) {
    try {
      const updated = await updateModelControl(model.model_id, {
        priority: model.priority,
        enabled: model.enabled,
      });
      setCustomModels((previous) =>
        previous.map((item) => (item.model_id === updated.model_id ? updated : item)),
      );
      setModels(await fetchModels());
      setSettingsError(null);
      setSettingsMessage(`已保存模型 ${updated.display_name}。`);
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(error instanceof Error ? error.message : "模型更新失败。");
    }
  }

  async function handleCreateModel() {
    try {
      if (!providers.length) {
        setSettingsMessage(null);
        setSettingsError("请先在 API 管理里添加一个模型服务商。");
        return;
      }
      const created = await createModelControl({
        ...newModel,
        provider_id: newModel.provider_id || providers[0].provider_id,
        supported_preset_modes: splitCommaList(newModelPresetScope),
        supported_task_types: splitCommaList(newModelTaskScope),
        supported_roles: splitCommaList(newModelRoleScope),
      });
      setCustomModels((previous) => [...previous, created]);
      setModels(await fetchModels());
      setNewModel(createEmptyModelDraft(providers[0]?.provider_id || ""));
      setNewModelPresetScope("");
      setNewModelTaskScope("");
      setNewModelRoleScope("");
      setSettingsError(null);
      setSettingsMessage(`已添加模型 ${created.display_name}。`);
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(error instanceof Error ? error.message : "模型添加失败。");
    }
  }

  async function handleDeleteModel(model: ModelSummary) {
    try {
      await deleteModelControl(model.model_id);
      setCustomModels((previous) =>
        previous.filter((item) => item.model_id !== model.model_id),
      );
      setModels(await fetchModels());
      setSettingsError(null);
      setSettingsMessage(`已删除模型 ${model.display_name}。`);
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(error instanceof Error ? error.message : "模型删除失败。");
    }
  }

  function updateProviderDraft(providerId: string, updates: Partial<ProviderSummary>) {
    setProviders((previous) =>
      previous.map((provider) =>
        provider.provider_id === providerId ? { ...provider, ...updates } : provider,
      ),
    );
  }

  async function handleProviderSave(provider: ProviderSummary) {
    try {
      const apiKey = providerApiKeys[provider.provider_id]?.trim();
      const updated = await updateProviderControl(provider.provider_id, {
        display_name: optionalText(provider.display_name),
        description: optionalText(provider.description),
        enabled: provider.enabled,
        api_base_url: optionalText(provider.api_base_url),
        protocol: optionalText(provider.protocol),
        api_key_env: optionalText(provider.api_key_env),
        ...(apiKey ? { api_key: apiKey } : {}),
        anthropic_api_base_url: optionalText(provider.anthropic_api_base_url),
      });
      setProviders((previous) =>
        previous.map((item) => (item.provider_id === updated.provider_id ? updated : item)),
      );
      setProviderApiKeys((previous) => ({ ...previous, [provider.provider_id]: "" }));
      setSettingsError(null);
      setSettingsMessage(`已保存模型服务商 ${updated.display_name}。`);
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(error instanceof Error ? error.message : "模型服务商更新失败。");
    }
  }

  async function handleCreateProvider() {
    try {
      const created = await createProviderControl({
        ...newProvider,
        api_base_url: optionalText(newProvider.api_base_url),
        api_key_env: optionalText(newProvider.api_key_env),
        api_key: optionalText(newProvider.api_key),
        protocol: optionalText(newProvider.protocol) || "openai-compatible",
        anthropic_api_base_url: optionalText(newProvider.anthropic_api_base_url),
      });
      setProviders((previous) => [...previous, created]);
      setNewProvider(createEmptyProviderDraft());
      if (!newModel.provider_id) {
        setNewModel((current) => ({ ...current, provider_id: created.provider_id }));
      }
      setModels(await fetchModels());
      setSettingsError(null);
      setSettingsMessage(`已添加模型服务商 ${created.display_name}。`);
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(error instanceof Error ? error.message : "模型服务商添加失败。");
    }
  }

  async function handleDeleteProvider(provider: ProviderSummary) {
    try {
      await deleteProviderControl(provider.provider_id);
      setProviders((previous) =>
        previous.filter((item) => item.provider_id !== provider.provider_id),
      );
      setCustomModels(await fetchEditableModels());
      setModels(await fetchModels());
      setSettingsError(null);
      setSettingsMessage(`已删除模型服务商 ${provider.display_name}。`);
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(error instanceof Error ? error.message : "模型服务商删除失败。");
    }
  }

  async function handleProviderTest(provider: ProviderSummary) {
    setTestingProviderId(provider.provider_id);
    setProviderTestMessages((previous) => {
      const next = { ...previous };
      delete next[provider.provider_id];
      return next;
    });
    try {
      const result = await testProviderConnection(provider.provider_id);
      const message = formatProviderTestText(result.status, result.detail);
      setProviderTestMessages((previous) => ({
        ...previous,
        [provider.provider_id]: {
          status: result.ok ? "success" : "error",
          text: message,
        },
      }));
    } catch (error) {
      setProviderTestMessages((previous) => ({
        ...previous,
        [provider.provider_id]: {
          status: "error",
          text: error instanceof Error ? error.message : "连接测试失败。",
        },
      }));
    } finally {
      setTestingProviderId((current) =>
        current === provider.provider_id ? null : current,
      );
    }
  }

  async function handleSaveMcpServer() {
    try {
      const headers = newMcpServer.headers_json.trim()
        ? (JSON.parse(newMcpServer.headers_json) as Record<string, string>)
        : {};
      const env = newMcpServer.env_json.trim()
        ? (JSON.parse(newMcpServer.env_json) as Record<string, string>)
        : {};
      const payload: MCPServerUpsert = {
        server_id: newMcpServer.server_id.trim(),
        display_name: newMcpServer.display_name.trim(),
        transport: newMcpServer.transport,
        endpoint_url: newMcpServer.endpoint_url.trim(),
        command: optionalText(newMcpServer.command),
        args: parseSkillList(newMcpServer.args),
        env,
        working_directory: optionalText(newMcpServer.working_directory),
        enabled: newMcpServer.enabled,
        headers,
        allowed_tools: parseSkillList(newMcpServer.allowed_tools),
        blocked_tools: parseSkillList(newMcpServer.blocked_tools),
        tool_call_requires_approval: newMcpServer.tool_call_requires_approval,
        notes: newMcpServer.notes.trim(),
      };
      const saved = await createMcpServer(payload);
      setMcpServers((previous) => [
        saved,
        ...previous.filter((item) => item.server_id !== saved.server_id),
      ]);
      setNewMcpServer(createEmptyMcpServerDraft());
      setSettingsError(null);
      setSettingsMessage(`已保存 MCP Server ${saved.display_name}。`);
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(
        error instanceof Error
          ? error.message
          : "MCP Server 保存失败，请检查 Headers JSON。",
      );
    }
  }

  async function handleSaveProjectSpace() {
    try {
      const payload: ProjectSpaceUpsert = {
        project_id: newProjectSpace.project_id.trim(),
        display_name: newProjectSpace.display_name.trim(),
        description: newProjectSpace.description.trim(),
        instructions: newProjectSpace.instructions.trim(),
        memory: newProjectSpace.memory.trim(),
        default_preset_mode: optionalText(newProjectSpace.default_preset_mode),
        repo_path: optionalText(newProjectSpace.repo_path),
        github_repo: optionalText(newProjectSpace.github_repo),
        skill_ids: parseSkillList(newProjectSpace.skill_ids),
        mcp_server_ids: parseSkillList(newProjectSpace.mcp_server_ids),
        file_ids: parseSkillList(newProjectSpace.file_ids),
        tags: parseSkillList(newProjectSpace.tags),
        enabled: newProjectSpace.enabled,
      };
      const saved = await createProjectSpace(payload);
      setProjectSpaces((previous) => [
        saved,
        ...previous.filter((item) => item.project_id !== saved.project_id),
      ]);
      setNewProjectSpace(createEmptyProjectSpaceDraft());
      setSettingsMessage(`已保存项目空间 ${saved.display_name}。`);
      setSettingsError(null);
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : "保存项目空间失败。");
    }
  }

  async function handleDeleteProjectSpace(project: ProjectSpaceSummary) {
    try {
      await deleteProjectSpace(project.project_id);
      setProjectSpaces((previous) =>
        previous.filter((item) => item.project_id !== project.project_id),
      );
      if (selectedProjectId === project.project_id) {
        setSelectedProjectId("");
      }
      setSettingsMessage(`已删除项目空间 ${project.display_name}。`);
      setSettingsError(null);
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : "删除项目空间失败。");
    }
  }

  async function handleToggleSkill(skill: SkillSummary) {
    try {
      const updated = await updateSkillSettings(skill.skill_id, {
        enabled: !skill.enabled,
      });
      setSkills((previous) =>
        previous.map((item) => (item.skill_id === updated.skill_id ? updated : item)),
      );
      setSettingsMessage(`${updated.name} 已${updated.enabled ? "启用" : "禁用"}。`);
      setSettingsError(null);
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : "更新 Skill 失败。");
    }
  }

  async function handleDeleteMcpServer(server: MCPServerSummary) {
    try {
      await deleteMcpServer(server.server_id);
      setMcpServers((previous) =>
        previous.filter((item) => item.server_id !== server.server_id),
      );
      setMcpToolResults((previous) => {
        const next = { ...previous };
        delete next[server.server_id];
        return next;
      });
      setSettingsError(null);
      setSettingsMessage(`已删除 MCP Server ${server.display_name}。`);
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(error instanceof Error ? error.message : "MCP Server 删除失败。");
    }
  }

  async function handleLoadMcpTools(server: MCPServerSummary) {
    setLoadingMcpToolsServerId(server.server_id);
    try {
      const result = await fetchMcpTools(server.server_id);
      setMcpToolResults((previous) => ({
        ...previous,
        [server.server_id]: result,
      }));
      setSettingsError(null);
      setSettingsMessage(`已读取 ${server.display_name} 的工具目录。`);
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(error instanceof Error ? error.message : "读取 MCP 工具失败。");
    } finally {
      setLoadingMcpToolsServerId((current) =>
        current === server.server_id ? null : current,
      );
    }
  }

  function updateTemplateDraft(
    updater: (current: RuleTemplateSummary) => RuleTemplateSummary,
  ) {
    setTemplateDraft((current) => updater(current));
  }

  function handleSelectTemplate(template: RuleTemplateSummary) {
    setSelectedTemplateId(template.template_id);
    setEditingTemplateId(template.template_id);
    setTemplateDraft(template);
    setSettingsError(null);
    setSettingsMessage(null);
  }

  function handleCreateTemplate() {
    const fresh = createEmptyTemplate(presetMode);
    setSelectedTemplateId(null);
    setEditingTemplateId(null);
    setTemplateDraft(fresh);
    setView("rules");
  }

  async function handleSaveTemplate() {
    try {
      const payload = {
        ...templateDraft,
        task_types: templateDraft.task_types.filter(Boolean),
        trigger_keywords: templateDraft.trigger_keywords.filter(Boolean),
        assignments: templateDraft.assignments.filter(
          (item) => item.role && item.responsibility && item.model_id,
        ),
      };
      const saved = editingTemplateId
        ? await updateRuleTemplate(editingTemplateId, payload)
        : await createRuleTemplate(payload);
      const templates = await fetchRuleTemplates();
      setRuleTemplates(templates);
      setSelectedTemplateId(saved.template_id);
      setEditingTemplateId(saved.template_id);
      setTemplateDraft(saved);
      setSettingsError(null);
      setSettingsMessage(`已保存模板 ${saved.display_name}。`);
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(error instanceof Error ? error.message : "模板保存失败。");
    }
  }

  async function handleDeleteTemplate() {
    if (!editingTemplateId) return;
    try {
      await deleteRuleTemplate(editingTemplateId);
      const templates = await fetchRuleTemplates();
      setRuleTemplates(templates);
      if (templates.length > 0) {
        handleSelectTemplate(templates[0]);
      } else {
        handleCreateTemplate();
      }
      setSettingsError(null);
      setSettingsMessage("已删除模板。");
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(error instanceof Error ? error.message : "模板删除失败。");
    }
  }

  function renderAssignmentsEditor(assignments: RuleAssignment[]) {
    return (
      <div className="assignment-list">
        {assignments.map((assignment, index) => (
          <div key={`${assignment.role}-${index}`} className="assignment-row">
            <input
              type="text"
              value={assignment.role}
              placeholder="角色"
              onChange={(event) =>
                updateTemplateDraft((current) => ({
                  ...current,
                  assignments: current.assignments.map((item, itemIndex) =>
                    itemIndex === index ? { ...item, role: event.target.value } : item,
                  ),
                }))
              }
            />
            <input
              type="text"
              value={assignment.responsibility}
              placeholder="职责"
              onChange={(event) =>
                updateTemplateDraft((current) => ({
                  ...current,
                  assignments: current.assignments.map((item, itemIndex) =>
                    itemIndex === index
                      ? { ...item, responsibility: event.target.value }
                      : item,
                  ),
                }))
              }
            />
            <select
              value={assignment.model_id}
              onChange={(event) =>
                updateTemplateDraft((current) => ({
                  ...current,
                  assignments: current.assignments.map((item, itemIndex) =>
                    itemIndex === index ? { ...item, model_id: event.target.value } : item,
                  ),
                }))
              }
            >
              {userModelOptions.map((model) => (
                <option key={model.model_id} value={model.model_id}>
                  {model.display_name}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="icon-button"
              onClick={() =>
                updateTemplateDraft((current) => ({
                  ...current,
                  assignments: current.assignments.filter((_, itemIndex) => itemIndex !== index),
                }))
              }
            >
              删除
            </button>
          </div>
        ))}
      </div>
    );
  }

  function renderWorkspace() {
    const activeRepo = activeTaskDetail?.metadata.repo_analysis;
    const activeGitHub = activeTaskDetail?.metadata.github_context;
    const activeAcademic = activeTaskDetail?.metadata.academic_context;
    const activeTrace = activeTaskDetail?.metadata.orchestration;
    const activeApproval = activeTaskDetail?.approval;
    const activeMetadata = activeTaskDetail?.metadata || {};
    const activeToolFlags =
      typeof activeMetadata.tool_flags === "object" && activeMetadata.tool_flags !== null
        ? (activeMetadata.tool_flags as Record<string, unknown>)
        : {};
    const activeToolContext =
      typeof activeMetadata.tool_context === "object" && activeMetadata.tool_context !== null
        ? (activeMetadata.tool_context as Record<string, unknown>)
        : {};
    const canvasArtifacts = Array.isArray(activeMetadata.canvas_artifacts)
      ? (activeMetadata.canvas_artifacts as CanvasArtifact[])
      : [];
    const generatedArtifacts = Array.isArray(activeMetadata.generated_artifacts)
      ? (activeMetadata.generated_artifacts as ArtifactSummary[])
      : [];
    const activeExecutionReport =
      typeof activeMetadata.execution_report === "object" && activeMetadata.execution_report !== null
        ? (activeMetadata.execution_report as {
            steps?: Array<Record<string, unknown>>;
            warnings?: unknown[];
            runtime_boundary?: Record<string, unknown>;
          })
        : null;
    const visibleMessages =
      conversationMessages.length > 0
        ? conversationMessages
        : activeTaskDetail
          ? hydrateConversationFromDetail(activeTaskDetail).messages
          : [];
    const conversationTurnCount = visibleMessages.filter(
      (message) => message.role === "user",
    ).length;
    const tabDescriptors: Array<{ tab: PanelTab; count: number; hasData: boolean }> = [
      {
        tab: "output",
        count: activeTaskDetail?.output ? 1 + generatedArtifacts.length : generatedArtifacts.length,
        hasData: Boolean(activeTaskDetail?.output || generatedArtifacts.length),
      },
      {
        tab: "stages",
        count: activeTrace?.stages?.length || 0,
        hasData: Boolean(activeTrace?.stages?.length),
      },
      { tab: "repo", count: activeRepo?.repo_summary ? 1 : 0, hasData: Boolean(activeRepo?.repo_summary) },
      {
        tab: "github",
        count: [activeGitHub?.repository, activeGitHub?.issue, activeGitHub?.pull_request].filter(Boolean).length,
        hasData: Boolean(activeGitHub?.repository || activeGitHub?.issue || activeGitHub?.pull_request),
      },
      {
        tab: "academic",
        count: (activeAcademic?.journal ? 1 : 0) + (activeAcademic?.reference_papers?.length || 0),
        hasData: Boolean(activeAcademic?.journal || activeAcademic?.reference_papers?.length),
      },
      { tab: "approval", count: activeApproval ? 1 : 0, hasData: Boolean(activeApproval) },
      {
        tab: "canvas",
        count: canvasArtifacts.length + Object.keys(activeToolFlags).length,
        hasData: Boolean(canvasArtifacts.length || Object.keys(activeToolFlags).length),
      },
      { tab: "metadata", count: activeTaskDetail ? 1 : 0, hasData: Boolean(activeTaskDetail) },
    ];

    return (
      <div className="workspace-body view-enter">
        <section className="chat-column chat-column-dialog">
          <div className="panel conversation-preview chat-surface">
            <div className="panel-title-row chat-title-row">
              <div>
                <h2>任务工作台</h2>
                <p className="subtle">
                  像对话一样描述任务；当前对话 {conversationTurnCount} 轮，预设、模型、规则和文件都收在下方工具栏里。
                </p>
              </div>
              <button
                type="button"
                className="secondary-button"
                onClick={() => handleNavClick("new-task", "workspace")}
              >
                新任务
              </button>
            </div>
            <div className="message-list chat-thread">
              {visibleMessages.length > 0 ? (
                visibleMessages.map((message) => (
                  <div
                    key={message.id}
                    className={`bubble ${message.role} ${
                      message.status === "failed" ? "failed" : ""
                    }`}
                  >
                    <div className="bubble-role">{formatChatRole(message.role)}</div>
                    <div className="bubble-content">{message.content}</div>
                    {message.taskId && (
                      <div className="bubble-meta">
                        {message.status ? formatStatus(message.status) : "已记录"} / {message.taskId}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="empty-hint chat-empty">
                  <strong>开启一次新的 Mindforge 对话</strong>
                  <span>直接输入任务。需要预设、模型、仓库、期刊或审批时，点击左下角 + 配置。</span>
                  <div className="quick-start-grid" aria-label="快速开始">
                    {QUICK_START_ACTIONS.map((action) => (
                      <button
                        key={action.label}
                        type="button"
                        className="quick-start-card"
                        onClick={() => handleQuickStart(action)}
                      >
                        <span>{action.label}</span>
                        <small>{action.description}</small>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="chat-composer" ref={composerRef}>
              {isTaskConfigOpen && (
                <div className="composer-config-panel" id="task-config-panel">
                  <div className="composer-config-head">
                    <strong>任务配置</strong>
                    <span className="subtle">这些是任务上下文，不再和正文输入抢层级。</span>
                  </div>
                  <div className="control-grid composer-control-grid">
                    <label>
                      <span>预设模式</span>
                      <select value={presetMode} onChange={(event) => setPresetMode(event.target.value)}>
                        {presets.map((preset) => (
                          <option key={preset.preset_mode} value={preset.preset_mode}>
                            {preset.display_name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      <span>任务类型</span>
                      <select value={taskType} onChange={(event) => setTaskType(event.target.value)}>
                        {visibleTaskTypeOptions.map((option) => (
                          <option key={option.value || "auto"} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="full-width">
                      <span>项目空间</span>
                      <select
                        value={selectedProjectId}
                        onChange={(event) => setSelectedProjectId(event.target.value)}
                      >
                        <option value="">不使用项目空间</option>
                        {projectSpaces
                          .filter((project) => project.enabled)
                          .map((project) => (
                            <option key={project.project_id} value={project.project_id}>
                              {project.display_name} / {project.project_id}
                            </option>
                          ))}
                      </select>
                      <small className="field-hint">
                        项目空间会注入项目说明、记忆、文件片段、默认 Skills 和 MCP 上下文。
                      </small>
                    </label>
                    {selectedPresetFields.showRepoPath && (
                      <label>
                        <span>仓库路径</span>
                        <input
                          type="text"
                          placeholder="E:\\CODE\\project or ."
                          value={repoPath}
                          onChange={(event) => setRepoPath(event.target.value)}
                        />
                      </label>
                    )}
                    <label>
                      <span>协调模型</span>
                      <select
                        value={modelOverride}
                        onChange={(event) => setModelOverride(event.target.value)}
                      >
                        {userModelOptions.length === 0 ? (
                          <option value="">请先添加用户模型</option>
                        ) : (
                          userModelOptions.map((model) => (
                            <option key={model.model_id} value={model.model_id}>
                              {model.display_name} / {model.provider_id}
                            </option>
                          ))
                        )}
                      </select>
                    </label>
                    <label className="full-width">
                      <span>规则模板</span>
                      <select
                        value={ruleTemplateId}
                        onChange={(event) => setRuleTemplateId(event.target.value)}
                      >
                        <option value="">自动选择</option>
                        {filteredTemplates.map((template) => (
                          <option key={template.template_id} value={template.template_id}>
                            {template.display_name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="full-width">
                      <span>Skills</span>
                      <input
                        type="text"
                        aria-label="Skills"
                        value={skillNames}
                        placeholder="frontend-design, gsd-do, academic-paper-reviewer"
                        list="skill-options"
                        onChange={(event) => setSkillNames(event.target.value)}
                      />
                      <datalist id="skill-options">
                        {skills.map((skill) => (
                          <option key={skill.skill_id} value={skill.skill_id}>
                            {skill.name}
                          </option>
                        ))}
                      </datalist>
                      <small className="field-hint">
                        多个 Skill 用逗号或换行分隔；当前会随任务发送给后端并写入历史。
                      </small>
                    </label>
                    <label className="full-width">
                      <span>MCP Servers</span>
                      <input
                        type="text"
                        aria-label="MCP Servers"
                        value={mcpServerNames}
                        placeholder="filesystem, github, browser"
                        list="mcp-server-options"
                        onChange={(event) => setMcpServerNames(event.target.value)}
                      />
                      <datalist id="mcp-server-options">
                        {mcpServers.map((server) => (
                          <option key={server.server_id} value={server.server_id}>
                            {server.display_name}
                          </option>
                        ))}
                      </datalist>
                      <small className="field-hint">
                        填入已注册 MCP server id；后端会读取 tools/list 并把工具目录注入任务上下文。
                      </small>
                    </label>
                    {selectedPresetFields.showGitHub && (
                      <>
                        <label>
                          <span>GitHub 仓库</span>
                          <input
                            type="text"
                            placeholder="owner/repo"
                            value={githubRepo}
                            onChange={(event) => setGitHubRepo(event.target.value)}
                          />
                        </label>
                        <label>
                          <span>Issue 编号</span>
                          <input
                            type="number"
                            min="1"
                            placeholder="可选"
                            value={githubIssueNumber}
                            onChange={(event) => setGitHubIssueNumber(event.target.value)}
                          />
                        </label>
                        <label>
                          <span>PR 编号</span>
                          <input
                            type="number"
                            min="1"
                            placeholder="可选"
                            value={githubPrNumber}
                            onChange={(event) => setGitHubPrNumber(event.target.value)}
                          />
                        </label>
                      </>
                    )}
                    {selectedPresetFields.showAcademic && (
                      <>
                        <label>
                          <span>期刊名称</span>
                          <input
                            type="text"
                            placeholder="Nature, IEEE TSE..."
                            value={journalName}
                            onChange={(event) => setJournalName(event.target.value)}
                          />
                        </label>
                        <label className="full-width">
                          <span>期刊投稿指南 URL</span>
                          <input
                            type="url"
                            placeholder="https://journal.example.com/for-authors"
                            value={journalUrl}
                            onChange={(event) => setJournalUrl(event.target.value)}
                          />
                        </label>
                        <label className="full-width">
                          <span>参考论文 URL</span>
                          <textarea
                            value={referencePaperUrls}
                            onChange={(event) => setReferencePaperUrls(event.target.value)}
                            placeholder="每行一个 URL，也可以用英文逗号分隔。"
                          />
                        </label>
                      </>
                    )}
                    {selectedPresetFields.showApproval && (
                      <label className="toggle-row full-width">
                        <span>执行前需要审批</span>
                        <input
                          type="checkbox"
                          checked={requiresApproval}
                          onChange={(event) => setRequiresApproval(event.target.checked)}
                        />
                      </label>
                    )}
                    {selectedPresetFields.showApproval && requiresApproval && (
                      <label className="full-width">
                        <span>高风险动作</span>
                        <input
                          type="text"
                          placeholder="写入文件，执行命令"
                          value={approvalActions}
                          onChange={(event) => setApprovalActions(event.target.value)}
                        />
                      </label>
                    )}
                  </div>
                </div>
              )}

              {attachments.length > 0 && (
                <div className="attachment-strip">
                  {attachments.map((attachment) => (
                    <span key={attachment.id} className="attachment-pill">
                      <span>{attachment.name}</span>
                      <small>
                        {formatAttachmentSize(attachment.size)}
                        {attachment.parsedStatus ? ` / ${formatStatus(attachment.parsedStatus)}` : ""}
                        {typeof attachment.chunkCount === "number"
                          ? ` / ${attachment.chunkCount} 块`
                          : ""}
                        {attachment.uploadError ? " / 本地预览" : ""}
                      </small>
                      <button
                        type="button"
                        aria-label={`移除 ${attachment.name}`}
                        onClick={() => removeAttachment(attachment.id)}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}

              {userModelOptions.length === 0 && (
                <div className="setup-callout" role="status">
                  <div>
                    <strong>先接入一个模型</strong>
                    <span>Mindforge 不再用内置假回答；需要先添加 Provider/API Key 和模型后才能发起任务。</span>
                  </div>
                  <button type="button" className="secondary-button" onClick={openModelSetup}>
                    去模型中心
                  </button>
                </div>
              )}
              {isUploadingAttachments && (
                <div className="message info" role="status" aria-live="polite">
                  正在上传并解析文件...
                </div>
              )}
              {loadError && <div className="message error" role="alert">{loadError}</div>}
              {submitError && <div className="message error" role="alert">{submitError}</div>}

              <label className="sr-only" htmlFor="task-prompt">任务描述</label>
              <textarea
                id="task-prompt"
                className="composer-textarea"
                aria-label="任务描述"
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                placeholder="有问题，尽管问。也可以描述你希望 Mindforge 完成的工程、论文或资料整理任务。"
              />
              <div className="composer-toolbar">
                <div className="composer-tools">
                  <div className="composer-toolbox">
                    <button
                      type="button"
                      className={`composer-plus ${isToolMenuOpen ? "active" : ""}`}
                      aria-label={isToolMenuOpen ? "收起工具菜单" : "打开工具菜单"}
                      aria-expanded={isToolMenuOpen}
                      aria-controls="composer-tool-menu"
                      onClick={() => setIsToolMenuOpen((value) => !value)}
                    >
                      +
                    </button>
                    {isToolMenuOpen && (
                      <div className="composer-tool-menu" id="composer-tool-menu">
                        <button
                          type="button"
                          className={`tool-menu-item ${isTaskConfigOpen ? "active" : ""}`}
                          aria-expanded={isTaskConfigOpen}
                          aria-controls="task-config-panel"
                          onClick={() => setIsTaskConfigOpen((value) => !value)}
                        >
                          <span>任务配置</span>
                          <small>{isTaskConfigOpen ? "收起配置面板" : "展开模型、仓库和审批"}</small>
                        </button>
                        <label className="tool-menu-item upload-menu-item">
                          <input
                            type="file"
                            multiple
                            aria-label="上传文件"
                            onChange={handleAttachmentInput}
                          />
                          <span>上传文件</span>
                          <small>附加文本、代码或资料上下文</small>
                        </label>
                      </div>
                    )}
                  </div>
                  <div className="capability-chip-row" aria-label="Composer capabilities">
                    {COMPOSER_CAPABILITIES.map((capability) => (
                      <button
                        key={capability.key}
                        type="button"
                        className={`capability-chip ${
                          capabilityFlags[capability.key] ? "active" : ""
                        }`}
                        aria-pressed={capabilityFlags[capability.key]}
                        title={capability.hint}
                        onClick={() => toggleCapabilityFlag(capability.key)}
                      >
                        {capability.label}
                      </button>
                    ))}
                  </div>
                  <label className="composer-model-picker">
                    <span>模型</span>
                    <select
                      aria-label="底部模型选择"
                      value={effectiveModelId}
                      onChange={(event) => setModelOverride(event.target.value)}
                      disabled={userModelOptions.length === 0}
                    >
                      {userModelOptions.length === 0 ? (
                        <option value="">请先添加模型</option>
                      ) : (
                        userModelOptions.map((model) => (
                          <option key={model.model_id} value={model.model_id}>
                            {model.display_name} / {model.provider_id}
                          </option>
                        ))
                      )}
                    </select>
                  </label>
                  <div className="composer-chip-row">
                    <span className="composer-chip">{selectedPresetName}</span>
                    <span className="composer-chip">{formatTaskType(taskType)}</span>
                    <span className="composer-chip">{selectedModelName}</span>
                    <span className="composer-chip">{selectedRuleTemplateName}</span>
                    {selectedSkills.length > 0 && (
                      <span className="composer-chip">{selectedSkills.length} 个 Skills</span>
                    )}
                    {selectedMcpServerIds.length > 0 && (
                      <span className="composer-chip">{selectedMcpServerIds.length} 个 MCP</span>
                    )}
                    {attachments.length > 0 && (
                      <span className="composer-chip">{attachments.length} 个附件</span>
                    )}
                  </div>
                  <div className="composer-shortcut">Enter 发送，Shift+Enter 换行</div>
                </div>
                <button
                  type="button"
                  className="primary-button send-button"
                  onClick={userModelOptions.length === 0 ? openModelSetup : handleSubmit}
                  disabled={isSubmitting || isUploadingAttachments}
                >
                  {isSubmitting
                    ? <><span className="spinner" />发送中...</>
                    : userModelOptions.length === 0
                      ? "先添加模型"
                      : isUploadingAttachments
                        ? "解析文件中..."
                        : "发送任务"}
                </button>
              </div>
            </div>
          </div>
        </section>

        <aside className="panel-column">
          <div className="panel tabs-panel">
            <div className="panel-title-row">
              <h2>任务详情</h2>
              <span className="subtle">
                {activeTaskDetail ? formatStatus(activeTaskDetail.status) : "空闲"}
              </span>
            </div>
            <div className="tabs-row" role="tablist" aria-label="任务详情面板">
              {tabDescriptors.map(({ tab, count, hasData }) => (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  aria-selected={activeTab === tab}
                  className={`tab-button ${activeTab === tab ? "active" : ""} ${
                    hasData ? "has-data" : "empty"
                  }`}
                  onClick={() => setActiveTab(tab)}
                >
                  <span>{TAB_LABELS[tab]}</span>
                  {hasData && <small aria-hidden="true">{count}</small>}
                </button>
              ))}
            </div>

            {activeTab === "output" && (
              <div className="panel-content">
                <h3>最终输出</h3>
                <pre>{activeResult?.data.output || "暂无输出。"}</pre>
                {activeExecutionReport?.steps?.length ? (
                  <div className="execution-report-card">
                    <div className="panel-title-row compact-row">
                      <strong>执行报告</strong>
                      <span className="subtle">
                        {String(activeExecutionReport.runtime_boundary?.mcp_runtime || "catalog/proxy")}
                      </span>
                    </div>
                    <div className="execution-step-grid">
                      {activeExecutionReport.steps.map((step) => (
                        <div key={String(step.id)} className="execution-step">
                          <span>{String(step.label || step.id)}</span>
                          <strong>{formatStatus(String(step.status || "unknown"))}</strong>
                          <small>{String(step.summary || "")}</small>
                        </div>
                      ))}
                    </div>
                    {Array.isArray(activeExecutionReport.warnings) &&
                      activeExecutionReport.warnings.length > 0 && (
                        <div className="execution-warning-list">
                          {activeExecutionReport.warnings.map((warning, index) => (
                            <span key={`${String(warning)}-${index}`}>{String(warning)}</span>
                          ))}
                        </div>
                      )}
                  </div>
                ) : null}
                {generatedArtifacts.length > 0 && (
                  <div className="generated-artifact-list">
                    <strong>自动生成的文件</strong>
                    {generatedArtifacts.map((artifact) => (
                      <a
                        key={artifact.artifact_id}
                        className="generated-artifact-card"
                        href={`${getApiBaseUrl()}${artifact.download_url.replace(/^\/api/, "")}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <span>{artifact.filename}</span>
                        <small>
                          {artifact.format.toUpperCase()} · {Math.max(1, Math.round(artifact.size_bytes / 1024))} KB
                        </small>
                      </a>
                    ))}
                  </div>
                )}
                <div className="export-row" aria-label="导出最终输出">
                  {(["md", "pdf", "docx", "tex"] as ArtifactFormat[]).map((format) => (
                    <button
                      key={format}
                      type="button"
                      className="secondary-button export-button"
                      disabled={exportingArtifactFormat === format}
                      onClick={() => handleExportActiveOutput(format)}
                    >
                      {exportingArtifactFormat === format
                        ? "导出中..."
                        : `导出 ${format.toUpperCase()}`}
                    </button>
                  ))}
                </div>
                {artifacts.length > 0 && (
                  <div className="artifact-link-row">
                    <span>最近导出</span>
                    {artifacts.slice(0, 3).map((artifact) => (
                      <a
                        key={artifact.artifact_id}
                        href={`${getApiBaseUrl()}${artifact.download_url.replace(/^\/api/, "")}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {artifact.filename}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "stages" && (
              <div className="panel-content">
                <h3>阶段轨迹</h3>
                {activeTrace?.stages?.length ? (
                  <div className="stage-list">
                    {activeTrace.stages.map((stage) => (
                      <div key={stage.stage_id} className="stage-card">
                        <div className="stage-head">
                          <strong>{formatRole(stage.stage_name || stage.role)}</strong>
                          <span>{stage.model}</span>
                        </div>
                        <div className="stage-meta">
                          <span>{formatStatus(stage.status)}</span>
                          <span>{stage.provider}</span>
                        </div>
                        <p>{stage.summary}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-hint">该任务暂无阶段数据。</div>
                )}
              </div>
            )}

            {activeTab === "repo" && (
              <div className="panel-content">
                <h3>仓库摘要</h3>
                {activeRepo?.repo_summary ? (
                  <>
                    <p>{activeRepo.repo_summary.summary_text}</p>
                    <div className="info-block">
                      <strong>入口文件</strong>
                      <ul>
                        {activeRepo.repo_summary.entrypoints.map((entry) => (
                          <li key={entry}>{entry}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="info-block">
                      <strong>识别到的技术栈</strong>
                      <div className="provider-list">
                        {activeRepo.repo_summary.detected_stack.map((stack) => (
                          <span key={stack} className="pill">
                            {stack}
                          </span>
                        ))}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="empty-hint">该任务暂无仓库摘要。</div>
                )}
              </div>
            )}

            {activeTab === "github" && (
              <div className="panel-content">
                <h3>GitHub 上下文</h3>
                {activeGitHub ? (
                  <div className="stage-list">
                    {activeGitHub.repository && (
                      <div className="stage-card">
                        <div className="stage-head">
                          <strong>{activeGitHub.repository.full_name}</strong>
                          <a href={activeGitHub.repository.html_url} target="_blank" rel="noreferrer">
                            打开
                          </a>
                        </div>
                        <div className="stage-meta">
                          <span>分支：{activeGitHub.repository.default_branch}</span>
                          <span>语言：{activeGitHub.repository.primary_language || "未知"}</span>
                        </div>
                        <p>{activeGitHub.repository.description || "暂无仓库描述。"}</p>
                      </div>
                    )}
                    {activeGitHub.issue && (
                      <div className="stage-card">
                        <div className="stage-head">
                          <strong>Issue #{activeGitHub.issue.number}</strong>
                          <a href={activeGitHub.issue.html_url} target="_blank" rel="noreferrer">
                            打开
                          </a>
                        </div>
                        <div className="stage-meta">
                          <span>{formatStatus(activeGitHub.issue.state)}</span>
                          <span>{activeGitHub.issue.author || "未知"}</span>
                        </div>
                        <p>{activeGitHub.issue.title}</p>
                        {activeGitHub.issue.body_excerpt && <p>{activeGitHub.issue.body_excerpt}</p>}
                      </div>
                    )}
                    {activeGitHub.pull_request && (
                      <div className="stage-card">
                        <div className="stage-head">
                          <strong>PR #{activeGitHub.pull_request.number}</strong>
                          <a href={activeGitHub.pull_request.html_url} target="_blank" rel="noreferrer">
                            打开
                          </a>
                        </div>
                        <div className="stage-meta">
                          <span>{formatStatus(activeGitHub.pull_request.state)}</span>
                          <span>
                            {activeGitHub.pull_request.head_ref || "-"} → {activeGitHub.pull_request.base_ref || "-"}
                          </span>
                        </div>
                        <p>{activeGitHub.pull_request.title}</p>
                        {activeGitHub.pull_request.body_excerpt && (
                          <p>{activeGitHub.pull_request.body_excerpt}</p>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="empty-hint">该任务暂无 GitHub 上下文。</div>
                )}
              </div>
            )}

            {activeTab === "academic" && (
              <div className="panel-content">
                <h3>论文上下文</h3>
                {activeAcademic ? (
                  <div className="stage-list">
                    {activeAcademic.journal && (
                      <div className="stage-card">
                        <div className="stage-head">
                          <strong>{activeAcademic.journal.journal_name || "期刊"}</strong>
                          <span>{formatStatus(activeAcademic.journal.status)}</span>
                        </div>
                        {activeAcademic.journal.journal_url && (
                          <a
                            href={activeAcademic.journal.journal_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            打开投稿指南
                          </a>
                        )}
                        {activeAcademic.journal.title && <p>{activeAcademic.journal.title}</p>}
                        {activeAcademic.journal.excerpt && (
                          <p>{activeAcademic.journal.excerpt}</p>
                        )}
                      </div>
                    )}
                    {activeAcademic.reference_papers.map((reference, index) => (
                      <div key={`${reference.url}-${index}`} className="stage-card">
                        <div className="stage-head">
                          <strong>参考论文 {index + 1}</strong>
                          <span>{formatStatus(reference.status)}</span>
                        </div>
                        <a href={reference.url} target="_blank" rel="noreferrer">
                          {reference.title || reference.url}
                        </a>
                        {reference.excerpt && <p>{reference.excerpt}</p>}
                      </div>
                    ))}
                    {activeAcademic.warnings.map((warning) => (
                      <div key={warning} className="message error">
                        {warning}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-hint">该任务暂无论文上下文。</div>
                )}
              </div>
            )}

            {activeTab === "approval" && (
              <div className="panel-content">
                <h3>审批</h3>
                {activeApproval ? (
                  <div className="approval-card">
                    <div className="stage-head">
                      <strong>{activeApproval.summary}</strong>
                      <span>{formatStatus(activeApproval.status)}</span>
                    </div>
                    <div className="approval-meta">
                      <span>风险：{formatRisk(activeApproval.risk_level)}</span>
                      <span>更新：{formatDate(activeApproval.updated_at)}</span>
                    </div>
                    <div className="provider-list">
                      {activeApproval.actions.map((action) => (
                        <span key={action} className="pill">
                          {action}
                        </span>
                      ))}
                    </div>
                    {activeApproval.decision_comment && (
                      <p className="subtle">备注：{activeApproval.decision_comment}</p>
                    )}
                    {activeTaskDetail?.status === "pending_approval" && activeApproval.status === "pending" && (
                      <div className="action-row approval-actions">
                        <button
                          type="button"
                          className="primary-button"
                          onClick={() => handleApprovalDecision("approve")}
                        >
                          批准并继续
                        </button>
                        <button
                          type="button"
                          className="secondary-button"
                          onClick={() => handleApprovalDecision("reject")}
                        >
                          拒绝
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="empty-hint">该任务没有审批记录。</div>
                )}
              </div>
            )}

            {activeTab === "metadata" && (
              <div className="panel-content">
                <h3>任务元数据</h3>
                <pre>{JSON.stringify(activeTaskDetail?.metadata || {}, null, 2)}</pre>
              </div>
            )}

            {activeTab === "canvas" && (
              <div className="panel-content">
                <h3>画布 / 工具结果</h3>
                <div className="canvas-panel">
                  <strong>工具能力已接入执行链</strong>
                  <p>
                    深度分析会影响模型调用；联网会注入搜索结果；代码执行会运行显式 Python
                    代码块；画布会把最终输出保存为可编辑 artifact。
                  </p>
                  <div className="canvas-status-grid">
                    {COMPOSER_CAPABILITIES.map((capability) => (
                      <span
                        key={capability.key}
                        className={`composer-chip ${
                          activeToolFlags[capability.key] ? "active" : ""
                        }`}
                      >
                        {capability.label}: {activeToolFlags[capability.key] ? "已启用" : "未启用"}
                      </span>
                    ))}
                  </div>
                  {Object.keys(activeToolContext).length > 0 && (
                    <>
                      <h4>工具上下文</h4>
                      <pre>{JSON.stringify(activeToolContext, null, 2)}</pre>
                    </>
                  )}
                  <h4>画布产物</h4>
                  {canvasArtifacts.length === 0 ? (
                    <p className="empty-hint">本任务没有生成画布产物。开启“画布”后重新发送即可生成。</p>
                  ) : (
                    <div className="canvas-artifact-list">
                      {canvasArtifacts.map((artifact, index) => {
                        const artifactId = String(artifact.artifact_id || index);
                        const isSaving = savingCanvasArtifactId === artifactId;
                        return (
                          <article
                            className="canvas-artifact-card"
                            key={artifactId}
                          >
                            <div className="stage-head">
                              <strong>{String(artifact.title || "未命名产物")}</strong>
                              <span className="subtle">
                                {String(artifact.kind || "artifact")}
                                {artifact.editable ? " / 可编辑" : ""}
                                {artifact.version ? ` / v${artifact.version}` : ""}
                              </span>
                            </div>
                            {Array.isArray(artifact.versions) && artifact.versions.length > 0 && (
                              <details className="canvas-version-list">
                                <summary>版本历史（{artifact.versions.length}）</summary>
                                {artifact.versions
                                  .slice()
                                  .reverse()
                                  .slice(0, 8)
                                  .map((version) => (
                                    <div
                                      key={`${artifactId}-${version.version}`}
                                      className="canvas-version-item"
                                    >
                                      <strong>v{version.version}</strong>
                                      <span>{version.updated_at ? formatDate(version.updated_at) : "-"}</span>
                                      <small>{version.source || "manual"}</small>
                                    </div>
                                  ))}
                              </details>
                            )}
                            {artifact.editable ? (
                              <>
                                <textarea
                                  className="canvas-editor"
                                  aria-label={`${artifact.title || "画布产物"} 内容`}
                                  value={getCanvasDraft(artifact)}
                                  onChange={(event) =>
                                    setCanvasDrafts((current) => ({
                                      ...current,
                                      [artifactId]: event.target.value,
                                    }))
                                  }
                                />
                                <div className="action-row">
                                  <button
                                    type="button"
                                    className="secondary-button"
                                    disabled={isSaving}
                                    onClick={() => handleSaveCanvasArtifact(artifact)}
                                  >
                                    {isSaving ? "保存中..." : "保存画布"}
                                  </button>
                                </div>
                              </>
                            ) : (
                              <pre>{artifactContentToText(artifact.content)}</pre>
                            )}
                          </article>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </aside>
      </div>
    );
  }

  function renderProjectCenter() {
    return (
      <div className="settings-shell tool-center-shell">
        {settingsMessage && <div className="message success">{settingsMessage}</div>}
        {settingsError && <div className="message error">{settingsError}</div>}

        <div className="panel settings-panel">
          <div className="panel-title-row">
            <h2>项目空间</h2>
            <span className="subtle">
              像 ChatGPT Projects / Claude Projects 一样管理长期上下文。
            </span>
          </div>
          <div className="tool-center-grid">
            <section className="settings-card tool-editor-card">
              <div className="stage-head">
                <strong>创建项目空间</strong>
                <span>说明、记忆、文件和工具</span>
              </div>
              <label>
                <span>Project ID</span>
                <input
                  type="text"
                  value={newProjectSpace.project_id}
                  placeholder="mindforge-dev"
                  onChange={(event) =>
                    setNewProjectSpace((current) => ({
                      ...current,
                      project_id: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>项目名称</span>
                <input
                  type="text"
                  value={newProjectSpace.display_name}
                  placeholder="Mindforge 开发"
                  onChange={(event) =>
                    setNewProjectSpace((current) => ({
                      ...current,
                      display_name: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="full-width">
                <span>项目说明</span>
                <textarea
                  value={newProjectSpace.description}
                  placeholder="这个项目是什么，目标用户是谁。"
                  onChange={(event) =>
                    setNewProjectSpace((current) => ({
                      ...current,
                      description: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="full-width">
                <span>项目指令</span>
                <textarea
                  value={newProjectSpace.instructions}
                  placeholder="长期生效的工作规则、代码风格、产品原则。"
                  onChange={(event) =>
                    setNewProjectSpace((current) => ({
                      ...current,
                      instructions: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="full-width">
                <span>项目记忆</span>
                <textarea
                  value={newProjectSpace.memory}
                  placeholder="关键决策、用户偏好、长期上下文。"
                  onChange={(event) =>
                    setNewProjectSpace((current) => ({
                      ...current,
                      memory: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>默认预设</span>
                <input
                  type="text"
                  value={newProjectSpace.default_preset_mode}
                  placeholder="code-engineering"
                  onChange={(event) =>
                    setNewProjectSpace((current) => ({
                      ...current,
                      default_preset_mode: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>仓库路径</span>
                <input
                  type="text"
                  value={newProjectSpace.repo_path}
                  placeholder="E:\\CODE\\agent助手"
                  onChange={(event) =>
                    setNewProjectSpace((current) => ({
                      ...current,
                      repo_path: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>GitHub 仓库</span>
                <input
                  type="text"
                  value={newProjectSpace.github_repo}
                  placeholder="owner/repo"
                  onChange={(event) =>
                    setNewProjectSpace((current) => ({
                      ...current,
                      github_repo: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>Skills</span>
                <input
                  type="text"
                  value={newProjectSpace.skill_ids}
                  placeholder="frontend-design, gsd-do"
                  onChange={(event) =>
                    setNewProjectSpace((current) => ({
                      ...current,
                      skill_ids: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>MCP Servers</span>
                <input
                  type="text"
                  value={newProjectSpace.mcp_server_ids}
                  placeholder="filesystem, browser"
                  onChange={(event) =>
                    setNewProjectSpace((current) => ({
                      ...current,
                      mcp_server_ids: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>文件 ID</span>
                <input
                  type="text"
                  value={newProjectSpace.file_ids}
                  placeholder="上传文件后填 file_id"
                  onChange={(event) =>
                    setNewProjectSpace((current) => ({
                      ...current,
                      file_ids: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>标签</span>
                <input
                  type="text"
                  value={newProjectSpace.tags}
                  placeholder="研发, 论文, 客户A"
                  onChange={(event) =>
                    setNewProjectSpace((current) => ({
                      ...current,
                      tags: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="toggle-row">
                <span>启用</span>
                <input
                  type="checkbox"
                  checked={newProjectSpace.enabled}
                  onChange={(event) =>
                    setNewProjectSpace((current) => ({
                      ...current,
                      enabled: event.target.checked,
                    }))
                  }
                />
              </label>
              <button type="button" className="primary-button" onClick={handleSaveProjectSpace}>
                保存项目空间
              </button>
            </section>

            <section className="settings-card">
              <div className="stage-head">
                <strong>如何使用</strong>
                <span>任务配置里选择</span>
              </div>
              <p>
                项目空间会在每次任务中注入项目说明、长期记忆、默认仓库、GitHub 仓库、
                Skills、MCP Server 和项目文件片段。它是后续跨会话记忆/RAG 的基础。
              </p>
              <div className="provider-list inline-pills">
                <span className="pill accent">{projectSpaces.length} 个项目</span>
                <span className="pill">{projectSpaces.filter((item) => item.enabled).length} 个启用</span>
              </div>
            </section>
          </div>
        </div>

        <div className="panel settings-panel">
          <div className="panel-title-row">
            <h2>项目列表</h2>
            <span className="subtle">{projectSpaces.length} 个空间</span>
          </div>
          <div className="settings-grid">
            {projectSpaces.length === 0 ? (
              <div className="empty-hint">还没有项目空间。先创建一个，再在任务配置中选择。</div>
            ) : (
              projectSpaces.map((project) => (
                <article className="settings-card" key={project.project_id}>
                  <div className="stage-head">
                    <strong>{project.display_name}</strong>
                    <span className={`pill ${project.enabled ? "accent" : "muted"}`}>
                      {project.enabled ? "启用" : "禁用"}
                    </span>
                  </div>
                  <code>{project.project_id}</code>
                  <p>{project.description || "暂无说明。"}</p>
                  <div className="provider-list inline-pills">
                    <span className="pill">{project.file_count} 个文件</span>
                    <span className="pill">{project.skill_ids.length} 个 Skill</span>
                    <span className="pill">{project.mcp_server_ids.length} 个 MCP</span>
                  </div>
                  {project.instructions && <p className="subtle">指令：{project.instructions}</p>}
                  {project.memory && <p className="subtle">记忆：{project.memory}</p>}
                  <div className="action-row">
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => {
                        setSelectedProjectId(project.project_id);
                        setView("workspace");
                        setActiveNavId("new-task");
                        setIsTaskConfigOpen(true);
                      }}
                    >
                      用于新任务
                    </button>
                    <button
                      type="button"
                      className="secondary-button danger-button"
                      onClick={() => void handleDeleteProjectSpace(project)}
                    >
                      删除
                    </button>
                  </div>
                </article>
              ))
            )}
          </div>
        </div>
      </div>
    );
  }

  function renderToolCenter() {
    return (
      <div className="settings-shell tool-center-shell">
        {settingsMessage && <div className="message success">{settingsMessage}</div>}
        {settingsError && <div className="message error">{settingsError}</div>}

        <div className="panel settings-panel">
          <div className="panel-title-row">
            <h2>工具与 Skills 中心</h2>
            <span className="subtle">MCP、Skills 和文档能力</span>
          </div>
          <div className="tool-center-grid">
            <section className="settings-card tool-editor-card">
              <div className="stage-head">
                <strong>添加 MCP Server</strong>
                <span>HTTP JSON-RPC</span>
              </div>
              <label>
                <span>Server ID</span>
                <input
                  type="text"
                  value={newMcpServer.server_id}
                  placeholder="filesystem"
                  onChange={(event) =>
                    setNewMcpServer((current) => ({
                      ...current,
                      server_id: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>显示名称</span>
                <input
                  type="text"
                  value={newMcpServer.display_name}
                  placeholder="本地文件系统"
                  onChange={(event) =>
                    setNewMcpServer((current) => ({
                      ...current,
                      display_name: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>传输方式</span>
                <select
                  value={newMcpServer.transport}
                  onChange={(event) =>
                    setNewMcpServer((current) => ({
                      ...current,
                      transport: event.target.value as "http-jsonrpc" | "stdio",
                    }))
                  }
                >
                  <option value="http-jsonrpc">HTTP JSON-RPC</option>
                  <option value="stdio">stdio 进程</option>
                </select>
              </label>
              <label>
                <span>Endpoint URL</span>
                <input
                  type="text"
                  value={newMcpServer.endpoint_url}
                  placeholder="http://127.0.0.1:8765/mcp"
                  onChange={(event) =>
                    setNewMcpServer((current) => ({
                      ...current,
                      endpoint_url: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>stdio 命令</span>
                <input
                  type="text"
                  value={newMcpServer.command}
                  placeholder="node / python / uvx"
                  onChange={(event) =>
                    setNewMcpServer((current) => ({
                      ...current,
                      command: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>stdio 参数</span>
                <input
                  type="text"
                  value={newMcpServer.args}
                  placeholder="server.js, --stdio"
                  onChange={(event) =>
                    setNewMcpServer((current) => ({
                      ...current,
                      args: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>工作目录</span>
                <input
                  type="text"
                  value={newMcpServer.working_directory}
                  placeholder="可选"
                  onChange={(event) =>
                    setNewMcpServer((current) => ({
                      ...current,
                      working_directory: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>Headers JSON</span>
                <textarea
                  className="json-textarea"
                  value={newMcpServer.headers_json}
                  placeholder='{"Authorization":"Bearer ..."}'
                  onChange={(event) =>
                    setNewMcpServer((current) => ({
                      ...current,
                      headers_json: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>Env JSON</span>
                <textarea
                  className="json-textarea"
                  value={newMcpServer.env_json}
                  placeholder='{"TOKEN":"..."}'
                  onChange={(event) =>
                    setNewMcpServer((current) => ({
                      ...current,
                      env_json: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>允许工具</span>
                <input
                  type="text"
                  value={newMcpServer.allowed_tools}
                  placeholder="read_file, search"
                  onChange={(event) =>
                    setNewMcpServer((current) => ({
                      ...current,
                      allowed_tools: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>禁用工具</span>
                <input
                  type="text"
                  value={newMcpServer.blocked_tools}
                  placeholder="delete_file, shell"
                  onChange={(event) =>
                    setNewMcpServer((current) => ({
                      ...current,
                      blocked_tools: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="toggle-row">
                <span>调用工具前需要审批</span>
                <input
                  type="checkbox"
                  checked={newMcpServer.tool_call_requires_approval}
                  onChange={(event) =>
                    setNewMcpServer((current) => ({
                      ...current,
                      tool_call_requires_approval: event.target.checked,
                    }))
                  }
                />
              </label>
              <label>
                <span>备注</span>
                <input
                  type="text"
                  value={newMcpServer.notes}
                  placeholder="这个 MCP 提供哪些工具"
                  onChange={(event) =>
                    setNewMcpServer((current) => ({
                      ...current,
                      notes: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="toggle-row">
                <span>启用</span>
                <input
                  type="checkbox"
                  checked={newMcpServer.enabled}
                  onChange={(event) =>
                    setNewMcpServer((current) => ({
                      ...current,
                      enabled: event.target.checked,
                    }))
                  }
                />
              </label>
              <button
                type="button"
                className="primary-button"
                onClick={handleSaveMcpServer}
              >
                保存 MCP Server
              </button>
            </section>

            <section className="settings-card">
              <div className="stage-head">
                <strong>Skills 目录</strong>
                <span>{skills.length} 个</span>
              </div>
              <p className="subtle">
                Mindforge 会扫描本机 SKILL.md，并在你选择 Skills 时把对应说明注入模型上下文。
              </p>
              <div className="skill-list compact-list">
                {skills.length === 0 ? (
                  <div className="empty-hint">未发现 Skills。请检查后端 skill_roots 配置。</div>
                ) : (
                  skills.slice(0, 12).map((skill) => (
                    <article key={skill.skill_id} className="skill-card">
                      <div className="stage-head">
                        <strong>{skill.name}</strong>
                        <span className={`pill ${skill.enabled ? "accent" : "muted"}`}>
                          {skill.enabled ? "启用" : "禁用"} / {skill.trust_level}
                        </span>
                      </div>
                      <code>{skill.skill_id}</code>
                      <p>{skill.description || "暂无描述。"}</p>
                      {skill.notes && <p className="subtle">{skill.notes}</p>}
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => void handleToggleSkill(skill)}
                      >
                        {skill.enabled ? "禁用 Skill" : "启用 Skill"}
                      </button>
                    </article>
                  ))
                )}
              </div>
            </section>
          </div>
        </div>

        <div className="panel settings-panel">
          <div className="panel-title-row">
            <h2>MCP Server 列表</h2>
            <span className="subtle">{mcpServers.length} 个已配置</span>
          </div>
          <div className="settings-grid">
            {mcpServers.length === 0 ? (
              <div className="empty-hint">
                还没有 MCP Server。添加后可在任务配置中选择并注入工具目录。
              </div>
            ) : (
              mcpServers.map((server) => {
                const toolResult = mcpToolResults[server.server_id];
                const loadingTools = loadingMcpToolsServerId === server.server_id;
                return (
                  <article key={server.server_id} className="settings-card">
                    <div className="stage-head">
                      <strong>{server.display_name}</strong>
                      <div className="provider-list inline-pills">
                        <span className={`pill ${server.enabled ? "accent" : "muted"}`}>
                          {server.enabled ? "启用" : "禁用"}
                        </span>
                        {server.headers_configured && (
                          <span className="pill muted">Headers 已脱敏</span>
                        )}
                        {server.env_configured && (
                          <span className="pill muted">Env 已脱敏</span>
                        )}
                        {server.tool_call_requires_approval !== false && (
                          <span className="pill muted">调用需审批</span>
                        )}
                      </div>
                    </div>
                    <div className="subtle">
                      {server.transport === "stdio"
                        ? `stdio: ${server.command || "未配置命令"}`
                        : server.endpoint_url}
                    </div>
                    {(server.allowed_tools?.length || server.blocked_tools?.length) ? (
                      <div className="provider-list inline-pills">
                        {server.allowed_tools?.length ? (
                          <span className="pill">允许 {server.allowed_tools.length}</span>
                        ) : null}
                        {server.blocked_tools?.length ? (
                          <span className="pill muted">禁用 {server.blocked_tools.length}</span>
                        ) : null}
                      </div>
                    ) : null}
                    {server.notes && <p>{server.notes}</p>}
                    <div className="action-row">
                      <button
                        type="button"
                        className="secondary-button"
                        disabled={loadingTools}
                        onClick={() => handleLoadMcpTools(server)}
                      >
                        {loadingTools ? "读取中..." : "读取工具目录"}
                      </button>
                      <button
                        type="button"
                        className="secondary-button danger-button"
                        onClick={() => handleDeleteMcpServer(server)}
                      >
                        删除
                      </button>
                    </div>
                    {toolResult && (
                      <div className="mcp-tool-list">
                        <strong>状态：{toolResult.status}</strong>
                        {toolResult.error_message && (
                          <p className="message error">{toolResult.error_message}</p>
                        )}
                        {toolResult.tools.map((tool) => (
                          <div key={tool.name} className="mcp-tool-item">
                            <code>{tool.name}</code>
                            <span>{tool.description || "暂无描述"}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </article>
                );
              })
            )}
          </div>
        </div>

        <div className="panel settings-panel">
          <div className="panel-title-row">
            <h2>MCP 调用审计</h2>
            <span className="subtle">{mcpAuditRecords.length} 条最近记录</span>
          </div>
          {mcpAuditRecords.length === 0 ? (
            <div className="empty-hint">
              暂无工具调用记录。直接调用 `/api/mcp/servers/:id/tools/call` 或后续自动工具执行都会写入这里。
            </div>
          ) : (
            <div className="mcp-audit-list">
              {mcpAuditRecords.slice(0, 12).map((record) => (
                <article key={record.audit_id} className="mcp-audit-item">
                  <div className="stage-head">
                    <strong>{record.tool_name}</strong>
                    <span className={`pill ${record.status === "ok" ? "accent" : "muted"}`}>
                      {formatStatus(record.status)}
                    </span>
                  </div>
                  <small>
                    {record.server_id} · {record.approved ? "已审批" : "未审批"} ·{" "}
                    {formatDate(record.created_at)}
                  </small>
                  {record.blocked_reason && <p>{record.blocked_reason}</p>}
                  {record.error_message && <p className="message error">{record.error_message}</p>}
                  {record.arguments_preview && <code>{record.arguments_preview}</code>}
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  function renderModelControl() {
    return (
      <div className="settings-shell">
        {settingsMessage && <div className="message success">{settingsMessage}</div>}
        {settingsError && <div className="message error">{settingsError}</div>}

        <div className="panel settings-panel">
          <div className="panel-title-row">
            <h2>模型控制中心</h2>
            <span className="subtle">优先级和启用状态</span>
          </div>
          <div className="settings-grid">
            {models.map((model) => (
              <div key={model.model_id} className="settings-card">
                <div className="stage-head">
                  <strong>{model.display_name}</strong>
                  <span>{model.provider_id}</span>
                </div>
                <div className="subtle">{model.upstream_model}</div>
                <label>
                  <span>优先级</span>
                  <select
                    value={model.priority}
                    onChange={(event) =>
                      setModels((previous) =>
                        previous.map((item) =>
                          item.model_id === model.model_id
                            ? {
                                ...item,
                                priority: event.target.value as ModelSummary["priority"],
                              }
                            : item,
                        ),
                      )
                    }
                  >
                    <option value="high">{PRIORITY_LABELS.high}</option>
                    <option value="medium">{PRIORITY_LABELS.medium}</option>
                    <option value="low">{PRIORITY_LABELS.low}</option>
                    <option value="disabled">{PRIORITY_LABELS.disabled}</option>
                  </select>
                </label>
                <label className="toggle-row">
                  <span>启用</span>
                  <input
                    type="checkbox"
                    checked={model.enabled}
                    onChange={(event) =>
                      setModels((previous) =>
                        previous.map((item) =>
                          item.model_id === model.model_id
                            ? { ...item, enabled: event.target.checked }
                            : item,
                        ),
                      )
                    }
                  />
                </label>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => handleModelSave(model)}
                >
                  保存模型设置
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="panel settings-panel provider-panel">
          <div className="panel-title-row">
            <h2>模型服务商/API 管理</h2>
            <span className="subtle">连接设置和密钥状态</span>
          </div>
          <p className="subtle provider-note">
            API key 只保留在后端环境变量中。这里仅编辑环境变量名称，并显示密钥是否已配置。
          </p>
          <div className="settings-grid provider-grid">
            {providers.length === 0 ? (
              <div className="empty-hint">暂无模型服务商数据。</div>
            ) : (
              providers.map((provider) => {
                const testMessage = providerTestMessages[provider.provider_id];
                return (
                  <div key={provider.provider_id} className="settings-card provider-card">
                    <div className="stage-head">
                      <strong>{provider.display_name}</strong>
                      <span className={`pill ${provider.enabled ? "accent" : "muted"} ${testingProviderId === provider.provider_id ? "pulse" : ""}`}>
                        {provider.enabled ? "已启用" : "已禁用"}
                      </span>
                    </div>
                    {provider.description && (
                      <div className="subtle">{provider.description}</div>
                    )}

                    <div className="provider-secret-row">
                      <span>API key</span>
                      <strong className={provider.api_key_configured ? "key-ok" : "key-missing"}>
                        {provider.api_key_configured ? "已配置" : "缺失"}
                      </strong>
                    </div>

                    <label className="toggle-row">
                      <span>启用</span>
                      <input
                        type="checkbox"
                        aria-label={`${provider.display_name} 启用状态`}
                        checked={provider.enabled}
                        onChange={(event) =>
                          updateProviderDraft(provider.provider_id, {
                            enabled: event.target.checked,
                          })
                        }
                      />
                    </label>
                    <label>
                      <span>基础 URL</span>
                      <input
                        type="text"
                        aria-label={`${provider.display_name} 基础 URL`}
                        value={provider.api_base_url ?? ""}
                        placeholder="https://api.example.com/v1"
                        onChange={(event) =>
                          updateProviderDraft(provider.provider_id, {
                            api_base_url: event.target.value,
                          })
                        }
                      />
                    </label>
                    <label>
                      <span>协议</span>
                      <input
                        type="text"
                        aria-label={`${provider.display_name} 协议`}
                        value={provider.protocol ?? ""}
                        placeholder="openai, openai-chat, openai-compatible, anthropic"
                        onChange={(event) =>
                          updateProviderDraft(provider.provider_id, {
                            protocol: event.target.value,
                          })
                        }
                      />
                    </label>
                    <label>
                      <span>API key 环境变量</span>
                      <input
                        type="text"
                        aria-label={`${provider.display_name} API key 环境变量`}
                        value={provider.api_key_env ?? ""}
                        placeholder="OPENAI_API_KEY"
                        onChange={(event) =>
                          updateProviderDraft(provider.provider_id, {
                            api_key_env: event.target.value,
                          })
                        }
                      />
                    </label>
                    <label>
                      <span>Anthropic URL</span>
                      <input
                        type="text"
                        aria-label={`${provider.display_name} Anthropic URL`}
                        value={provider.anthropic_api_base_url ?? ""}
                        placeholder="可选的 Anthropic-compatible endpoint"
                        onChange={(event) =>
                          updateProviderDraft(provider.provider_id, {
                            anthropic_api_base_url: event.target.value,
                          })
                        }
                      />
                    </label>

                    <div className="action-row provider-actions">
                      <button
                        type="button"
                        className="secondary-button"
                        aria-label={`保存 ${provider.display_name} 模型服务商`}
                        onClick={() => handleProviderSave(provider)}
                      >
                        保存模型服务商
                      </button>
                      <button
                        type="button"
                        className="secondary-button"
                        aria-label={`测试 ${provider.display_name} 连接`}
                        disabled={testingProviderId === provider.provider_id}
                        onClick={() => handleProviderTest(provider)}
                      >
                        {testingProviderId === provider.provider_id
                          ? "测试中..."
                          : "测试连接"}
                      </button>
                    </div>
                    {testMessage && (
                      <div className={`message ${testMessage.status}`}>
                        {testMessage.text}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    );
  }

  function renderModelControlV2() {
    return (
      <div className="settings-shell view-enter">
        {settingsMessage && <div className="message success">{settingsMessage}</div>}
        {settingsError && <div className="message error">{settingsError}</div>}

        <div className="panel settings-panel provider-panel">
          <div className="panel-title-row">
            <h2>模型服务商/API 管理</h2>
            <span className="subtle">用户自定义 Provider 和 API key</span>
          </div>
          <p className="subtle provider-note">
            这里不再预置 OpenAI、Kimi、GLM 或豆包。Provider、API 地址和 API key 都由用户自己添加；API key 只保存在本地忽略文件，不会从接口返回。
          </p>
          <div className="control-grid">
            <label>
              <span>Provider ID</span>
              <input
                type="text"
                value={newProvider.provider_id}
                placeholder="volces-ark"
                onChange={(event) =>
                  setNewProvider((current) => ({
                    ...current,
                    provider_id: event.target.value,
                  }))
                }
              />
            </label>
            <label>
              <span>显示名称</span>
              <input
                type="text"
                value={newProvider.display_name}
                placeholder="Volces Ark"
                onChange={(event) =>
                  setNewProvider((current) => ({
                    ...current,
                    display_name: event.target.value,
                  }))
                }
              />
            </label>
            <label className="full-width">
              <span>描述</span>
              <input
                type="text"
                value={newProvider.description || ""}
                placeholder="用于代码工程任务的豆包模型服务商"
                onChange={(event) =>
                  setNewProvider((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
              />
            </label>
            <label>
              <span>基础 URL</span>
              <input
                type="text"
                value={newProvider.api_base_url || ""}
                placeholder="https://ark.cn-beijing.volces.com/api/coding/v3"
                onChange={(event) =>
                  setNewProvider((current) => ({
                    ...current,
                    api_base_url: event.target.value,
                  }))
                }
              />
            </label>
            <label>
              <span>协议</span>
              <select
                value={newProvider.protocol || "openai-compatible"}
                onChange={(event) =>
                  setNewProvider((current) => ({
                    ...current,
                    protocol: event.target.value,
                  }))
                }
              >
                <option value="openai-compatible">OpenAI 兼容</option>
                <option value="openai">OpenAI</option>
                <option value="openai-chat">OpenAI Chat</option>
                <option value="anthropic">Anthropic</option>
              </select>
            </label>
            <label>
              <span>API key</span>
              <input
                type="password"
                value={newProvider.api_key || ""}
                placeholder="粘贴 API key"
                onChange={(event) =>
                  setNewProvider((current) => ({
                    ...current,
                    api_key: event.target.value,
                  }))
                }
              />
            </label>
            <label>
              <span>API key 环境变量</span>
              <input
                type="text"
                value={newProvider.api_key_env || ""}
                placeholder="ARK_API_KEY"
                onChange={(event) =>
                  setNewProvider((current) => ({
                    ...current,
                    api_key_env: event.target.value,
                  }))
                }
              />
            </label>
            <label className="full-width">
              <span>Anthropic URL</span>
              <input
                type="text"
                value={newProvider.anthropic_api_base_url || ""}
                placeholder="可选的 Anthropic-compatible endpoint"
                onChange={(event) =>
                  setNewProvider((current) => ({
                    ...current,
                    anthropic_api_base_url: event.target.value,
                  }))
                }
              />
            </label>
            <label className="toggle-row">
              <span>启用</span>
              <input
                type="checkbox"
                checked={newProvider.enabled}
                onChange={(event) =>
                  setNewProvider((current) => ({
                    ...current,
                    enabled: event.target.checked,
                  }))
                }
              />
            </label>
          </div>
          <div className="action-row">
            <button type="button" className="primary-button" onClick={handleCreateProvider}>
              添加模型服务商
            </button>
            <div className="subtle">先添加 Provider/API，再添加具体模型。</div>
          </div>

          <div className="settings-grid provider-grid">
            {providers.length === 0 ? (
              <div className="empty-hint">还没有用户模型服务商。请先添加 API。</div>
            ) : (
              providers.map((provider) => {
                const testMessage = providerTestMessages[provider.provider_id];
                return (
                  <div key={provider.provider_id} className="settings-card provider-card">
                    <div className="stage-head">
                      <strong>{provider.display_name}</strong>
                      <span className={`pill ${provider.enabled ? "accent" : "muted"} ${testingProviderId === provider.provider_id ? "pulse" : ""}`}>
                        {provider.enabled ? "已启用" : "已禁用"}
                      </span>
                    </div>
                    <div className="provider-secret-row">
                      <span>API key</span>
                      <strong className={provider.api_key_configured ? "key-ok" : "key-missing"}>
                        {provider.api_key_configured ? "已配置" : "缺失"}
                      </strong>
                    </div>
                    <label className="toggle-row">
                      <span>启用</span>
                      <input
                        type="checkbox"
                        aria-label={`${provider.display_name} 启用状态`}
                        checked={provider.enabled}
                        onChange={(event) =>
                          updateProviderDraft(provider.provider_id, {
                            enabled: event.target.checked,
                          })
                        }
                      />
                    </label>
                    <label>
                      <span>显示名称</span>
                      <input
                        type="text"
                        aria-label={`${provider.display_name} 显示名称`}
                        value={provider.display_name}
                        onChange={(event) =>
                          updateProviderDraft(provider.provider_id, {
                            display_name: event.target.value,
                          })
                        }
                      />
                    </label>
                    <label>
                      <span>描述</span>
                      <input
                        type="text"
                        aria-label={`${provider.display_name} 描述`}
                        value={provider.description ?? ""}
                        onChange={(event) =>
                          updateProviderDraft(provider.provider_id, {
                            description: event.target.value,
                          })
                        }
                      />
                    </label>
                    <label>
                      <span>基础 URL</span>
                      <input
                        type="text"
                        aria-label={`${provider.display_name} 基础 URL`}
                        value={provider.api_base_url ?? ""}
                        placeholder="https://api.example.com/v1"
                        onChange={(event) =>
                          updateProviderDraft(provider.provider_id, {
                            api_base_url: event.target.value,
                          })
                        }
                      />
                    </label>
                    <label>
                      <span>协议</span>
                      <select
                        aria-label={`${provider.display_name} 协议`}
                        value={provider.protocol ?? "openai-compatible"}
                        onChange={(event) =>
                          updateProviderDraft(provider.provider_id, {
                            protocol: event.target.value,
                          })
                        }
                      >
                        <option value="openai-compatible">OpenAI 兼容</option>
                        <option value="openai">OpenAI</option>
                        <option value="openai-chat">OpenAI Chat</option>
                        <option value="anthropic">Anthropic</option>
                      </select>
                    </label>
                    <label>
                      <span>API key</span>
                      <input
                        type="password"
                        aria-label={`${provider.display_name} API key`}
                        value={providerApiKeys[provider.provider_id] ?? ""}
                        placeholder={
                          provider.api_key_configured
                            ? "留空则不修改已保存 API key"
                            : "粘贴 API key"
                        }
                        onChange={(event) =>
                          setProviderApiKeys((previous) => ({
                            ...previous,
                            [provider.provider_id]: event.target.value,
                          }))
                        }
                      />
                    </label>
                    <label>
                      <span>API key 环境变量</span>
                      <input
                        type="text"
                        aria-label={`${provider.display_name} API key 环境变量`}
                        value={provider.api_key_env ?? ""}
                        placeholder="OPENAI_API_KEY"
                        onChange={(event) =>
                          updateProviderDraft(provider.provider_id, {
                            api_key_env: event.target.value,
                          })
                        }
                      />
                    </label>
                    <label>
                      <span>Anthropic URL</span>
                      <input
                        type="text"
                        aria-label={`${provider.display_name} Anthropic URL`}
                        value={provider.anthropic_api_base_url ?? ""}
                        placeholder="可选的 Anthropic-compatible endpoint"
                        onChange={(event) =>
                          updateProviderDraft(provider.provider_id, {
                            anthropic_api_base_url: event.target.value,
                          })
                        }
                      />
                    </label>
                    <div className="action-row provider-actions">
                      <button
                        type="button"
                        className="secondary-button"
                        aria-label={`保存 ${provider.display_name} 模型服务商`}
                        onClick={() => handleProviderSave(provider)}
                      >
                        保存模型服务商
                      </button>
                      <button
                        type="button"
                        className="secondary-button"
                        aria-label={`测试 ${provider.display_name} 连接`}
                        disabled={testingProviderId === provider.provider_id}
                        onClick={() => handleProviderTest(provider)}
                      >
                        {testingProviderId === provider.provider_id
                          ? "测试中..."
                          : "测试连接"}
                      </button>
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => handleDeleteProvider(provider)}
                      >
                        删除模型服务商
                      </button>
                    </div>
                    {testMessage && (
                      <div className={`message ${testMessage.status}`}>
                        {testMessage.text}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="panel settings-panel">
          <div className="panel-title-row">
            <h2>模型控制中心</h2>
            <span className="subtle">只显示用户自己添加的模型</span>
          </div>
          <div className="control-grid">
            <label>
              <span>模型 ID</span>
              <input
                type="text"
                value={newModel.model_id}
                placeholder="doubao-seed-2.0-lite"
                onChange={(event) =>
                  setNewModel((current) => ({
                    ...current,
                    model_id: event.target.value,
                    upstream_model: current.upstream_model || event.target.value,
                  }))
                }
              />
            </label>
            <label>
              <span>显示名称</span>
              <input
                type="text"
                value={newModel.display_name}
                placeholder="Doubao Seed 2.0 Lite"
                onChange={(event) =>
                  setNewModel((current) => ({
                    ...current,
                    display_name: event.target.value,
                  }))
                }
              />
            </label>
            <label>
              <span>模型服务商</span>
              <select
                value={newModel.provider_id || providers[0]?.provider_id || ""}
                disabled={providers.length === 0}
                onChange={(event) =>
                  setNewModel((current) => ({
                    ...current,
                    provider_id: event.target.value,
                  }))
                }
              >
                {providers.length === 0 ? (
                  <option value="">请先添加模型服务商</option>
                ) : (
                  providers.map((provider) => (
                    <option key={provider.provider_id} value={provider.provider_id}>
                      {provider.display_name}
                    </option>
                  ))
                )}
              </select>
            </label>
            <label>
              <span>上游模型名</span>
              <input
                type="text"
                value={newModel.upstream_model}
                placeholder="供应商实际 model 名称"
                onChange={(event) =>
                  setNewModel((current) => ({
                    ...current,
                    upstream_model: event.target.value,
                  }))
                }
              />
            </label>
            <label>
              <span>优先级</span>
              <select
                value={newModel.priority}
                onChange={(event) =>
                  setNewModel((current) => ({
                    ...current,
                    priority: event.target.value as ModelSummary["priority"],
                  }))
                }
              >
                <option value="high">{PRIORITY_LABELS.high}</option>
                <option value="medium">{PRIORITY_LABELS.medium}</option>
                <option value="low">{PRIORITY_LABELS.low}</option>
                <option value="disabled">{PRIORITY_LABELS.disabled}</option>
              </select>
            </label>
            <label className="toggle-row">
              <span>启用</span>
              <input
                type="checkbox"
                checked={newModel.enabled}
                onChange={(event) =>
                  setNewModel((current) => ({
                    ...current,
                    enabled: event.target.checked,
                  }))
                }
              />
            </label>
            <label>
              <span>适用预设</span>
              <input
                type="text"
                value={newModelPresetScope}
                placeholder="code-engineering, paper-revision；留空表示全部"
                onChange={(event) => setNewModelPresetScope(event.target.value)}
              />
            </label>
            <label>
              <span>适用任务类型</span>
              <input
                type="text"
                value={newModelTaskScope}
                placeholder="planning, writing, review；留空表示全部"
                onChange={(event) => setNewModelTaskScope(event.target.value)}
              />
            </label>
            <label className="full-width">
              <span>适用角色</span>
              <input
                type="text"
                value={newModelRoleScope}
                placeholder="backend, frontend, reviewer；留空表示全部"
                onChange={(event) => setNewModelRoleScope(event.target.value)}
              />
            </label>
          </div>
          <div className="action-row">
            <button
              type="button"
              className="primary-button"
              onClick={handleCreateModel}
              disabled={providers.length === 0}
            >
              添加模型
            </button>
            <div className="subtle">模型也不再预置，必须由用户绑定到自己添加的 Provider。</div>
          </div>

          <div className="settings-grid">
            {customModels.length === 0 ? (
              <div className="empty-hint">还没有用户模型。先添加 Provider/API，再添加模型。</div>
            ) : (
              customModels.map((model) => (
                <div key={model.model_id} className="settings-card">
                  <div className="stage-head">
                    <strong>{model.display_name}</strong>
                    <span>{model.provider_id}</span>
                  </div>
                  <div className="subtle">{model.upstream_model}</div>
                  <label>
                    <span>优先级</span>
                    <select
                      value={model.priority}
                      onChange={(event) =>
                        setCustomModels((previous) =>
                          previous.map((item) =>
                            item.model_id === model.model_id
                              ? {
                                  ...item,
                                  priority: event.target.value as ModelSummary["priority"],
                                }
                              : item,
                          ),
                        )
                      }
                    >
                      <option value="high">{PRIORITY_LABELS.high}</option>
                      <option value="medium">{PRIORITY_LABELS.medium}</option>
                      <option value="low">{PRIORITY_LABELS.low}</option>
                      <option value="disabled">{PRIORITY_LABELS.disabled}</option>
                    </select>
                  </label>
                  <label className="toggle-row">
                    <span>启用</span>
                    <input
                      type="checkbox"
                      checked={model.enabled}
                      onChange={(event) =>
                        setCustomModels((previous) =>
                          previous.map((item) =>
                            item.model_id === model.model_id
                              ? { ...item, enabled: event.target.checked }
                              : item,
                          ),
                        )
                      }
                    />
                  </label>
                  <div className="action-row provider-actions">
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => handleModelSave(model)}
                    >
                      保存模型设置
                    </button>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => handleDeleteModel(model)}
                    >
                      删除模型
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    );
  }

  function renderRuleTemplates() {
    return (
      <div className="settings-shell template-shell view-enter">
        <div className="panel template-list-panel">
          <div className="panel-title-row">
            <h2>规则模板</h2>
            <button type="button" className="secondary-button" onClick={handleCreateTemplate}>
              新建模板
            </button>
          </div>
          <div className="history-list">
            {ruleTemplates.length === 0 ? (
              <div className="empty-hint">暂无模板。</div>
            ) : (
              ruleTemplates.map((template) => (
                <button
                  key={template.template_id}
                  type="button"
                  className={`history-item ${template.template_id === selectedTemplateId ? "active" : ""}`}
                  onClick={() => handleSelectTemplate(template)}
                >
                  <span>{template.display_name}</span>
                  <small>
                    {template.preset_mode}
                    {template.is_default ? " / 默认" : ""}
                  </small>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="panel template-editor-panel">
          <div className="panel-title-row">
            <h2>模板编辑器</h2>
            <span className="subtle">{editingTemplateId ? "编辑已有模板" : "创建新模板"}</span>
          </div>
          {settingsMessage && <div className="message success">{settingsMessage}</div>}
          {settingsError && <div className="message error">{settingsError}</div>}
          <div className="control-grid">
            <label>
              <span>模板 ID</span>
              <input
                type="text"
                value={templateDraft.template_id}
                onChange={(event) =>
                  updateTemplateDraft((current) => ({
                    ...current,
                    template_id: event.target.value,
                  }))
                }
              />
            </label>
            <label>
              <span>显示名称</span>
              <input
                type="text"
                value={templateDraft.display_name}
                onChange={(event) =>
                  updateTemplateDraft((current) => ({
                    ...current,
                    display_name: event.target.value,
                  }))
                }
              />
            </label>
            <label className="full-width">
              <span>描述</span>
              <input
                type="text"
                value={templateDraft.description}
                onChange={(event) =>
                  updateTemplateDraft((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
              />
            </label>
            <label>
              <span>预设模式</span>
              <select
                value={templateDraft.preset_mode}
                onChange={(event) =>
                  updateTemplateDraft((current) => ({
                    ...current,
                    preset_mode: event.target.value,
                  }))
                }
              >
                {presets.map((preset) => (
                  <option key={preset.preset_mode} value={preset.preset_mode}>
                    {preset.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>协调模型</span>
              <select
                value={templateDraft.default_coordinator_model_id}
                onChange={(event) =>
                  updateTemplateDraft((current) => ({
                    ...current,
                    default_coordinator_model_id: event.target.value,
                  }))
                }
              >
                {userModelOptions.map((model) => (
                  <option key={model.model_id} value={model.model_id}>
                    {model.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>任务类型</span>
              <input
                type="text"
                value={templateDraft.task_types.join(", ")}
                placeholder="planning, review"
                onChange={(event) =>
                  updateTemplateDraft((current) => ({
                    ...current,
                    task_types: event.target.value
                      .split(",")
                      .map((item) => item.trim())
                      .filter(Boolean),
                  }))
                }
              />
            </label>
            <label>
              <span>触发关键词</span>
              <input
                type="text"
                value={templateDraft.trigger_keywords.join(", ")}
                placeholder="论文, 审查, 期刊"
                onChange={(event) =>
                  updateTemplateDraft((current) => ({
                    ...current,
                    trigger_keywords: event.target.value
                      .split(",")
                      .map((item) => item.trim())
                      .filter(Boolean),
                  }))
                }
              />
            </label>
            <label className="toggle-row">
              <span>启用</span>
              <input
                type="checkbox"
                checked={templateDraft.enabled}
                onChange={(event) =>
                  updateTemplateDraft((current) => ({
                    ...current,
                    enabled: event.target.checked,
                  }))
                }
              />
            </label>
            <label className="toggle-row">
              <span>默认模板</span>
              <input
                type="checkbox"
                checked={templateDraft.is_default}
                onChange={(event) =>
                  updateTemplateDraft((current) => ({
                    ...current,
                    is_default: event.target.checked,
                  }))
                }
              />
            </label>
            <label className="full-width">
              <span>备注</span>
              <textarea
                value={templateDraft.notes}
                onChange={(event) =>
                  updateTemplateDraft((current) => ({
                    ...current,
                    notes: event.target.value,
                  }))
                }
              />
            </label>
          </div>

          <div className="panel-title-row inline-spacer">
            <h3>角色分配</h3>
            <button
              type="button"
              className="secondary-button"
              onClick={() =>
                updateTemplateDraft((current) => ({
                  ...current,
                  assignments: [
                    ...current.assignments,
                    {
                      role: "new-role",
                      responsibility: "说明职责",
                      model_id: defaultUserModelId,
                    },
                  ],
                }))
              }
            >
              添加分配
            </button>
          </div>
          {renderAssignmentsEditor(templateDraft.assignments)}

          <div className="action-row">
            <button type="button" className="primary-button" onClick={handleSaveTemplate}>
              保存模板
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={handleDeleteTemplate}
              disabled={!editingTemplateId}
            >
              删除模板
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">M</div>
          <div>
            <div className="brand-title">Mindforge</div>
            <div className="brand-subtitle">Web 工作台</div>
          </div>
        </div>

        <nav className="nav-list">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${item.id === activeNavId ? "active" : ""}`}
              type="button"
              onClick={() => handleNavClick(item.id, item.view)}
            >
              <span>{item.label}</span>
              <small>{item.hint}</small>
            </button>
          ))}
        </nav>

        <section className="sidebar-section">
          <div className="panel-title-row history-toolbar">
            <div className="sidebar-heading">最近对话</div>
            <select
              className="history-filter"
              value={historyFilter}
              onChange={(event) => setHistoryFilter(event.target.value as HistoryFilter)}
            >
              {HISTORY_FILTERS.map((filter) => (
                <option key={filter.value} value={filter.value}>
                  {filter.label}
                </option>
              ))}
            </select>
          </div>
          <div className="history-list">
            {conversationHistoryItems.length === 0 ? (
              <div className="empty-hint">暂无历史对话。</div>
            ) : (
              conversationHistoryItems.map((task) => {
                const deleteKey = task.conversation_id || `task:${task.task_id}`;
                const isActive =
                  task.task_id === activeTaskId || task.conversation_id === conversationId;
                return (
                  <div
                    key={deleteKey}
                    className={`history-row ${isActive ? "active" : ""}`}
                  >
                    <button
                      type="button"
                      className={`history-item ${isActive ? "active" : ""}`}
                      onClick={() => void handleHistorySelect(task.task_id)}
                    >
                      <span>{formatTitle(task.prompt)}</span>
                      <small>
                        {formatStatus(task.status)} / {formatDate(task.updated_at)}
                        {task.conversation_turn_count ? ` / ${task.conversation_turn_count} 轮` : ""}
                      </small>
                    </button>
                    <button
                      type="button"
                      className={`history-delete ${
                        confirmingDeleteKey === deleteKey ? "confirming" : ""
                      }`}
                      aria-label={`删除对话 ${formatTitle(task.prompt)}`}
                      disabled={deletingConversationKey === deleteKey}
                      onClick={() => void handleDeleteHistoryItem(task)}
                    >
                      {deletingConversationKey === deleteKey
                        ? "..."
                        : confirmingDeleteKey === deleteKey
                          ? "确认"
                          : "×"}
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </section>

        <section className="sidebar-section compact">
          <div className="sidebar-heading">待审批</div>
          <div className="provider-list">
            <span className="pill accent">{pendingApprovals.length} 个待审批</span>
            {pendingApprovals.slice(0, 2).map((approval) => (
              <span key={approval.approval_id} className="pill">
                {formatRisk(approval.risk_level)}
              </span>
            ))}
          </div>
        </section>

        <section className="sidebar-section compact">
          <div className="sidebar-heading">后端</div>
          <div className="api-hint">{getApiBaseUrl()}</div>
          <div className="provider-list">
            {providers.map((provider) => (
              <span key={provider.provider_id} className={`pill ${provider.enabled ? "" : "muted"}`}>
                {provider.display_name}
              </span>
            ))}
          </div>
        </section>
      </aside>

      <main className="workspace">
        <header className="workspace-header">
          <div>
            <h1>Mindforge 控制工作台</h1>
            <p>
              参考 OpenHands 的 Web 工作台，集中管理任务历史、审批、模型、模型服务商和规则模板。
            </p>
          </div>
          <div className="status-row">
            <span className="pill accent">本地工作台</span>
            <span className="pill">对话上下文：当前会话</span>
            <span className="pill">{customModels.length} 个模型</span>
            <span className="pill">{providers.length} 个模型服务商</span>
            <span className="pill">{ruleTemplates.length} 个模板</span>
            <span className="pill">{projectSpaces.length} 个项目空间</span>
            <span className="pill">{conversationHistoryItems.length} 个最近对话</span>
          </div>
        </header>

        {view === "workspace" && renderWorkspace()}
        {view === "projects" && renderProjectCenter()}
        {view === "tools" && renderToolCenter()}
        {view === "models" && renderModelControlV2()}
        {view === "rules" && renderRuleTemplates()}
      </main>
    </div>
  );
}
