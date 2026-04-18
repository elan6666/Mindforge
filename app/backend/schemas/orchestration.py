"""Structured orchestration metadata for multi-stage task execution."""

from typing import Any

from pydantic import BaseModel, Field


class StageExecution(BaseModel):
    """One executed stage in a serial multi-agent chain."""

    order: int
    stage_id: str
    stage_name: str
    role: str
    model: str
    status: str
    provider: str
    summary: str
    output: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class OrchestrationTrace(BaseModel):
    """Serializable trace returned to API callers for orchestration visibility."""

    preset_mode: str
    strategy: str
    total_stages: int
    completed_stages: int
    failed_stage: str | None = None
    stages: list[StageExecution] = Field(default_factory=list)
