import { useEffect, useMemo, useState } from "react";
import {
  approveTask,
  createModelControl,
  createProviderControl,
  createRuleTemplate,
  deleteModelControl,
  deleteProviderControl,
  deleteRuleTemplate,
  fetchEditableModels,
  fetchHistoryTasks,
  fetchModels,
  fetchPendingApprovals,
  fetchPresets,
  fetchUserProviders,
  fetchRuleTemplates,
  fetchTaskHistoryDetail,
  getApiBaseUrl,
  rejectTask,
  submitTask,
  testProviderConnection,
  updateModelControl,
  updateProviderControl,
  updateRuleTemplate,
} from "./lib/api";
import type {
  ApprovalRecord,
  ModelCreateRequest,
  ModelSummary,
  ProviderCreateRequest,
  PresetSummary,
  ProviderSummary,
  RuleAssignment,
  RuleTemplateSummary,
  TaskHistoryDetail,
  TaskHistorySummary,
  TaskResult,
} from "./types";

type PanelTab =
  | "output"
  | "stages"
  | "repo"
  | "github"
  | "academic"
  | "approval"
  | "metadata";
type AppView = "workspace" | "models" | "rules";
type HistoryFilter = "all" | "completed" | "pending_approval" | "failed" | "rejected";
type ProviderTestMessage = { status: "success" | "error"; text: string };
type PresetFieldConfig = {
  showRepoPath: boolean;
  showGitHub: boolean;
  showAcademic: boolean;
  showApproval: boolean;
  taskTypes: string[];
};

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

const NAV_ITEMS: Array<{
  id: string;
  label: string;
  hint: string;
  view: AppView;
}> = [
  { id: "new-task", label: "新任务", hint: "创建", view: "workspace" },
  { id: "history", label: "历史", hint: "最近", view: "workspace" },
  { id: "projects", label: "工作台", hint: "空间", view: "workspace" },
  { id: "presets", label: "模板", hint: "规则", view: "rules" },
  { id: "settings", label: "模型", hint: "控制", view: "models" },
];

const TASK_TYPE_OPTIONS = [
  { value: "", label: "自动" },
  { value: "planning", label: "规划" },
  { value: "writing", label: "写作" },
  { value: "review", label: "审查" },
];

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

function createEmptyTemplate(presetMode = "code-engineering"): RuleTemplateSummary {
  return {
    template_id: "new-template",
    display_name: "新规则模板",
    description: "说明这个规则模板适合什么任务。",
    preset_mode: presetMode,
    task_types: [],
    default_coordinator_model_id: "gpt-5.4",
    enabled: true,
    is_default: false,
    trigger_keywords: [],
    assignments: [
      {
        role: "project-manager",
        responsibility: "负责主要规划和任务拆解",
        model_id: "gpt-5.4",
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

function presetFieldConfig(presetMode: string): PresetFieldConfig {
  return PRESET_FIELD_CONFIGS[presetMode] || PRESET_FIELD_CONFIGS.default;
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
  const [view, setView] = useState<AppView>("workspace");
  const [activeNavId, setActiveNavId] = useState("new-task");
  const [activeTab, setActiveTab] = useState<PanelTab>("output");

  const [presets, setPresets] = useState<PresetSummary[]>([]);
  const [providers, setProviders] = useState<ProviderSummary[]>([]);
  const [models, setModels] = useState<ModelSummary[]>([]);
  const [customModels, setCustomModels] = useState<ModelSummary[]>([]);
  const [ruleTemplates, setRuleTemplates] = useState<RuleTemplateSummary[]>([]);
  const [historyItems, setHistoryItems] = useState<TaskHistorySummary[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<ApprovalRecord[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [activeTaskDetail, setActiveTaskDetail] = useState<TaskHistoryDetail | null>(null);

  const [prompt, setPrompt] = useState("");
  const [presetMode, setPresetMode] = useState("code-engineering");
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
  const [requiresApproval, setRequiresApproval] = useState(false);
  const [approvalActions, setApprovalActions] = useState("写入文件");
  const [historyFilter, setHistoryFilter] = useState<HistoryFilter>("all");

  const [isSubmitting, setIsSubmitting] = useState(false);
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

  async function refreshHistory(nextActiveTaskId?: string | null) {
    const statusQuery = historyFilter === "all" ? undefined : historyFilter;
    const [history, approvals] = await Promise.all([
      fetchHistoryTasks(statusQuery),
      fetchPendingApprovals(),
    ]);
    setHistoryItems(history);
    setPendingApprovals(approvals);
    const targetTaskId =
      nextActiveTaskId ||
      activeTaskId ||
      history[0]?.task_id ||
      null;
    if (targetTaskId) {
      const detail = await fetchTaskHistoryDetail(targetTaskId);
      setActiveTaskId(targetTaskId);
      setActiveTaskDetail(detail);
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
    const [presetData, providerData, runtimeModelData, customModelData, templateData] = await Promise.all([
      fetchPresets(),
      providerDataPromise,
      fetchModels(),
      fetchEditableModels(),
      fetchRuleTemplates(),
    ]);
    setPresets(presetData);
    setProviders(providerData);
    setModels(runtimeModelData);
    setCustomModels(customModelData);
    setRuleTemplates(templateData);
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

  function handleNavClick(navId: string, targetView: AppView) {
    setActiveNavId(navId);
    setView(targetView);
    setSettingsMessage(null);
    setSettingsError(null);
  }

  async function handleHistorySelect(taskId: string) {
    const detail = await fetchTaskHistoryDetail(taskId);
    setActiveTaskId(taskId);
    setActiveTaskDetail(detail);
    setActiveTab("output");
    setView("workspace");
    setActiveNavId("history");
  }

  async function handleSubmit() {
    if (!prompt.trim()) {
      setSubmitError("请输入任务描述。");
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
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
      const result = await submitTask({
        prompt,
        preset_mode: presetMode,
        repo_path: fieldConfig.showRepoPath ? repoPath || undefined : undefined,
        task_type: taskType || undefined,
        model_override: modelOverride || undefined,
        rule_template_id: ruleTemplateId || undefined,
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
        metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
      });
      const taskId = result.data.metadata.task_id;
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
              {models.map((model) => (
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

    return (
      <div className="workspace-body">
        <section className="chat-column">
          <div className="panel panel-intro">
            <div className="panel-title-row">
              <h2>任务工作台</h2>
              <span className="subtle">新请求</span>
            </div>
            <div className="control-grid">
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
                  <option value="">自动选择</option>
                  {models
                    .filter((item) => item.enabled && item.priority !== "disabled")
                    .map((model) => (
                      <option key={model.model_id} value={model.model_id}>
                        {model.display_name} / {model.provider_id}
                      </option>
                    ))}
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

            <label className="prompt-field">
              <span>任务描述</span>
              <textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="描述你希望 Mindforge 完成的任务。"
              />
            </label>
            <div className="action-row">
              <button type="button" className="primary-button" onClick={handleSubmit} disabled={isSubmitting}>
                {isSubmitting ? "提交中..." : "提交任务"}
              </button>
              <div className="subtle">
                接口：/api/tasks, /api/history/tasks, /api/approvals/pending
              </div>
            </div>
            {loadError && <div className="message error">{loadError}</div>}
            {submitError && <div className="message error">{submitError}</div>}
          </div>

          <div className="panel conversation-preview">
            <div className="panel-title-row">
              <h2>对话预览</h2>
              <span className="subtle">
                {activeTaskDetail ? formatTitle(activeTaskDetail.prompt) : "未选择任务"}
              </span>
            </div>
            <div className="message-list">
              {activeTaskDetail ? (
                <>
                  <div className="bubble user">
                    <div className="bubble-role">用户</div>
                    <div>{activeTaskDetail.prompt}</div>
                  </div>
                  <div className="bubble assistant">
                    <div className="bubble-role">Mindforge</div>
                    <div>
                      {activeTaskDetail.output ||
                        activeTaskDetail.error_message ||
                        activeTaskDetail.message}
                    </div>
                  </div>
                </>
              ) : (
                <div className="empty-hint">
                  从历史记录中选择任务，或提交一个新任务。
                </div>
              )}
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
            <div className="tabs-row">
              {(["output", "stages", "repo", "github", "academic", "approval", "metadata"] as PanelTab[]).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  className={`tab-button ${activeTab === tab ? "active" : ""}`}
                  onClick={() => setActiveTab(tab)}
                >
                  {TAB_LABELS[tab]}
                </button>
              ))}
            </div>

            {activeTab === "output" && (
              <div className="panel-content">
                <h3>最终输出</h3>
                <pre>{activeResult?.data.output || "暂无输出。"}</pre>
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
          </div>
        </aside>
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
                      <span className={`pill ${provider.enabled ? "accent" : "muted"}`}>
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
      <div className="settings-shell">
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
                      <span className={`pill ${provider.enabled ? "accent" : "muted"}`}>
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
      <div className="settings-shell template-shell">
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
                {models.map((model) => (
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
                      model_id: models[0]?.model_id || "gpt-5.4",
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
            <div className="sidebar-heading">最近任务</div>
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
            {historyItems.length === 0 ? (
              <div className="empty-hint">暂无历史任务。</div>
            ) : (
              historyItems.map((task) => (
                <button
                  key={task.task_id}
                  type="button"
                  className={`history-item ${task.task_id === activeTaskId ? "active" : ""}`}
                  onClick={() => void handleHistorySelect(task.task_id)}
                >
                  <span>{formatTitle(task.prompt)}</span>
                  <small>
                    {formatStatus(task.status)} / {formatDate(task.updated_at)}
                  </small>
                </button>
              ))
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
            <span className="pill accent">Phase 11</span>
            <span className="pill">论文修改已就绪</span>
            <span className="pill">{models.length} 个模型</span>
            <span className="pill">{providers.length} 个模型服务商</span>
            <span className="pill">{ruleTemplates.length} 个模板</span>
            <span className="pill">{historyItems.length} 个最近任务</span>
          </div>
        </header>

        {view === "workspace" && renderWorkspace()}
        {view === "models" && renderModelControlV2()}
        {view === "rules" && renderRuleTemplates()}
      </main>
    </div>
  );
}
