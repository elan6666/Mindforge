import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
} from "react";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";
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
  exportLoopMarkdown,
  fetchConversationHistory,
  fetchEditableModels,
  fetchHistoryTasks,
  fetchLoops,
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
  importLoopMarkdown,
  improveLoop,
  rejectTask,
  retryLoopStage,
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
  LoopDefinition,
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

gsap.registerPlugin(useGSAP);

type PanelTab =
  | "output"
  | "stages"
  | "repo"
  | "github"
  | "academic"
  | "approval"
  | "canvas"
  | "metadata";
type AppView =
  | "workspace"
  | "forge"
  | "war-room"
  | "loops"
  | "arena"
  | "timeline"
  | "artifacts"
  | "memory"
  | "approvals"
  | "models"
  | "rules"
  | "tools"
  | "projects"
  | "capabilities";
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
type VisualStyle = "default" | "orbital-command";
type LoopRunStage = {
  order?: number;
  stage_id?: string;
  stage_name?: string;
  role?: string;
  role_name?: string;
  status?: string;
  summary?: string;
  output?: string;
  model?: string;
  provider?: string;
  duration_ms?: number;
  attempt?: number;
  retry_count?: number;
  evidence_required?: string[];
  expected_output?: string;
};
type LoopRuntimeTimelineItem = {
  order?: number;
  stage_id?: string;
  stage_name?: string;
  role?: string;
  model?: string;
  status?: string;
  duration_ms?: number;
  attempt?: number;
  retry_count?: number;
};
type LoopModelPerformance = {
  model_id?: string;
  provider?: string;
  roles?: string[];
  stages?: string[];
  completed_count?: number;
  failed_count?: number;
  total_duration_ms?: number;
  total_tokens?: number;
  average_confidence?: number | null;
};
type LoopEvidenceLedgerItem = {
  stage_id?: string;
  stage_name?: string;
  role?: string;
  model?: string;
  status?: string;
  evidence_score?: number;
  requirements?: Array<{ requirement?: string; status?: string }>;
  checks?: Array<{ field?: string; label?: string; status?: string }>;
  sources?: Array<{ kind?: string; value?: string }>;
  dates?: string[];
  confidence?: number | null;
  missing_fields?: string[];
  counter_evidence_present?: boolean;
  expected_output?: string;
  summary?: string;
};
type LoopImproveSuggestion = {
  kind?: string;
  priority?: string;
  title?: string;
  detail?: string;
  stage_id?: string;
};
type LoopRunMetadata = {
  loop_id?: string;
  loop_name?: string;
  version?: string;
  forge_id?: string;
  status?: string;
  roles?: Array<Record<string, unknown>>;
  stages?: LoopRunStage[];
  timeline?: LoopRuntimeTimelineItem[];
  model_performance?: LoopModelPerformance[];
  evidence_ledger?: LoopEvidenceLedgerItem[];
  improve_suggestions?: LoopImproveSuggestion[];
  evidence_rules?: string[];
  artifact_outputs?: Array<Record<string, unknown>>;
  improvement_count?: number;
  runtime_version?: string;
  total_duration_ms?: number;
};
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

const VISUAL_STYLE_STORAGE_KEY = "mindforge.visualStyle";

const VISUAL_STYLES: Array<{
  id: VisualStyle;
  name: string;
  label: string;
  description: string;
}> = [
  {
    id: "default",
    name: "Default",
    label: "默认",
    description: "当前 Apple-inspired 控制工作台",
  },
  {
    id: "orbital-command",
    name: "Orbital Command",
    label: "轨道指挥舱",
    description: "深色太空系作战界面",
  },
];

function readInitialVisualStyle(): VisualStyle {
  if (typeof window === "undefined") return "default";
  try {
    const storedStyle = window.localStorage.getItem(VISUAL_STYLE_STORAGE_KEY);
    return VISUAL_STYLES.some((style) => style.id === storedStyle)
      ? (storedStyle as VisualStyle)
      : "default";
  } catch {
    return "default";
  }
}

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

const FORGE_WORKFLOWS: ForgeWorkflow[] = [
  {
    id: "code-forge",
    title: "Code Forge",
    label: "代码工程",
    tagline: "像指挥一个工程小队一样处理仓库任务。",
    description:
      "面向 bug 修复、功能实现、代码审查、测试生成和 PR 辅助，强调多角色拆解、执行证据和审查闭环。",
    tasks: ["修复 Bug", "实现功能", "代码审查", "解释代码库", "生成测试", "PR 总结", "安全检查"],
    agents: [
      { role: "Project Manager", responsibility: "拆任务、定边界、确认验收标准" },
      { role: "Backend Agent", responsibility: "分析 API、数据模型、后端风险" },
      { role: "Frontend Agent", responsibility: "分析 UI、状态、交互和浏览器验证" },
      { role: "Reviewer", responsibility: "检查遗漏、测试证据和回归风险" },
    ],
    stages: ["读取仓库", "任务拆解", "实现/建议", "运行验证", "审查交付"],
    context: ["仓库路径", "GitHub Issue/PR", "测试命令", "AGENTS/README 规则"],
    outputs: ["代码审查报告", "实现计划", "测试证据", "PR 总结"],
    plugins: ["GitHub", "Browser", "Codex Security"],
  },
  {
    id: "doc-forge",
    title: "Doc Forge",
    label: "文档与论文",
    tagline: "把写作变成审稿、修订、导出的专业流程。",
    description:
      "覆盖论文润色、审稿人式反馈、技术文档、Markdown/Word/PDF/LaTeX 交付，不只是生成文字。",
    tasks: ["论文润色", "审稿人反馈", "技术文档整理", "Markdown 转 Word/PDF", "LaTeX 草稿整理", "项目报告生成"],
    agents: [
      { role: "Standards Editor", responsibility: "提取期刊、格式或文档规范" },
      { role: "Reviser", responsibility: "改写正文并保持术语一致" },
      { role: "Style Reviewer", responsibility: "检查语言风格和表达质量" },
      { role: "Content Reviewer", responsibility: "检查论证、证据和结构" },
      { role: "Final Reviewer", responsibility: "汇总投稿/发布风险" },
    ],
    stages: ["读取材料", "提取规范", "修订正文", "多轮审查", "导出产物"],
    context: ["目标期刊", "参考文献", "审稿意见", "写作风格"],
    outputs: ["论文修改稿", "审稿意见表", "DOCX/PDF/TEX", "技术报告"],
    plugins: ["Documents", "Presentations", "Canva"],
  },
  {
    id: "research-forge",
    title: "Research Forge",
    label: "深度研究",
    tagline: "生成可追溯证据的研究档案，而不是一篇漂亮空泛的报告。",
    description:
      "面向技术/行业调研、竞品分析、文献综述、投研和政策追踪，突出来源、争议点、可信度和不确定性。",
    tasks: ["技术调研", "竞品分析", "文献综述", "市场分析", "政策追踪", "新闻核验"],
    agents: [
      { role: "Research Lead", responsibility: "定义问题和研究边界" },
      { role: "Source Scout", responsibility: "搜索并筛选资料来源" },
      { role: "Evidence Analyst", responsibility: "提取证据、争议和可信度" },
      { role: "Synthesis Reviewer", responsibility: "交叉验证并形成结论" },
    ],
    stages: ["明确问题", "搜索资料", "提取证据", "交叉验证", "生成报告"],
    context: ["研究问题", "来源清单", "引用格式", "未验证信息"],
    outputs: ["研究报告", "证据表", "竞品矩阵", "不确定性清单"],
    plugins: ["Browser", "Data Analytics", "Documents"],
  },
  {
    id: "site-forge",
    title: "Site Forge",
    label: "网页与前端",
    tagline: "从设计方向到 React 实现，再到浏览器截图验收。",
    description:
      "面向 landing page、dashboard、产品原型、截图复刻和 Figma 到代码，把网页生成升级成真实前端工程闭环。",
    tasks: ["生成 Landing Page", "改造已有页面", "生成 Dashboard", "产品原型", "参考截图实现 UI", "浏览器测试"],
    agents: [
      { role: "Product Designer", responsibility: "定义视觉方向和首屏层级" },
      { role: "Frontend Agent", responsibility: "实现 React/CSS 和响应式状态" },
      { role: "Browser QA", responsibility: "截图、交互和移动端验证" },
      { role: "Reviewer", responsibility: "检查可用性、性能和交付风险" },
    ],
    stages: ["设计方向", "实现页面", "浏览器验证", "截图对比", "保存产物"],
    context: ["参考截图", "Figma 链接", "品牌约束", "目标设备"],
    outputs: ["前端页面", "截图证据", "设计说明", "可部署包"],
    plugins: ["Figma", "Browser", "Vercel"],
  },
  {
    id: "data-forge",
    title: "Data Forge",
    label: "表格与数据",
    tagline: "把表格变成可解释的业务或研究结论。",
    description:
      "面向 CSV/Excel、数据清洗、指标分析、图表建议、异常值和洞察报告，强调解释和导出。",
    tasks: ["上传数据", "字段识别", "指标分析", "生成图表", "异常值检查", "导出报告"],
    agents: [
      { role: "Data Analyst", responsibility: "识别字段、口径和指标" },
      { role: "Chart Designer", responsibility: "选择图表和展示方式" },
      { role: "Insight Reviewer", responsibility: "解释异常、趋势和结论可信度" },
      { role: "Report Builder", responsibility: "生成可交付报告和表格" },
    ],
    stages: ["读取数据", "清洗字段", "分析指标", "生成图表", "导出报告"],
    context: ["CSV/Excel", "指标口径", "时间范围", "分组维度"],
    outputs: ["数据报告", "图表", "清洗表格", "洞察摘要"],
    plugins: ["Data Analytics", "Spreadsheets", "Presentations"],
  },
];

const FORGE_BY_ID = Object.fromEntries(
  FORGE_WORKFLOWS.map((workflow) => [workflow.id, workflow]),
) as Record<string, ForgeWorkflow>;

const WORKFLOW_PACKS: WorkflowPack[] = [
  {
    id: "code-review-pack",
    title: "Code Review Pack",
    forgeId: "code-forge",
    summary: "把仓库任务变成可审计的工程审查：读代码、跑测试、检查安全风险并生成 PR 级报告。",
    plugins: ["GitHub", "Codex Security", "Build Web Apps", "Browser"],
    skills: [
      "byte-code-rules",
      "build-web-apps:frontend-testing-debugging",
      "codex-security:security-diff-scan",
      "github:github",
    ],
    inputs: ["repo path", "GitHub issue/PR", "test command", "acceptance criteria"],
    outputs: ["code review report", "test evidence", "risk list", "Artifact Library entry"],
    risk: "medium",
    artifactType: "代码审查报告",
    nextPrompt:
      "请按 Code Review Pack 执行：读取仓库上下文，识别变更风险，运行相关测试，检查安全问题，并输出可进入 Artifact Library 的代码审查报告。",
    status: "ready",
  },
  {
    id: "site-shipping-pack",
    title: "Site Shipping Pack",
    forgeId: "site-forge",
    summary: "从产品设计到前端实现、浏览器截图和部署建议的网页交付链路。",
    plugins: ["Product Design", "Figma", "Build Web Apps", "Browser", "Vercel"],
    skills: [
      "product-design:index",
      "frontend-design",
      "gsap-react",
      "build-web-apps:frontend-app-builder",
      "build-web-apps:frontend-testing-debugging",
    ],
    inputs: ["design brief", "reference screenshot", "target viewport", "brand constraints"],
    outputs: ["React UI", "browser screenshots", "design rationale", "deployment checklist"],
    risk: "medium",
    artifactType: "网页原型与截图证据",
    nextPrompt:
      "请按 Site Shipping Pack 执行：先给出前端设计方向，再实现页面，使用浏览器做桌面和移动端验证，最后沉淀截图证据和交付说明。",
    status: "ready",
  },
  {
    id: "paper-delivery-pack",
    title: "Paper Delivery Pack",
    forgeId: "doc-forge",
    summary: "把论文/报告材料转成审稿式修订、格式检查和可导出的文档产物。",
    plugins: ["Documents", "LaTeX", "Presentations", "Canva"],
    skills: [
      "nature-reviewer",
      "nature-polishing",
      "nature-citation",
      "latex:latex-compile",
      "presentations:Presentations",
    ],
    inputs: ["draft document", "target journal/style", "references", "review comments"],
    outputs: ["revised draft", "review memo", "DOCX/PDF/TEX", "slide handoff"],
    risk: "low",
    artifactType: "论文修订稿",
    nextPrompt:
      "请按 Paper Delivery Pack 执行：提取写作/期刊要求，给出审稿人式反馈，修订正文，并准备 Markdown、DOCX、PDF 或 LaTeX 导出路径。",
    status: "ready",
  },
  {
    id: "data-insight-pack",
    title: "Data Insight Pack",
    forgeId: "data-forge",
    summary: "把表格、CSV 或任务历史变成指标解释、图表和可阅读的数据报告。",
    plugins: ["Data Analytics", "Spreadsheets", "Presentations"],
    skills: [
      "data-analytics:build-report",
      "data-analytics:visualize-data",
      "spreadsheets:Spreadsheets",
      "data-analytics:design-kpis",
    ],
    inputs: ["CSV/Excel", "metric definitions", "time range", "grouping dimensions"],
    outputs: ["analysis report", "charts", "cleaned table", "dashboard package"],
    risk: "low",
    artifactType: "数据洞察报告",
    nextPrompt:
      "请按 Data Insight Pack 执行：识别字段和指标口径，检查异常值，生成图表建议，并输出可导出的数据洞察报告。",
    status: "ready",
  },
  {
    id: "research-dossier-pack",
    title: "Research Dossier Pack",
    forgeId: "research-forge",
    summary: "把联网资料、文献和竞品信息沉淀为可追溯的研究档案。",
    plugins: ["Browser", "Data Analytics", "Documents", "Notion"],
    skills: [
      "byte-research",
      "notion:notion-research-documentation",
      "data-analytics:product-business-analysis",
      "documents:documents",
    ],
    inputs: ["research question", "source constraints", "citation style", "uncertainty policy"],
    outputs: ["research dossier", "evidence table", "competitor matrix", "open questions"],
    risk: "medium",
    artifactType: "研究档案",
    nextPrompt:
      "请按 Research Dossier Pack 执行：明确研究问题，收集多来源证据，标注争议和不确定性，并输出可追溯研究档案。",
    status: "needs-auth",
  },
  {
    id: "demo-growth-pack",
    title: "Demo Growth Pack",
    forgeId: "site-forge",
    summary: "把已完成的产品能力转成演示视频、发布素材和增长页面。",
    plugins: ["HyperFrames by HeyGen", "Canva", "Creative Production", "Browser"],
    skills: [
      "hyperframes:website-to-hyperframes",
      "canva:canva-branded-presentation",
      "creative-production:moodboard-explorer",
      "browser:control-in-app-browser",
    ],
    inputs: ["live URL", "feature script", "brand assets", "target channel"],
    outputs: ["demo storyboard", "video capture plan", "social assets", "landing copy"],
    risk: "medium",
    artifactType: "演示与增长素材",
    nextPrompt:
      "请按 Demo Growth Pack 执行：围绕当前 Mindforge 功能写 60 秒演示脚本，规划网页录屏和社媒素材，并沉淀为可复用发布包。",
    status: "planned",
  },
];

const WORKFLOW_PACKS_BY_FORGE = WORKFLOW_PACKS.reduce<Record<string, WorkflowPack[]>>(
  (groups, pack) => {
    groups[pack.forgeId] = [...(groups[pack.forgeId] || []), pack];
    return groups;
  },
  {},
);

const WORKFLOW_PACK_STATUS_LABELS: Record<WorkflowPack["status"], string> = {
  ready: "可直接编排",
  "needs-auth": "需确认授权",
  planned: "规划中",
};

const WORKFLOW_PACK_RISK_LABELS: Record<WorkflowPack["risk"], string> = {
  low: "低风险",
  medium: "中风险",
  high: "高风险",
};

const WORKFLOW_PACK_LOOP_MAP: Record<string, string> = {
  "code-review-pack": "code-review-loop",
  "research-dossier-pack": "worldcup-prediction-loop",
};

const NAV_GROUPS: NavGroup[] = [
  {
    title: "开始",
    items: [
      { id: "new-task", label: "新任务", hint: "创建", view: "workspace" },
      { id: "projects", label: "项目空间", hint: "Project Memory", view: "projects" },
    ],
  },
  {
    title: "Forge 工作流",
    items: FORGE_WORKFLOWS.map((workflow) => ({
      id: workflow.id,
      label: workflow.title,
      hint: workflow.label,
      view: "forge",
      forgeId: workflow.id,
    })),
  },
  {
    title: "Agent 编排",
    items: [
      { id: "war-room", label: "Agent War Room", hint: "多 Agent 作战室", view: "war-room" },
      { id: "loop-library", label: "Loop Library", hint: "可迁移循环库", view: "loops" },
      { id: "model-arena", label: "Model Arena", hint: "模型擂台", view: "arena" },
      { id: "skills-mcp", label: "Skills / MCP", hint: "能力插件中心", view: "tools" },
    ],
  },
  {
    title: "资产沉淀",
    items: [
      { id: "timeline", label: "历史时间线", hint: "任务轨迹", view: "timeline" },
      { id: "artifacts", label: "Artifact Library", hint: "产物库", view: "artifacts" },
      { id: "project-memory", label: "项目记忆", hint: "长期上下文", view: "memory" },
    ],
  },
  {
    title: "系统控制",
    items: [
      { id: "models", label: "模型控制", hint: "Provider / Key", view: "models" },
      { id: "approvals", label: "审批中心", hint: "风险动作", view: "approvals" },
      { id: "settings", label: "设置", hint: "规则模板", view: "rules" },
    ],
  },
];

const NAV_ITEMS = NAV_GROUPS.flatMap((group) => group.items);

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
  provided: "已提供",
  missing: "缺失",
  not_required: "不要求",
  verified: "已验证",
  partial: "部分通过",
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

function formatUserFacingError(message: string): string {
  const normalized = message.trim();
  if (!normalized) return "操作暂时没有完成，请稍后重试。";
  if (/failed to fetch|networkerror|load failed|fetch/i.test(normalized)) {
    return "正在连接后端服务，请稍后刷新或检查 API 地址。";
  }
  return normalized;
}

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

const CAPABILITY_STATUS_LABELS = {
  ready: "已具备",
  partial: "可用但需打磨",
  next: "下一步",
} as const;

type CapabilityStatus = keyof typeof CAPABILITY_STATUS_LABELS;

type CapabilityCard = {
  title: string;
  status: CapabilityStatus;
  benchmark: string;
  current: string;
  next: string;
  signals: string[];
  routeLabel: string;
  routeView: AppView;
  routeNavId: string;
};

type WorkflowPack = {
  id: string;
  title: string;
  forgeId: string;
  summary: string;
  plugins: string[];
  skills: string[];
  inputs: string[];
  outputs: string[];
  risk: "low" | "medium" | "high";
  artifactType: string;
  nextPrompt: string;
  status: "ready" | "needs-auth" | "planned";
};

type ForgeWorkflow = {
  id: string;
  title: string;
  label: string;
  tagline: string;
  description: string;
  tasks: string[];
  agents: Array<{ role: string; responsibility: string }>;
  stages: string[];
  context: string[];
  outputs: string[];
  plugins: string[];
};

type NavItem = {
  id: string;
  label: string;
  hint: string;
  view: AppView;
  forgeId?: string;
};

type NavGroup = {
  title: string;
  items: NavItem[];
};

function formatStatus(value?: string | null): string {
  if (!value) return "-";
  return STATUS_LABELS[value] || value;
}

function formatDurationMs(value?: number | null): string {
  if (!value || value < 0) return "-";
  if (value < 1000) return `${value} ms`;
  return `${(value / 1000).toFixed(value < 10_000 ? 1 : 0)} s`;
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
  const shellRef = useRef<HTMLDivElement | null>(null);
  const composerRef = useRef<HTMLDivElement | null>(null);
  const [view, setView] = useState<AppView>("workspace");
  const [visualStyle, setVisualStyle] = useState<VisualStyle>(() =>
    readInitialVisualStyle(),
  );
  const [activeNavId, setActiveNavId] = useState("new-task");
  const [selectedForgeId, setSelectedForgeId] = useState(FORGE_WORKFLOWS[0].id);
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
  const [loops, setLoops] = useState<LoopDefinition[]>([]);
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
  const [selectedLoopId, setSelectedLoopId] = useState("");
  const [loopImportText, setLoopImportText] = useState("");
  const [loopNaturalLanguageDraft, setLoopNaturalLanguageDraft] = useState("");
  const [loopMessage, setLoopMessage] = useState<string | null>(null);
  const [isLoopBusy, setIsLoopBusy] = useState(false);
  const [loopStageRetrying, setLoopStageRetrying] = useState<string | null>(null);
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

  useEffect(() => {
    try {
      window.localStorage.setItem(VISUAL_STYLE_STORAGE_KEY, visualStyle);
    } catch {
      // Ignore unavailable storage; the style still works for this session.
    }
  }, [visualStyle]);

  useGSAP(
    () => {
      const root = shellRef.current;
      if (!root || typeof window === "undefined" || typeof window.matchMedia !== "function") {
        return;
      }

      const select = gsap.utils.selector(root);
      const mm = gsap.matchMedia();
      mm.add(
        {
          isDesktop: "(min-width: 901px)",
          reduceMotion: "(prefers-reduced-motion: reduce)",
        },
        (context) => {
          const { isDesktop, reduceMotion } = context.conditions || {};
          if (reduceMotion) {
            gsap.set(select(".ambient-drift, .orbital-ring"), { clearProps: "all" });
            return;
          }

          const intro = gsap.timeline({
            defaults: { duration: 0.58, ease: "power3.out" },
          });
          const fromIfPresent = (
            selector: string,
            vars: gsap.TweenVars,
            position?: gsap.Position,
          ) => {
            const targets = select(selector);
            if (targets.length > 0) {
              intro.from(targets, vars, position);
            }
          };

          fromIfPresent(".brand, .nav-group, .style-switcher-section", {
            autoAlpha: 0,
            x: isDesktop ? -18 : 0,
            y: isDesktop ? 0 : -8,
            stagger: 0.045,
          });
          fromIfPresent(
            ".workspace-header .motion-reveal",
            {
              autoAlpha: 0,
              y: 18,
              stagger: 0.075,
            },
            "-=0.34",
          );
          fromIfPresent(
            ".view-enter, .panel-column .panel",
            {
              autoAlpha: 0,
              y: 22,
              stagger: { each: 0.045, from: "start" },
            },
            "-=0.24",
          );
          fromIfPresent(
            ".chat-composer",
            {
              autoAlpha: 0,
              y: 20,
              scale: 0.985,
            },
            "-=0.28",
          );

          const ambientTargets = select(".ambient-drift");
          if (ambientTargets.length > 0) {
            gsap.to(ambientTargets, {
              x: visualStyle === "orbital-command" ? 28 : 12,
              y: visualStyle === "orbital-command" ? -18 : -10,
              scale: visualStyle === "orbital-command" ? 1.035 : 1.018,
              duration: visualStyle === "orbital-command" ? 7.5 : 10,
              ease: "sine.inOut",
              repeat: -1,
              yoyo: true,
            });
          }

          const ringTargets = select(".orbital-ring");
          if (ringTargets.length > 0) {
            gsap.to(ringTargets, {
              rotation: (index) => (index % 2 === 0 ? 360 : -360),
              transformOrigin: "50% 50%",
              duration: (index) => 34 + index * 13,
              ease: "none",
              repeat: -1,
            });
          }
        },
      );
      return () => mm.revert();
    },
    { dependencies: [visualStyle, view], revertOnUpdate: true },
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
  const selectedLoop = loops.find((loop) => loop.loop_id === selectedLoopId) || null;
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
      loopData,
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
      fetchLoops().catch(() => [] as LoopDefinition[]),
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
    setLoops(loopData);
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

  useEffect(() => {
    if (window.navigator.userAgent.toLowerCase().includes("jsdom")) return;
    try {
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    } catch {
      // jsdom does not implement scrollTo; real browsers use this to reset view changes.
    }
  }, [view]);

  function handleNavClick(navId: string, targetView: AppView, forgeId?: string) {
    setActiveNavId(navId);
    setView(targetView);
    if (forgeId && FORGE_BY_ID[forgeId]) {
      setSelectedForgeId(forgeId);
    }
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
      setSelectedLoopId("");
      setSelectedProjectId("");
      setCapabilityFlags(DEFAULT_CAPABILITY_FLAGS);
      setSubmitError(null);
      setIsToolMenuOpen(false);
      setIsTaskConfigOpen(false);
      setConfirmingDeleteKey(null);
    }
  }

  function handleWorkflowPackLaunch(pack: WorkflowPack) {
    const forge = FORGE_BY_ID[pack.forgeId] || FORGE_WORKFLOWS[0];
    setSelectedForgeId(forge.id);
    setActiveNavId(forge.id);
    setView("forge");
    setPrompt(pack.nextPrompt);
    setSkillNames(pack.skills.join(", "));
    setMcpServerNames(
      pack.plugins
        .map((plugin) => plugin.toLowerCase().replace(/[^a-z0-9]+/g, "-"))
        .filter(Boolean)
        .join(", "),
    );
    setSelectedLoopId(WORKFLOW_PACK_LOOP_MAP[pack.id] || "");
    setCapabilityFlags({
      ...DEFAULT_CAPABILITY_FLAGS,
      deep_analysis: true,
      web_search: forge.id === "research-forge",
      code_execution: forge.id === "code-forge" || forge.id === "site-forge",
      canvas: forge.id === "site-forge" || forge.id === "doc-forge",
    });
    setIsTaskConfigOpen(true);
    setIsToolMenuOpen(false);
    setSubmitError(null);
    setSettingsMessage(null);
    setSettingsError(null);
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
        loop_id:
          typeof activeTaskDetail?.metadata.loop_id === "string"
            ? activeTaskDetail.metadata.loop_id
            : null,
        loop_name:
          typeof activeTaskDetail?.metadata.loop === "object" &&
          activeTaskDetail.metadata.loop !== null &&
          typeof activeTaskDetail.metadata.loop.name === "string"
            ? activeTaskDetail.metadata.loop.name
            : null,
        provenance:
          typeof activeTaskDetail?.metadata.artifact_provenance === "object" &&
          activeTaskDetail.metadata.artifact_provenance !== null
            ? (activeTaskDetail.metadata.artifact_provenance as Record<string, unknown>)
            : {},
      });
      setArtifacts((current) => [artifact, ...current.filter((item) => item.artifact_id !== artifact.artifact_id)]);
      window.open(`${getApiBaseUrl()}${artifact.download_url.replace(/^\/api/, "")}`, "_blank");
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "导出文档失败。");
    } finally {
      setExportingArtifactFormat(null);
    }
  }

  function buildLoopMarkdownFromNaturalLanguage(description: string): string {
    const name = description.trim().split(/[，。,.!?]/)[0]?.slice(0, 40) || "Custom Loop";
    return [
      `# Loop: ${name}`,
      "",
      `- id: ${createClientId("custom-loop")}`,
      "- version: 1.0.0",
      `- forge: ${selectedForgeId}`,
      "- status: ready",
      "",
      "## Purpose",
      description.trim() || "用自然语言创建的 Mindforge Loop。",
      "",
      "## Inputs",
      "- task goal",
      "- project context",
      "- acceptance criteria",
      "",
      "## Roles",
      "- Coordinator (coordinator): 拆解目标、安排阶段、合并结论。",
      "- Specialist (specialist): 处理关键分析和执行。",
      "- Reviewer (reviewer): 检查证据、遗漏和下一轮改进。",
      "",
      "## Steps",
      "1. 明确目标 [coordinator] - 确认任务、边界和验收标准 -> 任务说明",
      "2. 执行分析 [specialist] - 按输入和工具完成核心处理 -> 阶段输出",
      "3. 审查证据 [reviewer] - 检查事实、风险、验证和反证 -> 审查意见",
      "4. 沉淀产物 [coordinator] - 输出报告、截图或文件，并记录来源 -> 可复用产物",
      "5. 改进 Loop [reviewer] - 根据本次结果更新下一轮检查点 -> Loop 改进建议",
      "",
      "## Tools",
      "- Skills / MCP",
      "- Browser",
      "- Artifact Library",
      "",
      "## Evidence Rules",
      "- 每个关键结论都要留下来源、截图、命令输出或模型阶段记录。",
      "- 未验证内容要标注不确定性，并进入下一轮改进。",
      "",
      "## Artifacts",
      "- Loop 运行报告 (markdown): 记录过程、证据和最终结论",
      "",
      "## Evaluation",
      "- 目标是否完成",
      "- 证据是否可追溯",
      "- 下一轮是否更清晰",
      "",
      "## Memory Policy",
      "保存 loop_id、版本、任务输出、证据和下一轮改进建议。",
      "",
    ].join("\n");
  }

  async function handleImportLoopMarkdown(content: string) {
    if (!content.trim()) {
      setLoopMessage("先粘贴 loop.md，或用自然语言生成一个。");
      return;
    }
    setIsLoopBusy(true);
    setLoopMessage(null);
    try {
      const loop = await importLoopMarkdown(content);
      setLoops((current) => [loop, ...current.filter((item) => item.loop_id !== loop.loop_id)]);
      setSelectedLoopId(loop.loop_id);
      setLoopImportText("");
      setLoopNaturalLanguageDraft("");
      setLoopMessage(`已导入 ${loop.name}，可以直接运行。`);
    } catch (error) {
      setLoopMessage(error instanceof Error ? error.message : "导入 Loop 失败。");
    } finally {
      setIsLoopBusy(false);
    }
  }

  async function handleExportLoop(loopId: string) {
    setIsLoopBusy(true);
    setLoopMessage(null);
    try {
      const exported = await exportLoopMarkdown(loopId);
      const blob = new Blob([exported.content], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = exported.filename;
      link.click();
      URL.revokeObjectURL(url);
      setLoopMessage(`已导出 ${exported.filename}。`);
    } catch (error) {
      setLoopMessage(error instanceof Error ? error.message : "导出 loop.md 失败。");
    } finally {
      setIsLoopBusy(false);
    }
  }

  async function handleImproveSelectedLoop(loopId: string) {
    setIsLoopBusy(true);
    setLoopMessage(null);
    try {
      const loop = await improveLoop(loopId, {
        task_id: activeTaskDetail?.task_id || null,
        note: activeTaskDetail
          ? `基于任务 ${activeTaskDetail.task_id} 的输出继续收紧证据和交付检查点。`
          : "手动触发一次 Loop 改进。",
      });
      setLoops((current) =>
        current.map((item) => (item.loop_id === loop.loop_id ? loop : item)),
      );
      setLoopMessage(`${loop.name} 已升级到 v${loop.version}。`);
    } catch (error) {
      setLoopMessage(error instanceof Error ? error.message : "改进 Loop 失败。");
    } finally {
      setIsLoopBusy(false);
    }
  }

  async function handleRetryLoopStage(stageId: string) {
    if (!activeTaskDetail?.task_id) return;
    setLoopStageRetrying(stageId);
    setLoopMessage(null);
    try {
      const detail = await retryLoopStage(activeTaskDetail.task_id, stageId, {
        note: "从 War Room 手动重跑此 stage，保留前序阶段摘要并刷新 Loop Runtime 指标。",
      });
      setActiveTaskDetail(detail);
      setActiveTaskId(detail.task_id);
      await refreshHistory(detail.task_id);
      setLoopMessage(`已重跑 ${stageId}，Loop Runtime 已刷新。`);
    } catch (error) {
      setLoopMessage(error instanceof Error ? error.message : "重跑 Loop stage 失败。");
    } finally {
      setLoopStageRetrying(null);
    }
  }

  function runLoop(loop: LoopDefinition) {
    setSelectedLoopId(loop.loop_id);
    setSelectedForgeId(FORGE_BY_ID[loop.forge_id] ? loop.forge_id : selectedForgeId);
    setPrompt(
      `按 ${loop.name} 执行这次任务：\n\n目标：\n\n请展示每个 Agent/阶段的处理过程、证据、最终产物和下一轮 Loop 改进建议。`,
    );
    setCapabilityFlags({
      ...DEFAULT_CAPABILITY_FLAGS,
      deep_analysis: true,
      web_search: loop.forge_id === "research-forge",
      code_execution: loop.forge_id === "code-forge" || loop.forge_id === "site-forge",
      canvas: true,
    });
    setSkillNames((current) => current || loop.tools.join(", "));
    setIsTaskConfigOpen(true);
    setView("workspace");
    setActiveNavId("new-task");
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
      if (selectedLoop) {
        metadata.loop_id = selectedLoop.loop_id;
        metadata.loop_name = selectedLoop.name;
        metadata.workflow_source = "loop-library";
      }
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
        loop_id: selectedLoop?.loop_id || undefined,
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

  function renderWorkflowPackCard(pack: WorkflowPack, compact = false) {
    const forge = FORGE_BY_ID[pack.forgeId] || FORGE_WORKFLOWS[0];
    return (
      <article key={pack.id} className={`workflow-pack-card ${compact ? "compact" : ""}`}>
        <div className="workflow-pack-head">
          <div>
            <span className="section-kicker">{forge.title}</span>
            <h3>{pack.title}</h3>
          </div>
          <div className="workflow-pack-badges">
            <span className={`capability-status ${pack.status}`}>
              {WORKFLOW_PACK_STATUS_LABELS[pack.status]}
            </span>
            <span className={`pill risk-${pack.risk}`}>
              {WORKFLOW_PACK_RISK_LABELS[pack.risk]}
            </span>
          </div>
        </div>
        <p>{pack.summary}</p>
        <div className="workflow-pack-section">
          <strong>插件</strong>
          <div className="workflow-plugins">
            {pack.plugins.map((plugin) => (
              <span key={plugin}>{plugin}</span>
            ))}
          </div>
        </div>
        <div className="workflow-pack-section">
          <strong>Skills</strong>
          <div className="capability-tags">
            {pack.skills.map((skill) => (
              <span key={skill} className="pill">
                {skill}
              </span>
            ))}
          </div>
        </div>
        {!compact && (
          <div className="workflow-pack-matrix">
            <div>
              <strong>输入</strong>
              <small>{pack.inputs.join(" / ")}</small>
            </div>
            <div>
              <strong>产物</strong>
              <small>{pack.outputs.join(" / ")}</small>
            </div>
            <div>
              <strong>沉淀类型</strong>
              <small>{pack.artifactType}</small>
            </div>
          </div>
        )}
        <button
          type="button"
          className="secondary-button"
          onClick={() => handleWorkflowPackLaunch(pack)}
        >
          套用这个插件包
        </button>
      </article>
    );
  }

  function renderCapabilityRadar() {
    const enabledProviders = providers.filter((provider) => provider.enabled);
    const enabledModels = models.filter(
      (model) => model.enabled && model.priority !== "disabled",
    );
    const enabledSkills = skills.filter((skill) => skill.enabled);
    const enabledMcpServers = mcpServers.filter((server) => server.enabled);
    const connectedProviders = enabledProviders.filter(
      (provider) => provider.api_key_configured,
    );
    const completedTasks = historyItems.filter((task) => task.status === "completed");
    const failedTasks = historyItems.filter((task) => task.status === "failed");
    const successRate =
      historyItems.length > 0
        ? Math.round((completedTasks.length / historyItems.length) * 100)
        : null;
    const readinessMetrics = [
      {
        label: "可用模型",
        value: `${enabledModels.length}`,
        detail: `${connectedProviders.length}/${enabledProviders.length || 0} 个 Provider 已配置 key`,
      },
      {
        label: "项目空间",
        value: `${projectSpaces.filter((project) => project.enabled).length}`,
        detail: "项目说明、记忆、文件与默认工具上下文",
      },
      {
        label: "Skills",
        value: `${enabledSkills.length}`,
        detail: `${skills.length} 个本地 Skill 可管理`,
      },
      {
        label: "MCP",
        value: `${enabledMcpServers.length}`,
        detail: `${mcpServers.reduce((total, server) => total + (server.tool_count || 0), 0)} 个已知工具`,
      },
      {
        label: "任务记录",
        value: `${historyItems.length}`,
        detail:
          successRate === null
            ? "等待首次真实任务"
            : `${successRate}% 完成率，${failedTasks.length} 个失败`,
      },
      {
        label: "审批",
        value: `${pendingApprovals.length}`,
        detail: "高风险动作的人类确认队列",
      },
    ];

    const capabilityCards: CapabilityCard[] = [
      {
        title: "项目记忆与上下文",
        status: projectSpaces.length > 0 ? "ready" : "partial",
        benchmark: "ChatGPT Projects：项目记忆、文件、应用链接和项目级指令。",
        current:
          projectSpaces.length > 0
            ? `已有 ${projectSpaces.length} 个项目空间，可绑定 repo、GitHub、Skills、MCP 和文件。`
            : "已有项目空间能力，但还没有创建项目上下文。",
        next: "为 Mindforge 自身创建一个项目空间，沉淀路线图、运行记录和评审准则。",
        signals: ["project memory", "files", "instructions", "sources"],
        routeLabel: "去项目空间",
        routeView: "projects",
        routeNavId: "projects",
      },
      {
        title: "多 Agent 编排",
        status: ruleTemplates.length > 0 && enabledModels.length > 0 ? "ready" : "partial",
        benchmark: "Codex：拆分任务、独立执行、运行命令并给出可验证证据。",
        current: `当前有 ${ruleTemplates.length} 个规则模板、${enabledModels.length} 个启用模型和 ${presets.length} 个预设。`,
        next: "补齐 AGENTS.md、测试证据和失败修复循环，让任务从“能跑”升级到“可审计”。",
        signals: ["presets", "role routing", "history", "tests"],
        routeLabel: "去规则模板",
        routeView: "rules",
        routeNavId: "presets",
      },
      {
        title: "工具与连接器",
        status: enabledSkills.length > 0 || enabledMcpServers.length > 0 ? "ready" : "partial",
        benchmark: "ChatGPT/Codex：连接器、MCP、浏览器、GitHub、文件和本地工具协同。",
        current: `已加载 ${enabledSkills.length} 个启用 Skill、${enabledMcpServers.length} 个启用 MCP Server。`,
        next: "把 Browser、GitHub、Figma、Data Analytics、Documents 等插件映射成可复用工作流。",
        signals: ["MCP", "Skills", "Browser", "GitHub"],
        routeLabel: "去工具中心",
        routeView: "tools",
        routeNavId: "tools",
      },
      {
        title: "画布与可交付物",
        status: "partial",
        benchmark: "ChatGPT Canvas：编辑写作/代码、聚焦片段、版本修订和导出。",
        current: "Mindforge 已支持 Canvas artifacts、MD/TEX/DOCX/PDF 导出和任务输出编辑入口。",
        next: "增加版本历史、局部编辑建议和导出质量预检。",
        signals: ["canvas", "exports", "documents", "presentations"],
        routeLabel: "去新任务",
        routeView: "workspace",
        routeNavId: "new-task",
      },
      {
        title: "安全、审批与密钥",
        status: pendingApprovals.length > 0 || providers.some((provider) => provider.api_key_configured)
          ? "ready"
          : "partial",
        benchmark: "Codex：受控环境、审批边界、仓库指导和高风险操作审查。",
        current: `本地管理 ${providers.length} 个 Provider，${pendingApprovals.length} 个待审批动作。`,
        next: "加入 Codex Security 扫描、密钥泄露检查和路由级风险标签。",
        signals: ["approval gates", "provider secrets", "security review"],
        routeLabel: "去模型中心",
        routeView: "models",
        routeNavId: "settings",
      },
      {
        title: "评测与数据闭环",
        status: historyItems.length > 0 ? "partial" : "next",
        benchmark: "Codex/ChatGPT：任务轨迹、测试输出、使用量、失败原因和迭代证据。",
        current:
          historyItems.length > 0
            ? `已有 ${historyItems.length} 条任务历史，可作为 Data Analytics 的输入。`
            : "历史与元数据结构已在，仍需要用量和质量看板。",
        next: "用 Data Analytics + Spreadsheets 建 token 成本、成功率和模型质量报告。",
        signals: ["Data Analytics", "Spreadsheets", "evals", "usage"],
        routeLabel: "看历史任务",
        routeView: "workspace",
        routeNavId: "history",
      },
    ];

    return (
      <div className="capability-shell view-enter">
        <section className="panel capability-overview-panel">
          <div className="panel-title-row">
            <div>
              <h2>能力雷达</h2>
              <p className="subtle">
                把 ChatGPT 的项目/画布/连接器能力和 Codex 的代码任务/评审/证据能力，映射到 Mindforge 当前可执行状态。
              </p>
            </div>
            <span className="pill accent">对标 ChatGPT + Codex</span>
          </div>
          <div className="readiness-grid">
            {readinessMetrics.map((metric) => (
              <div key={metric.label} className="readiness-tile">
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
                <small>{metric.detail}</small>
              </div>
            ))}
          </div>
        </section>

        <section className="capability-grid" aria-label="能力对标列表">
          {capabilityCards.map((capability) => (
            <article key={capability.title} className="capability-card">
              <div className="capability-card-head">
                <h3>{capability.title}</h3>
                <span className={`capability-status ${capability.status}`}>
                  {CAPABILITY_STATUS_LABELS[capability.status]}
                </span>
              </div>
              <dl className="capability-copy">
                <dt>标杆</dt>
                <dd>{capability.benchmark}</dd>
                <dt>当前</dt>
                <dd>{capability.current}</dd>
                <dt>下一步</dt>
                <dd>{capability.next}</dd>
              </dl>
              <div className="capability-tags">
                {capability.signals.map((signal) => (
                  <span key={signal} className="pill">
                    {signal}
                  </span>
                ))}
              </div>
              <button
                type="button"
                className="secondary-button"
                onClick={() => handleNavClick(capability.routeNavId, capability.routeView)}
              >
                {capability.routeLabel}
              </button>
            </article>
          ))}
        </section>

        <section className="panel plugin-workflow-panel">
          <div className="panel-title-row">
            <div>
              <h2>Workflow Pack Registry</h2>
              <p className="subtle">
                把已安装插件和本地 skills 组合成可执行工作流包，先形成统一入口，再逐步接真实外部授权。
              </p>
            </div>
            <span className="pill accent">{WORKFLOW_PACKS.length} 个插件包</span>
          </div>
          <div className="workflow-pack-grid">
            {WORKFLOW_PACKS.map((pack) => renderWorkflowPackCard(pack))}
          </div>
        </section>
      </div>
    );
  }

  function renderForgeWorkspace() {
    const forge = FORGE_BY_ID[selectedForgeId] || FORGE_WORKFLOWS[0];
    const workflowPacks = WORKFLOW_PACKS_BY_FORGE[forge.id] || [];
    const enabledModels = userModelOptions.length;
    const enabledSkills = skills.filter((skill) => skill.enabled).length;
    const enabledMcpServers = mcpServers.filter((server) => server.enabled).length;

    return (
      <div className="forge-shell view-enter">
        <section className="panel forge-hero-panel">
          <div className="forge-hero-copy">
            <span className="section-kicker">Forge 工作流</span>
            <h2>{forge.title}</h2>
            <p>{forge.tagline}</p>
            <small>{forge.description}</small>
          </div>
          <div className="forge-command-card">
            <span>你想完成什么{forge.label}任务？</span>
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder={`例如：${forge.tasks[0]}，并输出可追溯的证据和产物。`}
              aria-label={`${forge.title} 任务输入`}
            />
            <div className="forge-command-actions">
              <button
                type="button"
                className="primary-button"
                onClick={() => {
                  setPresetMode(
                    forge.id === "doc-forge"
                      ? "paper-revision"
                      : forge.id === "code-forge"
                        ? "code-engineering"
                        : "default",
                  );
                  setView("workspace");
                  setActiveNavId("new-task");
                  setActiveTaskId(null);
                  setActiveTaskDetail(null);
                  setActiveTab("output");
                  setSubmitError(null);
                  setIsToolMenuOpen(false);
                  setIsTaskConfigOpen(true);
                }}
              >
                用此工作流发起
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => handleNavClick("war-room", "war-room")}
              >
                查看团队编排
              </button>
            </div>
          </div>
        </section>

        <section className="forge-layout">
          <div className="panel forge-main-panel">
            <div className="panel-title-row">
              <div>
                <h2>常用任务</h2>
                <p className="subtle">这些不是普通分类，而是会带出 Agent、上下文、验证和产物的流程入口。</p>
              </div>
            </div>
            <div className="forge-task-grid">
              {forge.tasks.map((task) => (
                <button
                  key={task}
                  type="button"
                  className="forge-task-card"
                  onClick={() => setPrompt(`${task}：请按 ${forge.title} 流程拆解、执行、审查并沉淀产物。`)}
                >
                  <strong>{task}</strong>
                  <small>{forge.stages.join(" / ")}</small>
                </button>
              ))}
            </div>
          </div>

          <aside className="panel forge-side-panel">
            <h2>本次团队</h2>
            <div className="agent-mini-list">
              {forge.agents.map((agent) => (
                <div key={agent.role} className="agent-mini-card">
                  <strong>{agent.role}</strong>
                  <span>{agent.responsibility}</span>
                </div>
              ))}
            </div>
            <div className="forge-context-block">
              <h3>上下文</h3>
              <div className="capability-tags">
                {forge.context.map((item) => (
                  <span key={item} className="pill">{item}</span>
                ))}
              </div>
            </div>
            <div className="forge-context-block">
              <h3>能力包</h3>
              <div className="capability-tags">
                {forge.plugins.map((plugin) => (
                  <span key={plugin} className="pill accent">{plugin}</span>
                ))}
              </div>
              <small className="subtle">
                当前可用：{enabledModels} 个模型 / {enabledSkills} 个 Skill / {enabledMcpServers} 个 MCP Server
              </small>
            </div>
          </aside>
        </section>

        <section className="panel workflow-pack-panel">
          <div className="panel-title-row">
            <div>
              <h2>推荐插件包</h2>
              <p className="subtle">
                当前 {forge.title} 会优先使用这些已安装插件和 skills，产物会沉淀到 Artifact Library。
              </p>
            </div>
            <span className="pill accent">{workflowPacks.length} 个匹配</span>
          </div>
          <div className="workflow-pack-grid compact-pack-grid">
            {workflowPacks.length === 0 ? (
              <div className="empty-hint">这个 Forge 暂无插件包。可以先在 Skills / MCP 中规划。</div>
            ) : (
              workflowPacks.map((pack) => renderWorkflowPackCard(pack, true))
            )}
          </div>
        </section>

        <section className="workflow-grid">
          {forge.outputs.map((output) => (
            <article key={output} className="workflow-card">
              <h3>{output}</h3>
              <p>会进入 Artifact Library，并关联来源任务、模型、文件、版本和导出格式。</p>
            </article>
          ))}
        </section>
      </div>
    );
  }

  function renderAgentWarRoom() {
    const forge = FORGE_BY_ID[selectedForgeId] || FORGE_WORKFLOWS[0];
    const workflowPacks = WORKFLOW_PACKS_BY_FORGE[forge.id] || [];
    const loopRun =
      typeof activeTaskDetail?.metadata.loop_run === "object" &&
      activeTaskDetail.metadata.loop_run !== null
        ? (activeTaskDetail.metadata.loop_run as LoopRunMetadata)
        : null;
    const loopStages = Array.isArray(loopRun?.stages) ? loopRun.stages : [];
    const loopTimeline =
      Array.isArray(loopRun?.timeline) && loopRun.timeline.length > 0
        ? loopRun.timeline
        : loopStages.map((stage) => ({
            order: stage.order,
            stage_id: stage.stage_id,
            stage_name: stage.stage_name,
            role: stage.role,
            model: stage.model,
            status: stage.status,
            duration_ms: stage.duration_ms,
            attempt: stage.attempt,
            retry_count: stage.retry_count,
          }));
    const modelPerformance = Array.isArray(loopRun?.model_performance)
      ? loopRun.model_performance
      : [];
    const evidenceLedger = Array.isArray(loopRun?.evidence_ledger)
      ? loopRun.evidence_ledger
      : [];
    const improveSuggestions = Array.isArray(loopRun?.improve_suggestions)
      ? loopRun.improve_suggestions
      : [];
    const activeStages = activeTaskDetail?.metadata.orchestration?.stages || [];
    const visibleAgents =
      Array.isArray(loopRun?.roles) && loopRun.roles.length > 0
        ? loopRun.roles.map((role) => ({
            role: String(role.name || role.role_id || "Agent"),
            responsibility: String(role.responsibility || "Loop role"),
          }))
        : activeStages.length > 0
          ? activeStages.map((stage) => ({
              role: stage.role || stage.stage_name,
              responsibility: stage.summary || stage.output || "已记录阶段输出。",
            }))
          : forge.agents;
    const visibleStages: LoopRunStage[] =
      loopStages.length > 0
        ? loopStages
        : forge.stages.map((stage, index) => ({
            order: index + 1,
            stage_id: stage,
            stage_name: stage,
            role: forge.agents[index]?.role || "Coordinator",
            status: "ready",
            summary:
              index < forge.agents.length
                ? forge.agents[index].responsibility
                : "合并证据、产物和下一步。",
            output: "",
          }));
    const timelineItems = loopTimeline.length > 0 ? loopTimeline : visibleStages;

    return (
      <div className="war-room-shell view-enter">
        <section className="panel war-room-hero">
          <div>
            <span className="section-kicker">Loop Runtime</span>
            <h2>Agent War Room</h2>
            <p className="subtle">
              让 Loop 像一个可运行系统：每个 Agent 的模型、耗时、证据和重跑记录都能被追踪。
            </p>
          </div>
          <span className="pill accent">
            {loopRun ? `当前 Loop：${loopRun.loop_name}` : `当前流程：${forge.title}`}
          </span>
        </section>
        {loopMessage && <div className="message info">{loopMessage}</div>}

        <section className="war-room-grid">
          <div className="panel agent-roster-panel">
            <h2>Agent 列表</h2>
            <div className="agent-roster">
              {visibleAgents.map((agent, index) => (
                <button
                  key={`${agent.role}-${index}`}
                  type="button"
                  className="agent-roster-card"
                >
                  <strong>{agent.role}</strong>
                  <span>{agent.responsibility}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="panel war-output-panel">
            <div className="panel-title-row">
              <div>
                <h2>{loopRun ? "Loop Run Timeline" : "当前阶段输出"}</h2>
                <p className="subtle">
                  {loopRun
                    ? `来自任务 ${activeTaskDetail?.task_id || ""} 的可重跑运行轨迹。`
                    : `没有活跃任务时展示 ${forge.title} 的标准流程。`}
                </p>
              </div>
              {loopRun && (
                <span className="pill muted">
                  {loopRun.runtime_version || "loop-runtime"} /{" "}
                  {formatDurationMs(loopRun.total_duration_ms)}
                </span>
              )}
            </div>
            {loopRun && (
              <div className="loop-runtime-summary">
                <div className="readiness-tile">
                  <span>Stages</span>
                  <strong>{loopStages.length}</strong>
                  <small>{formatStatus(loopRun.status)}</small>
                </div>
                <div className="readiness-tile">
                  <span>Models</span>
                  <strong>{modelPerformance.length || "-"}</strong>
                  <small>按 role 记录表现</small>
                </div>
                <div className="readiness-tile">
                  <span>Retries</span>
                  <strong>
                    {loopTimeline.reduce(
                      (total, stage) => total + Number(stage.retry_count || 0),
                      0,
                    )}
                  </strong>
                  <small>可单 stage 重跑</small>
                </div>
              </div>
            )}
            <div className="war-stage-list">
              {timelineItems.map((stage, index) => {
                const stageId = String(stage.stage_id || index);
                const fullStage = loopStages.find((item) => item.stage_id === stage.stage_id);
                return (
                  <div key={stageId} className="war-stage-card loop-runtime-stage-card">
                    <span>{String(stage.order || index + 1).padStart(2, "0")}</span>
                    <div>
                      <strong>
                        {String(
                          stage.stage_name ||
                            (stage as Record<string, unknown>).title ||
                            "Loop stage",
                        )}
                      </strong>
                      <small>
                        {String(
                          fullStage?.summary ||
                            (stage as LoopRunStage).summary ||
                            "等待任务运行后写入阶段结果。",
                        )}
                      </small>
                    </div>
                    <div className="loop-stage-meta">
                      <small>
                        {String(stage.role || "agent")} / {formatStatus(String(stage.status || "ready"))}
                      </small>
                      <small>
                        {String(stage.model || fullStage?.model || "model")} /{" "}
                        {formatDurationMs(Number(stage.duration_ms || fullStage?.duration_ms || 0))}
                      </small>
                      <small>attempt {Number(stage.attempt || fullStage?.attempt || 1)}</small>
                    </div>
                    {loopRun && stage.stage_id && (
                      <button
                        type="button"
                        className="secondary-button compact-action"
                        onClick={() => void handleRetryLoopStage(String(stage.stage_id))}
                        disabled={Boolean(loopStageRetrying)}
                      >
                        {loopStageRetrying === stage.stage_id ? "Retrying" : "Retry"}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <aside className="panel war-evidence-panel">
            <h2>证据 / 工具 / 模型</h2>
            <div className="readiness-grid compact-readiness">
              <div className="readiness-tile">
                <span>模型</span>
                <strong>{userModelOptions.length}</strong>
                <small>可分配给不同 Agent</small>
              </div>
              <div className="readiness-tile">
                <span>Skills</span>
                <strong>{skills.filter((skill) => skill.enabled).length}</strong>
                <small>可注入工作流</small>
              </div>
              <div className="readiness-tile">
                <span>审批</span>
                <strong>{pendingApprovals.length}</strong>
                <small>高风险动作确认</small>
              </div>
            </div>
            <div className="forge-context-block">
              <h3>{loopRun ? "Loop 证据规则" : "插件包"}</h3>
              <div className="capability-tags">
                {loopRun?.evidence_rules?.length ? (
                  loopRun.evidence_rules.map((rule) => (
                    <span key={rule} className="pill accent">
                      {rule}
                    </span>
                  ))
                ) : workflowPacks.length === 0 ? (
                  <span className="pill muted">暂无匹配插件包</span>
                ) : (
                  workflowPacks.map((pack) => (
                    <span key={pack.id} className="pill accent">
                      {pack.title}
                    </span>
                  ))
                )}
              </div>
            </div>
            {modelPerformance.length > 0 && (
              <div className="forge-context-block">
                <h3>Model Performance</h3>
                <div className="loop-runtime-list">
                  {modelPerformance.map((item) => (
                    <article key={item.model_id || item.provider} className="loop-runtime-row">
                      <strong>{item.model_id || "model"}</strong>
                      <small>
                        {item.roles?.join(", ") || "role"} /{" "}
                        {formatDurationMs(item.total_duration_ms || 0)}
                      </small>
                      <small>
                        ok {item.completed_count || 0} / fail {item.failed_count || 0}
                        {item.total_tokens ? ` / ${item.total_tokens} tokens` : ""}
                        {item.average_confidence
                          ? ` / confidence ${item.average_confidence}%`
                          : ""}
                      </small>
                    </article>
                  ))}
                </div>
              </div>
            )}
            {evidenceLedger.length > 0 && (
              <div className="forge-context-block">
                <h3>Evidence Ledger</h3>
                <div className="loop-runtime-list">
                  {evidenceLedger.map((item) => (
                    <article key={item.stage_id || item.stage_name} className="loop-runtime-row">
                      <strong>{item.stage_name || item.stage_id}</strong>
                      <small>
                        {formatStatus(item.status)} / Evidence{" "}
                        {typeof item.evidence_score === "number"
                          ? `${item.evidence_score}%`
                          : "-"}{" "}
                        / {item.model || "model"}
                      </small>
                      <small>
                        sources {item.sources?.length || 0}
                        {item.confidence ? ` / confidence ${item.confidence}%` : ""}
                        {item.dates?.length ? ` / dates ${item.dates.slice(0, 2).join(", ")}` : ""}
                      </small>
                      <small>
                        {item.missing_fields?.length
                          ? `缺失：${item.missing_fields.slice(0, 3).join("、")}`
                          : item.requirements?.map((rule) => rule.requirement).join(" · ") ||
                          item.expected_output ||
                          "证据字段完整"}
                      </small>
                    </article>
                  ))}
                </div>
              </div>
            )}
            {improveSuggestions.length > 0 && (
              <div className="forge-context-block">
                <h3>Improve Suggestions</h3>
                <div className="loop-runtime-list">
                  {improveSuggestions.map((item, index) => (
                    <article key={`${item.title}-${index}`} className="loop-runtime-row">
                      <strong>{item.title || item.kind || "Suggestion"}</strong>
                      <small>
                        {item.priority || "medium"} / {item.kind || "improve"}
                      </small>
                      <small>{item.detail || "收紧下一轮 Loop 定义。"}</small>
                    </article>
                  ))}
                </div>
              </div>
            )}
            {loopRun?.loop_id && (
              <button
                type="button"
                className="secondary-button"
                onClick={() => void handleImproveSelectedLoop(String(loopRun.loop_id))}
                disabled={isLoopBusy}
              >
                Improve Loop
              </button>
            )}
            <button
              type="button"
              className="secondary-button"
              onClick={() => handleNavClick("artifacts", "artifacts")}
            >
              查看产物库
            </button>
          </aside>
        </section>
      </div>
    );
  }

  function renderLoopLibrary() {
    return (
      <div className="asset-shell view-enter">
        <section className="panel loop-library-hero">
          <div>
            <span className="section-kicker">Loop 引擎</span>
            <h2>Loop Library</h2>
            <p className="subtle">
              Prompt 只优化一句话，Loop 优化整套循环：目标、角色、工具、证据、产物、记忆和下一轮改进。
            </p>
          </div>
          <span className="pill accent">{loops.length} 个可运行 Loop</span>
        </section>

        <section className="loop-library-grid">
          <div className="panel loop-list-panel">
            <div className="panel-title-row">
              <div>
                <h2>可迁移循环</h2>
                <p className="subtle">每个 Loop 都可以导出成 loop.md，跟项目一起放到 GitHub 或迁移到另一台设备。</p>
              </div>
            </div>
            <div className="workflow-pack-grid">
              {loops.length === 0 ? (
                <div className="empty-hint">后端还没有返回 Loop。检查 /api/loops 或刷新页面。</div>
              ) : (
                loops.map((loop) => (
                  <article
                    key={loop.loop_id}
                    className={`workflow-pack-card ${selectedLoopId === loop.loop_id ? "active" : ""}`}
                  >
                    <div className="pack-card-head">
                      <span className="pill accent">{FORGE_BY_ID[loop.forge_id]?.title || loop.forge_id}</span>
                      <span className="pill">v{loop.version}</span>
                    </div>
                    <h3>{loop.name}</h3>
                    <p>{loop.description}</p>
                    <div className="capability-tags">
                      <span className="pill">{loop.roles.length} 个 Agent</span>
                      <span className="pill">{loop.steps.length} 个阶段</span>
                      <span className="pill">改进 {loop.improvement_count} 次</span>
                    </div>
                    <div className="pack-detail-list">
                      {loop.steps.slice(0, 4).map((step, index) => (
                        <span key={step.step_id}>
                          {index + 1}. {step.title} / {step.owner_role}
                        </span>
                      ))}
                    </div>
                    <div className="pack-action-row">
                      <button type="button" className="primary-button" onClick={() => runLoop(loop)}>
                        运行 Loop
                      </button>
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => void handleExportLoop(loop.loop_id)}
                        disabled={isLoopBusy}
                      >
                        导出 loop.md
                      </button>
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => void handleImproveSelectedLoop(loop.loop_id)}
                        disabled={isLoopBusy}
                      >
                        Improve
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>
          </div>

          <aside className="panel loop-import-panel">
            <h2>自然语言创建 Loop</h2>
            <p className="subtle">
              描述你想反复执行的流程，Mindforge 会先生成一份 loop.md，再导入成可运行 Loop。
            </p>
            <label>
              <span>一句话流程</span>
              <textarea
                value={loopNaturalLanguageDraft}
                onChange={(event) => setLoopNaturalLanguageDraft(event.target.value)}
                placeholder="例如：用 5 个专家 Agent 做世界杯冠军预测，展示证据、分歧、最终结论和下一轮改进。"
              />
            </label>
            <button
              type="button"
              className="secondary-button"
              onClick={() =>
                setLoopImportText(buildLoopMarkdownFromNaturalLanguage(loopNaturalLanguageDraft))
              }
            >
              生成 loop.md 草稿
            </button>
            <label>
              <span>导入 loop.md</span>
              <textarea
                value={loopImportText}
                onChange={(event) => setLoopImportText(event.target.value)}
                placeholder="# Loop: My Workflow..."
              />
            </label>
            <button
              type="button"
              className="primary-button"
              onClick={() => void handleImportLoopMarkdown(loopImportText)}
              disabled={isLoopBusy}
            >
              导入 Loop
            </button>
            {loopMessage && <div className="message info">{loopMessage}</div>}
          </aside>
        </section>
      </div>
    );
  }

  function renderModelArena() {
    const arenaModels = userModelOptions.slice(0, 5);
    const scoringRows = [
      "准确性",
      "结构清晰度",
      "执行能力",
      "中文表达",
      "代码质量",
      "成本",
      "速度",
      "适合角色",
    ];

    return (
      <div className="arena-shell view-enter">
        <section className="panel arena-hero">
          <div>
            <span className="section-kicker">模型调度</span>
            <h2>Model Arena</h2>
            <p className="subtle">
              多模型同题竞技，帮用户决定哪个模型适合哪个任务、角色和成本边界。
            </p>
          </div>
          <button
            type="button"
            className="primary-button"
            onClick={() => handleNavClick("models", "models")}
          >
            配置模型
          </button>
        </section>

        <section className="panel arena-prompt-panel">
          <label>
            <span>竞技题目</span>
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="输入同一个任务，未来可并行发送给 2-5 个模型并由 Reviewer 评分。"
            />
          </label>
        </section>

        <section className="arena-grid">
          {(arenaModels.length > 0 ? arenaModels : customModels.slice(0, 5)).map((model) => (
            <article key={model.model_id} className="panel arena-model-card">
              <span className="pill accent">{model.provider_id}</span>
              <h3>{model.display_name}</h3>
              <p>{model.upstream_model}</p>
              <div className="capability-tags">
                <span className="pill">{PRIORITY_LABELS[model.priority]}</span>
                <span className="pill">{model.enabled ? "启用" : "未启用"}</span>
              </div>
            </article>
          ))}
        </section>

        <section className="panel arena-score-panel">
          <h2>评分维度</h2>
          <div className="score-grid">
            {scoringRows.map((row) => (
              <span key={row}>{row}</span>
            ))}
          </div>
        </section>
      </div>
    );
  }

  function renderHistoryTimeline() {
    return (
      <div className="asset-shell view-enter">
        <section className="panel">
          <div className="panel-title-row">
            <div>
              <span className="section-kicker">资产沉淀</span>
              <h2>历史时间线</h2>
              <p className="subtle">聊天历史升级为任务轨迹：状态、更新时间、轮次和可继续处理的入口。</p>
            </div>
            <span className="pill accent">{conversationHistoryItems.length} 条记录</span>
          </div>
          <div className="timeline-list">
            {conversationHistoryItems.length === 0 ? (
              <div className="empty-hint">暂无历史任务。</div>
            ) : (
              conversationHistoryItems.map((task) => (
                <button
                  key={task.conversation_id || task.task_id}
                  type="button"
                  className="timeline-card"
                  onClick={() => void handleHistorySelect(task.task_id)}
                >
                  <strong>{formatTitle(task.prompt)}</strong>
                  <span>{formatStatus(task.status)} / {formatDate(task.updated_at)}</span>
                  <small>{task.conversation_turn_count ? `${task.conversation_turn_count} 轮对话` : "单次任务"}</small>
                </button>
              ))
            )}
          </div>
        </section>
      </div>
    );
  }

  function renderArtifactLibrary() {
    const generatedFromActive =
      activeTaskDetail && Array.isArray(activeTaskDetail.metadata.generated_artifacts)
        ? (activeTaskDetail.metadata.generated_artifacts as ArtifactSummary[])
        : [];
    const allArtifacts = [...artifacts, ...generatedFromActive];

    return (
      <div className="asset-shell view-enter">
        <section className="panel">
          <div className="panel-title-row">
            <div>
              <span className="section-kicker">资产沉淀</span>
              <h2>Artifact Library</h2>
              <p className="subtle">
                把代码报告、论文稿、研究报告、网页原型、数据图表和导出文件从聊天里沉淀出来。
              </p>
            </div>
            <span className="pill accent">{allArtifacts.length} 个产物</span>
          </div>
          <div className="artifact-library-grid">
            {allArtifacts.length === 0 ? (
              WORKFLOW_PACKS.slice(0, 6).map((pack) => (
                <article key={pack.id} className="artifact-library-card placeholder">
                  <strong>{pack.artifactType}</strong>
                  <span>{pack.title}</span>
                  <small>
                    {pack.outputs.slice(0, 3).join(" / ")}。未来会显示来源任务、模型、版本、导出格式和继续编辑入口。
                  </small>
                </article>
              ))
            ) : (
              allArtifacts.map((artifact) => (
                <a
                  key={artifact.artifact_id}
                  className="artifact-library-card"
                  href={artifact.download_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <strong>{artifact.title}</strong>
                  <span>{artifact.format.toUpperCase()} / {artifact.filename}</span>
                  {artifact.loop_name && (
                    <small>Loop：{artifact.loop_name}</small>
                  )}
                  <small>{formatDate(artifact.created_at)}</small>
                </a>
              ))
            )}
          </div>
        </section>
      </div>
    );
  }

  function renderProjectMemoryMap() {
    return (
      <div className="asset-shell view-enter">
        <section className="panel">
          <div className="panel-title-row">
            <div>
              <span className="section-kicker">长期上下文</span>
              <h2>Project Memory Map</h2>
              <p className="subtle">让 Mindforge 记住项目目标、仓库、关键文件、历史决策、偏好和重要产物。</p>
            </div>
            <button
              type="button"
              className="secondary-button"
              onClick={() => handleNavClick("projects", "projects")}
            >
              管理项目空间
            </button>
          </div>
          <div className="memory-grid">
            {projectSpaces.length === 0 ? (
              <div className="empty-hint">暂无项目空间。先创建一个项目空间来沉淀长期记忆。</div>
            ) : (
              projectSpaces.map((project) => (
                <article key={project.project_id} className="memory-card">
                  <span className="pill">{project.enabled ? "启用" : "停用"}</span>
                  <h3>{project.display_name}</h3>
                  <p>{project.description || "暂无描述。"}</p>
                  <div className="capability-tags">
                    <span className="pill">{project.file_count} 个文件</span>
                    <span className="pill">{project.skill_ids.length} 个 Skill</span>
                    <span className="pill">{project.mcp_server_ids.length} 个 MCP</span>
                  </div>
                </article>
              ))
            )}
          </div>
        </section>
      </div>
    );
  }

  function renderApprovalCenter() {
    return (
      <div className="asset-shell view-enter">
        <section className="panel">
          <div className="panel-title-row">
            <div>
              <span className="section-kicker">系统控制</span>
              <h2>审批中心</h2>
              <p className="subtle">把高风险动作从黑箱执行变成可确认、可拒绝、可追溯的队列。</p>
            </div>
            <span className="pill accent">{pendingApprovals.length} 个待审批</span>
          </div>
          <div className="approval-center-list">
            {pendingApprovals.length === 0 ? (
              <div className="empty-hint">暂无待审批动作。</div>
            ) : (
              pendingApprovals.map((approval) => (
                <article key={approval.approval_id} className="approval-card">
                  <div className="approval-meta">
                    <span>{formatRisk(approval.risk_level)}</span>
                    <span>{formatDate(approval.created_at)}</span>
                  </div>
                  <strong>{approval.summary}</strong>
                  <div className="capability-tags">
                    {approval.actions.map((action) => (
                      <span key={action} className="pill">{action}</span>
                    ))}
                  </div>
                </article>
              ))
            )}
          </div>
        </section>
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
                    <label className="full-width">
                      <span>Loop</span>
                      <select
                        value={selectedLoopId}
                        onChange={(event) => setSelectedLoopId(event.target.value)}
                      >
                        <option value="">不使用 Loop</option>
                        {loops.map((loop) => (
                          <option key={loop.loop_id} value={loop.loop_id}>
                            {loop.name} / {FORGE_BY_ID[loop.forge_id]?.title || loop.forge_id}
                          </option>
                        ))}
                      </select>
                      <small className="field-hint">
                        Loop 会把角色、阶段、证据规则和产物来源写入 War Room 与 Artifact Library。
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
              {loadError && (
                <div className="message error" role="alert">
                  {formatUserFacingError(loadError)}
                </div>
              )}
              {submitError && (
                <div className="message error" role="alert">
                  {formatUserFacingError(submitError)}
                </div>
              )}

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
                    {selectedLoop && (
                      <span className="composer-chip">Loop：{selectedLoop.name}</span>
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

        <div className="panel settings-panel workflow-pack-registry">
          <div className="panel-title-row">
            <div>
              <span className="section-kicker">Workflow Pack Registry</span>
              <h2>插件与 Skills 工作流包</h2>
              <p className="subtle">
                每个包都把已安装插件、本地 skills、输入、产物和风险边界绑定到一个 Forge 流程。
              </p>
            </div>
            <div className="provider-list inline-pills">
              <span className="pill accent">{WORKFLOW_PACKS.length} 个包</span>
              <span className="pill">{WORKFLOW_PACKS.filter((pack) => pack.status === "ready").length} 个可直接编排</span>
              <span className="pill muted">{WORKFLOW_PACKS.filter((pack) => pack.status !== "ready").length} 个需确认</span>
            </div>
          </div>
          <div className="workflow-pack-grid">
            {WORKFLOW_PACKS.map((pack) => renderWorkflowPackCard(pack))}
          </div>
        </div>

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
    <div
      ref={shellRef}
      className={`shell shell--${visualStyle}`}
      data-visual-style={visualStyle}
    >
      <div className="ambient-stage" aria-hidden="true">
        <div className="ambient-image ambient-drift" />
        <div className="orbital-ring ring-one" />
        <div className="orbital-ring ring-two" />
        <div className="orbital-ring ring-three" />
      </div>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">M</div>
          <div>
            <div className="brand-title">Mindforge</div>
            <div className="brand-subtitle">Web 工作台</div>
          </div>
        </div>

        <nav className="nav-groups" aria-label="Mindforge 工作区导航">
          {NAV_GROUPS.map((group) => (
            <section key={group.title} className="nav-group">
              <div className="nav-group-title">{group.title}</div>
              <div className="nav-list">
                {group.items.map((item) => (
                  <button
                    key={item.id}
                    className={`nav-item ${item.id === activeNavId ? "active" : ""}`}
                    type="button"
                    onClick={() => handleNavClick(item.id, item.view, item.forgeId)}
                  >
                    <span>{item.label}</span>
                    <small>{item.hint}</small>
                  </button>
                ))}
              </div>
            </section>
          ))}
        </nav>

        <section className="sidebar-section style-switcher-section">
          <div className="sidebar-heading">外观</div>
          <div className="style-switcher" aria-label="外观风格切换">
            {VISUAL_STYLES.map((style) => (
              <button
                key={style.id}
                type="button"
                className={`style-option ${visualStyle === style.id ? "active" : ""}`}
                aria-pressed={visualStyle === style.id}
                onClick={() => setVisualStyle(style.id)}
              >
                <span>{style.name}</span>
                <small>{style.label}</small>
              </button>
            ))}
          </div>
          <p className="style-switcher-note">
            {VISUAL_STYLES.find((style) => style.id === visualStyle)?.description}
          </p>
        </section>

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

      <main className={`workspace workspace--${view}`}>
        <header className="workspace-header">
          <div>
            <h1 className="motion-reveal">Mindforge 控制工作台</h1>
              <p className="motion-reveal">
                把 AI 当成一支可配置团队，而不是一个聊天框：从 Forge 工作流到作战室，再到产物库全程可审计。
              </p>
            <div className="hero-actions motion-reveal" aria-label="首屏操作">
              <button
                type="button"
                className="primary-button hero-primary"
                onClick={() => handleNavClick("new-task", "workspace")}
              >
                开始新任务
              </button>
              <button
                type="button"
                className="secondary-button hero-secondary"
                onClick={() => handleNavClick("war-room", "war-room")}
              >
                进入作战室
              </button>
            </div>
          </div>
          <div className="status-row motion-reveal">
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
        {view === "forge" && renderForgeWorkspace()}
        {view === "war-room" && renderAgentWarRoom()}
        {view === "loops" && renderLoopLibrary()}
        {view === "arena" && renderModelArena()}
        {view === "timeline" && renderHistoryTimeline()}
        {view === "artifacts" && renderArtifactLibrary()}
        {view === "memory" && renderProjectMemoryMap()}
        {view === "approvals" && renderApprovalCenter()}
        {view === "projects" && renderProjectCenter()}
        {view === "tools" && renderToolCenter()}
        {view === "capabilities" && renderCapabilityRadar()}
        {view === "models" && renderModelControlV2()}
        {view === "rules" && renderRuleTemplates()}
      </main>
    </div>
  );
}
