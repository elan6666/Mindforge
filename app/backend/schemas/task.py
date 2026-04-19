"""Request and response contracts for task execution."""

from typing import Any

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    """Incoming task payload accepted by the API."""

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
