"""History and persistence-facing schemas."""

from typing import Any

from pydantic import BaseModel, Field

from app.backend.schemas.approval import ApprovalRecord


class TaskHistorySummary(BaseModel):
    """Compact task-history row for list views."""

    task_id: str
    prompt: str
    preset_mode: str
    task_type: str | None = None
    status: str
    provider: str | None = None
    created_at: str
    updated_at: str
    requires_approval: bool = False
    approval_status: str | None = None
    conversation_id: str | None = None
    conversation_turn_count: int | None = None


class StageHistoryRecord(BaseModel):
    """Persisted stage execution row."""

    order: int
    stage_id: str
    stage_name: str
    role: str
    model: str
    provider: str | None = None
    status: str
    summary: str
    output: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    created_at: str


class TaskHistoryDetail(TaskHistorySummary):
    """Expanded task history detail used by the frontend drawer."""

    repo_path: str | None = None
    message: str
    output: str
    error_message: str | None = None
    request_payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    stages: list[StageHistoryRecord] = Field(default_factory=list)
    approval: ApprovalRecord | None = None


class CanvasArtifactUpdate(BaseModel):
    """Editable canvas artifact update payload."""

    title: str | None = Field(default=None, max_length=160)
    content: Any
