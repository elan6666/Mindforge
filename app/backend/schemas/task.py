"""Request and response contracts for task execution."""

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class TaskAttachment(BaseModel):
    """Structured attachment context supplied by a composer."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("id", "attachment_id", "attachmentId"),
        description="Optional client-side attachment identifier.",
    )
    name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("name", "filename", "file_name", "fileName"),
        description="Display name or original filename.",
    )
    mime_type: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "mime_type",
            "mimeType",
            "content_type",
            "contentType",
        ),
        description="Attachment MIME/content type when known.",
    )
    size_bytes: int | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("size_bytes", "sizeBytes", "size"),
        description="Attachment size in bytes when known.",
    )
    text_excerpt: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "text_excerpt",
            "textExcerpt",
            "excerpt",
            "preview",
        ),
        description="Short text excerpt extracted from the attachment.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Attachment-specific metadata such as source, checksum, or parser hints.",
    )


class TaskToolFlags(BaseModel):
    """Composer-controlled execution affordances requested by the user."""

    model_config = ConfigDict(extra="allow")

    web_search: bool | None = Field(
        default=None,
        description="Whether the composer requested web search.",
    )
    deep_analysis: bool | None = Field(
        default=None,
        description="Whether the composer requested deeper analysis mode.",
    )
    code_execution: bool | None = Field(
        default=None,
        description="Whether the composer requested code execution affordances.",
    )
    canvas: bool | None = Field(
        default=None,
        description="Whether the composer requested canvas/artifact support.",
    )


class TaskConversationMessage(BaseModel):
    """One prior message in a continuing composer conversation."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    role: str = Field(
        default="user",
        description="Conversation role, usually user or assistant.",
    )
    content: str = Field(..., min_length=1, description="Message text.")
    task_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("task_id", "taskId"),
        description="Task run that produced or consumed this message.",
    )
    created_at: str | None = Field(
        default=None,
        validation_alias=AliasChoices("created_at", "createdAt"),
        description="Client-side or persisted creation timestamp.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional message metadata for future conversation features.",
    )


class TaskRequest(BaseModel):
    """Incoming task payload accepted by the API."""

    model_config = ConfigDict(populate_by_name=True)

    prompt: str = Field(..., min_length=1, description="Primary task prompt.")
    task_type: str | None = Field(
        default=None,
        description="Optional high-level task type used by model routing.",
    )
    preset_mode: str | None = Field(
        default=None,
        description="Optional preset or scenario identifier.",
    )
    model_override: str | None = Field(
        default=None,
        description="Optional explicit single-pass model override.",
    )
    rule_template_id: str | None = Field(
        default=None,
        description="Optional explicit rule template selection for dynamic role assignment.",
    )
    role_model_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Optional role-to-model overrides for multi-stage execution.",
    )
    conversation_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("conversation_id", "conversationId"),
        description="Stable client-side conversation identifier for follow-up turns.",
    )
    conversation_history: list[TaskConversationMessage] = Field(
        default_factory=list,
        validation_alias=AliasChoices("conversation_history", "conversationHistory"),
        description="Prior messages in the same conversation, excluding the current prompt.",
    )
    github_repo: str | None = Field(
        default=None,
        description="Optional GitHub repository reference such as owner/repo.",
    )
    github_issue_number: int | None = Field(
        default=None,
        ge=1,
        description="Optional GitHub issue number used for read-only context retrieval.",
    )
    github_pr_number: int | None = Field(
        default=None,
        ge=1,
        description="Optional GitHub pull request number used for read-only context retrieval.",
    )
    journal_name: str | None = Field(
        default=None,
        description="Optional journal name used by paper-revision standards analysis.",
    )
    journal_url: str | None = Field(
        default=None,
        description="Optional journal guideline URL used for read-only standards context.",
    )
    reference_paper_urls: list[str] = Field(
        default_factory=list,
        description="Optional reference paper URLs used for style and structure context.",
    )
    attachments: list[TaskAttachment] = Field(
        default_factory=list,
        description="Structured composer attachments with metadata and text excerpts.",
    )
    tool_flags: TaskToolFlags = Field(
        default_factory=TaskToolFlags,
        description="Grouped composer/tool flags.",
    )
    web_search: bool | None = Field(
        default=None,
        description="Top-level compatibility flag for requested web search.",
    )
    deep_analysis: bool | None = Field(
        default=None,
        description="Top-level compatibility flag for requested deeper analysis.",
    )
    code_execution: bool | None = Field(
        default=None,
        description="Top-level compatibility flag for requested code execution.",
    )
    canvas: bool | None = Field(
        default=None,
        description="Top-level compatibility flag for requested canvas/artifact support.",
    )
    repo_path: str | None = Field(
        default=None,
        description="Optional repository path to analyze later.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional task metadata for future extensions.",
    )


class TaskResponseData(BaseModel):
    """Structured execution details returned to the caller."""

    output: str
    provider: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    """Normalized API response returned by the service layer."""

    status: str
    message: str
    data: TaskResponseData
    error_message: str | None = None


class TaskErrorResponse(BaseModel):
    """Structured failure payload for invalid task submissions."""

    status: str = "failed"
    message: str
    error_message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
