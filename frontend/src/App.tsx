import { useEffect, useMemo, useState } from "react";
import {
  approveTask,
  createRuleTemplate,
  deleteRuleTemplate,
  fetchEditableModels,
  fetchHistoryTasks,
  fetchPendingApprovals,
  fetchPresets,
  fetchProviders,
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
  ModelSummary,
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

const NAV_ITEMS: Array<{
  id: string;
  label: string;
  hint: string;
  view: AppView;
}> = [
  { id: "new-task", label: "New Task", hint: "Create", view: "workspace" },
  { id: "history", label: "History", hint: "Recent", view: "workspace" },
  { id: "projects", label: "Workspace", hint: "Shell", view: "workspace" },
  { id: "presets", label: "Templates", hint: "Rules", view: "rules" },
  { id: "settings", label: "Models", hint: "Control", view: "models" },
];

const TASK_TYPE_OPTIONS = [
  { value: "", label: "Auto" },
  { value: "planning", label: "Planning" },
  { value: "writing", label: "Writing" },
  { value: "review", label: "Review" },
];

const HISTORY_FILTERS: Array<{ value: HistoryFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "pending_approval", label: "Pending" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "rejected", label: "Rejected" },
];

function formatTitle(prompt: string): string {
  const trimmed = prompt.trim();
  if (!trimmed) return "Untitled task";
  return trimmed.length > 30 ? `${trimmed.slice(0, 30)}...` : trimmed;
}

function createEmptyTemplate(presetMode = "code-engineering"): RuleTemplateSummary {
  return {
    template_id: "new-template",
    display_name: "New Template",
    description: "Describe what this template is for.",
    preset_mode: presetMode,
    task_types: [],
    default_coordinator_model_id: "gpt-5.4",
    enabled: true,
    is_default: false,
    trigger_keywords: [],
    assignments: [
      {
        role: "project-manager",
        responsibility: "Primary planning responsibility",
        model_id: "gpt-5.4",
      },
    ],
    notes: "",
  };
}

function formatDate(value?: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleString();
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

export function App() {
  const [view, setView] = useState<AppView>("workspace");
  const [activeNavId, setActiveNavId] = useState("new-task");
  const [activeTab, setActiveTab] = useState<PanelTab>("output");

  const [presets, setPresets] = useState<PresetSummary[]>([]);
  const [providers, setProviders] = useState<ProviderSummary[]>([]);
  const [models, setModels] = useState<ModelSummary[]>([]);
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
  const [approvalActions, setApprovalActions] = useState("write files");
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
    const providerDataPromise = fetchProviders().catch((error) => {
      providerLoadError =
        error instanceof Error ? error.message : "Failed to load provider controls.";
      return [] as ProviderSummary[];
    });
    const [presetData, providerData, modelData, templateData] = await Promise.all([
      fetchPresets(),
      providerDataPromise,
      fetchEditableModels(),
      fetchRuleTemplates(),
    ]);
    setPresets(presetData);
    setProviders(providerData);
    setModels(modelData);
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
        setLoadError(error instanceof Error ? error.message : "Failed to load bootstrap data.");
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
        setLoadError(error instanceof Error ? error.message : "Failed to load history.");
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
      setSubmitError("Please enter a task prompt.");
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const metadata: Record<string, unknown> = {};
      if (requiresApproval) {
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
        repo_path: repoPath || undefined,
        task_type: taskType || undefined,
        model_override: modelOverride || undefined,
        rule_template_id: ruleTemplateId || undefined,
        github_repo: githubRepo || undefined,
        github_issue_number: githubIssueNumber ? Number(githubIssueNumber) : undefined,
        github_pr_number: githubPrNumber ? Number(githubPrNumber) : undefined,
        journal_name: journalName || undefined,
        journal_url: journalUrl || undefined,
        reference_paper_urls: parseUrlList(referencePaperUrls),
        metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
      });
      const taskId = result.data.metadata.task_id;
      await refreshHistory(taskId || null);
      setActiveTab(result.status === "pending_approval" ? "approval" : "output");
      setSubmitError(null);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Task submission failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleApprovalDecision(action: "approve" | "reject") {
    if (!activeTaskId) return;
    try {
      if (action === "approve") {
        await approveTask(activeTaskId, "Approved from workspace");
      } else {
        await rejectTask(activeTaskId, "Rejected from workspace");
      }
      await refreshHistory(activeTaskId);
      setActiveTab("approval");
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Approval request failed.");
    }
  }

  async function handleModelSave(model: ModelSummary) {
    try {
      const updated = await updateModelControl(model.model_id, {
        priority: model.priority,
        enabled: model.enabled,
      });
      setModels((previous) =>
        previous.map((item) => (item.model_id === updated.model_id ? updated : item)),
      );
      setSettingsError(null);
      setSettingsMessage(`Saved model ${updated.display_name}.`);
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(error instanceof Error ? error.message : "Model update failed.");
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
      const updated = await updateProviderControl(provider.provider_id, {
        enabled: provider.enabled,
        api_base_url: optionalText(provider.api_base_url),
        protocol: optionalText(provider.protocol),
        api_key_env: optionalText(provider.api_key_env),
        anthropic_api_base_url: optionalText(provider.anthropic_api_base_url),
      });
      setProviders((previous) =>
        previous.map((item) => (item.provider_id === updated.provider_id ? updated : item)),
      );
      setSettingsError(null);
      setSettingsMessage(`Saved provider ${updated.display_name}.`);
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(error instanceof Error ? error.message : "Provider update failed.");
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
      const message = `${result.status}: ${result.detail}`;
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
          text: error instanceof Error ? error.message : "Connection test failed.",
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
      setSettingsMessage(`Saved template ${saved.display_name}.`);
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(error instanceof Error ? error.message : "Template save failed.");
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
      setSettingsMessage("Deleted template.");
    } catch (error) {
      setSettingsMessage(null);
      setSettingsError(error instanceof Error ? error.message : "Template delete failed.");
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
              placeholder="role"
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
              placeholder="responsibility"
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
              Delete
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
              <h2>Task Workspace</h2>
              <span className="subtle">New request</span>
            </div>
            <div className="control-grid">
              <label>
                <span>Preset</span>
                <select value={presetMode} onChange={(event) => setPresetMode(event.target.value)}>
                  {presets.map((preset) => (
                    <option key={preset.preset_mode} value={preset.preset_mode}>
                      {preset.display_name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Task Type</span>
                <select value={taskType} onChange={(event) => setTaskType(event.target.value)}>
                  {TASK_TYPE_OPTIONS.map((option) => (
                    <option key={option.value || "auto"} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Repository Path</span>
                <input
                  type="text"
                  placeholder="E:\\CODE\\project or ."
                  value={repoPath}
                  onChange={(event) => setRepoPath(event.target.value)}
                />
              </label>
              <label>
                <span>Coordinator Model</span>
                <select
                  value={modelOverride}
                  onChange={(event) => setModelOverride(event.target.value)}
                >
                  <option value="">Auto select</option>
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
                <span>Rule Template</span>
                <select
                  value={ruleTemplateId}
                  onChange={(event) => setRuleTemplateId(event.target.value)}
                >
                  <option value="">Auto select</option>
                  {filteredTemplates.map((template) => (
                    <option key={template.template_id} value={template.template_id}>
                      {template.display_name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>GitHub Repo</span>
                <input
                  type="text"
                  placeholder="owner/repo"
                  value={githubRepo}
                  onChange={(event) => setGitHubRepo(event.target.value)}
                />
              </label>
              <label>
                <span>Issue Number</span>
                <input
                  type="number"
                  min="1"
                  placeholder="Optional"
                  value={githubIssueNumber}
                  onChange={(event) => setGitHubIssueNumber(event.target.value)}
                />
              </label>
              <label>
                <span>PR Number</span>
                <input
                  type="number"
                  min="1"
                  placeholder="Optional"
                  value={githubPrNumber}
                  onChange={(event) => setGitHubPrNumber(event.target.value)}
                />
              </label>
              <label>
                <span>Journal Name</span>
                <input
                  type="text"
                  placeholder="Nature, IEEE TSE..."
                  value={journalName}
                  onChange={(event) => setJournalName(event.target.value)}
                />
              </label>
              <label className="full-width">
                <span>Journal Guidelines URL</span>
                <input
                  type="url"
                  placeholder="https://journal.example.com/for-authors"
                  value={journalUrl}
                  onChange={(event) => setJournalUrl(event.target.value)}
                />
              </label>
              <label className="full-width">
                <span>Reference Paper URLs</span>
                <textarea
                  value={referencePaperUrls}
                  onChange={(event) => setReferencePaperUrls(event.target.value)}
                  placeholder="One URL per line, or comma-separated."
                />
              </label>
              <label className="toggle-row full-width">
                <span>Require approval before execution</span>
                <input
                  type="checkbox"
                  checked={requiresApproval}
                  onChange={(event) => setRequiresApproval(event.target.checked)}
                />
              </label>
              {requiresApproval && (
                <label className="full-width">
                  <span>High-risk actions</span>
                  <input
                    type="text"
                    placeholder="write files, execute shell"
                    value={approvalActions}
                    onChange={(event) => setApprovalActions(event.target.value)}
                  />
                </label>
              )}
            </div>

            <label className="prompt-field">
              <span>Prompt</span>
              <textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="Describe the task for Mindforge."
              />
            </label>
            <div className="action-row">
              <button type="button" className="primary-button" onClick={handleSubmit} disabled={isSubmitting}>
                {isSubmitting ? "Submitting..." : "Submit task"}
              </button>
              <div className="subtle">
                APIs: /api/tasks, /api/history/tasks, /api/approvals/pending
              </div>
            </div>
            {loadError && <div className="message error">{loadError}</div>}
            {submitError && <div className="message error">{submitError}</div>}
          </div>

          <div className="panel conversation-preview">
            <div className="panel-title-row">
              <h2>Conversation Preview</h2>
              <span className="subtle">
                {activeTaskDetail ? formatTitle(activeTaskDetail.prompt) : "No task selected"}
              </span>
            </div>
            <div className="message-list">
              {activeTaskDetail ? (
                <>
                  <div className="bubble user">
                    <div className="bubble-role">User</div>
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
                  Select a task from history or submit a new one.
                </div>
              )}
            </div>
          </div>
        </section>

        <aside className="panel-column">
          <div className="panel tabs-panel">
            <div className="panel-title-row">
              <h2>Task Detail</h2>
              <span className="subtle">
                {activeTaskDetail ? activeTaskDetail.status : "Idle"}
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
                  {tab}
                </button>
              ))}
            </div>

            {activeTab === "output" && (
              <div className="panel-content">
                <h3>Final Output</h3>
                <pre>{activeResult?.data.output || "No output yet."}</pre>
              </div>
            )}

            {activeTab === "stages" && (
              <div className="panel-content">
                <h3>Stage Trace</h3>
                {activeTrace?.stages?.length ? (
                  <div className="stage-list">
                    {activeTrace.stages.map((stage) => (
                      <div key={stage.stage_id} className="stage-card">
                        <div className="stage-head">
                          <strong>{stage.stage_name}</strong>
                          <span>{stage.model}</span>
                        </div>
                        <div className="stage-meta">
                          <span>{stage.status}</span>
                          <span>{stage.provider}</span>
                        </div>
                        <p>{stage.summary}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-hint">No stage data for this task.</div>
                )}
              </div>
            )}

            {activeTab === "repo" && (
              <div className="panel-content">
                <h3>Repository Summary</h3>
                {activeRepo?.repo_summary ? (
                  <>
                    <p>{activeRepo.repo_summary.summary_text}</p>
                    <div className="info-block">
                      <strong>Entrypoints</strong>
                      <ul>
                        {activeRepo.repo_summary.entrypoints.map((entry) => (
                          <li key={entry}>{entry}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="info-block">
                      <strong>Detected Stack</strong>
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
                  <div className="empty-hint">No repository summary for this task.</div>
                )}
              </div>
            )}

            {activeTab === "github" && (
              <div className="panel-content">
                <h3>GitHub Context</h3>
                {activeGitHub ? (
                  <div className="stage-list">
                    {activeGitHub.repository && (
                      <div className="stage-card">
                        <div className="stage-head">
                          <strong>{activeGitHub.repository.full_name}</strong>
                          <a href={activeGitHub.repository.html_url} target="_blank" rel="noreferrer">
                            Open
                          </a>
                        </div>
                        <div className="stage-meta">
                          <span>branch: {activeGitHub.repository.default_branch}</span>
                          <span>language: {activeGitHub.repository.primary_language || "unknown"}</span>
                        </div>
                        <p>{activeGitHub.repository.description || "No repository description."}</p>
                      </div>
                    )}
                    {activeGitHub.issue && (
                      <div className="stage-card">
                        <div className="stage-head">
                          <strong>Issue #{activeGitHub.issue.number}</strong>
                          <a href={activeGitHub.issue.html_url} target="_blank" rel="noreferrer">
                            Open
                          </a>
                        </div>
                        <div className="stage-meta">
                          <span>{activeGitHub.issue.state}</span>
                          <span>{activeGitHub.issue.author || "unknown"}</span>
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
                            Open
                          </a>
                        </div>
                        <div className="stage-meta">
                          <span>{activeGitHub.pull_request.state}</span>
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
                  <div className="empty-hint">No GitHub context for this task.</div>
                )}
              </div>
            )}

            {activeTab === "academic" && (
              <div className="panel-content">
                <h3>Academic Context</h3>
                {activeAcademic ? (
                  <div className="stage-list">
                    {activeAcademic.journal && (
                      <div className="stage-card">
                        <div className="stage-head">
                          <strong>{activeAcademic.journal.journal_name || "Journal"}</strong>
                          <span>{activeAcademic.journal.status}</span>
                        </div>
                        {activeAcademic.journal.journal_url && (
                          <a
                            href={activeAcademic.journal.journal_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open guidelines
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
                          <strong>Reference paper {index + 1}</strong>
                          <span>{reference.status}</span>
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
                  <div className="empty-hint">No academic context for this task.</div>
                )}
              </div>
            )}

            {activeTab === "approval" && (
              <div className="panel-content">
                <h3>Approval</h3>
                {activeApproval ? (
                  <div className="approval-card">
                    <div className="stage-head">
                      <strong>{activeApproval.summary}</strong>
                      <span>{activeApproval.status}</span>
                    </div>
                    <div className="approval-meta">
                      <span>Risk: {activeApproval.risk_level}</span>
                      <span>Updated: {formatDate(activeApproval.updated_at)}</span>
                    </div>
                    <div className="provider-list">
                      {activeApproval.actions.map((action) => (
                        <span key={action} className="pill">
                          {action}
                        </span>
                      ))}
                    </div>
                    {activeApproval.decision_comment && (
                      <p className="subtle">Comment: {activeApproval.decision_comment}</p>
                    )}
                    {activeTaskDetail?.status === "pending_approval" && activeApproval.status === "pending" && (
                      <div className="action-row approval-actions">
                        <button
                          type="button"
                          className="primary-button"
                          onClick={() => handleApprovalDecision("approve")}
                        >
                          Approve and continue
                        </button>
                        <button
                          type="button"
                          className="secondary-button"
                          onClick={() => handleApprovalDecision("reject")}
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="empty-hint">This task has no approval record.</div>
                )}
              </div>
            )}

            {activeTab === "metadata" && (
              <div className="panel-content">
                <h3>Task Metadata</h3>
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
            <h2>Model Control Center</h2>
            <span className="subtle">Priorities and enablement</span>
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
                  <span>Priority</span>
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
                    <option value="high">high</option>
                    <option value="medium">medium</option>
                    <option value="low">low</option>
                    <option value="disabled">disabled</option>
                  </select>
                </label>
                <label className="toggle-row">
                  <span>Enabled</span>
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
                  Save model settings
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="panel settings-panel provider-panel">
          <div className="panel-title-row">
            <h2>Provider/API Management</h2>
            <span className="subtle">Connection settings and key status</span>
          </div>
          <p className="subtle provider-note">
            API keys stay on the backend. This view only edits environment variable names and
            reports whether a key is configured.
          </p>
          <div className="settings-grid provider-grid">
            {providers.length === 0 ? (
              <div className="empty-hint">No providers loaded.</div>
            ) : (
              providers.map((provider) => {
                const testMessage = providerTestMessages[provider.provider_id];
                return (
                  <div key={provider.provider_id} className="settings-card provider-card">
                    <div className="stage-head">
                      <strong>{provider.display_name}</strong>
                      <span className={`pill ${provider.enabled ? "accent" : "muted"}`}>
                        {provider.enabled ? "Enabled" : "Disabled"}
                      </span>
                    </div>
                    {provider.description && (
                      <div className="subtle">{provider.description}</div>
                    )}

                    <div className="provider-secret-row">
                      <span>API key</span>
                      <strong className={provider.api_key_configured ? "key-ok" : "key-missing"}>
                        {provider.api_key_configured ? "Configured" : "Missing"}
                      </strong>
                    </div>

                    <label className="toggle-row">
                      <span>Enabled</span>
                      <input
                        type="checkbox"
                        aria-label={`${provider.display_name} enabled`}
                        checked={provider.enabled}
                        onChange={(event) =>
                          updateProviderDraft(provider.provider_id, {
                            enabled: event.target.checked,
                          })
                        }
                      />
                    </label>
                    <label>
                      <span>Base URL</span>
                      <input
                        type="text"
                        aria-label={`${provider.display_name} base URL`}
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
                      <span>Protocol</span>
                      <input
                        type="text"
                        aria-label={`${provider.display_name} protocol`}
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
                      <span>API key env</span>
                      <input
                        type="text"
                        aria-label={`${provider.display_name} API key environment variable`}
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
                        placeholder="Optional Anthropic-compatible endpoint"
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
                        aria-label={`Save ${provider.display_name} provider`}
                        onClick={() => handleProviderSave(provider)}
                      >
                        Save provider
                      </button>
                      <button
                        type="button"
                        className="secondary-button"
                        aria-label={`Test ${provider.display_name} connection`}
                        disabled={testingProviderId === provider.provider_id}
                        onClick={() => handleProviderTest(provider)}
                      >
                        {testingProviderId === provider.provider_id
                          ? "Testing..."
                          : "Test connection"}
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

  function renderRuleTemplates() {
    return (
      <div className="settings-shell template-shell">
        <div className="panel template-list-panel">
          <div className="panel-title-row">
            <h2>Rule Templates</h2>
            <button type="button" className="secondary-button" onClick={handleCreateTemplate}>
              New template
            </button>
          </div>
          <div className="history-list">
            {ruleTemplates.length === 0 ? (
              <div className="empty-hint">No templates yet.</div>
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
                    {template.is_default ? " / default" : ""}
                  </small>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="panel template-editor-panel">
          <div className="panel-title-row">
            <h2>Template Editor</h2>
            <span className="subtle">{editingTemplateId ? "Edit existing" : "Create new"}</span>
          </div>
          {settingsMessage && <div className="message success">{settingsMessage}</div>}
          {settingsError && <div className="message error">{settingsError}</div>}
          <div className="control-grid">
            <label>
              <span>Template ID</span>
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
              <span>Display Name</span>
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
              <span>Description</span>
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
              <span>Preset Mode</span>
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
              <span>Coordinator Model</span>
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
              <span>Task Types</span>
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
              <span>Trigger Keywords</span>
              <input
                type="text"
                value={templateDraft.trigger_keywords.join(", ")}
                placeholder="paper, review, journal"
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
              <span>Enabled</span>
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
              <span>Default</span>
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
              <span>Notes</span>
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
            <h3>Assignments</h3>
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
                      responsibility: "Describe responsibility",
                      model_id: models[0]?.model_id || "gpt-5.4",
                    },
                  ],
                }))
              }
            >
              Add assignment
            </button>
          </div>
          {renderAssignmentsEditor(templateDraft.assignments)}

          <div className="action-row">
            <button type="button" className="primary-button" onClick={handleSaveTemplate}>
              Save template
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={handleDeleteTemplate}
              disabled={!editingTemplateId}
            >
              Delete template
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
            <div className="brand-subtitle">Web Workspace</div>
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
            <div className="sidebar-heading">Recent Tasks</div>
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
              <div className="empty-hint">No tasks in history yet.</div>
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
                    {task.status} / {formatDate(task.updated_at)}
                  </small>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="sidebar-section compact">
          <div className="sidebar-heading">Pending approvals</div>
          <div className="provider-list">
            <span className="pill accent">{pendingApprovals.length} pending</span>
            {pendingApprovals.slice(0, 2).map((approval) => (
              <span key={approval.approval_id} className="pill">
                {approval.risk_level}
              </span>
            ))}
          </div>
        </section>

        <section className="sidebar-section compact">
          <div className="sidebar-heading">Backend</div>
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
            <h1>Mindforge Control Workspace</h1>
            <p>
              Web app shell inspired by OpenHands, with task history, approvals, model and
              provider control, and rule templates in one place.
            </p>
          </div>
          <div className="status-row">
            <span className="pill accent">Phase 11</span>
            <span className="pill">Paper revision ready</span>
            <span className="pill">{models.length} models</span>
            <span className="pill">{providers.length} providers</span>
            <span className="pill">{ruleTemplates.length} templates</span>
            <span className="pill">{historyItems.length} recent tasks</span>
          </div>
        </header>

        {view === "workspace" && renderWorkspace()}
        {view === "models" && renderModelControl()}
        {view === "rules" && renderRuleTemplates()}
      </main>
    </div>
  );
}
