"""Approval-related schemas for blocking task gates."""

from pydantic import BaseModel, Field


class ApprovalRequirement(BaseModel):
    """Resolved approval requirement for one task submission."""

    required: bool = False
    risk_level: str = "none"
    summary: str = ""
    actions: list[str] = Field(default_factory=list)


class ApprovalRecord(BaseModel):
    """Persisted approval record for one task."""

    approval_id: str
    task_id: str
    status: str
    risk_level: str
    summary: str
    actions: list[str] = Field(default_factory=list)
    decision_comment: str | None = None
    created_at: str
    updated_at: str


class ApprovalDecisionRequest(BaseModel):
    """Approve/reject payload."""

    comment: str | None = Field(
        default=None,
        description="Optional user comment explaining the approval decision.",
    )
