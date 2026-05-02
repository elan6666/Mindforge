"""Schemas for generated document artifacts."""

from typing import Literal

from pydantic import BaseModel, Field

ArtifactFormat = Literal["md", "pdf", "docx", "tex"]


class ArtifactExportRequest(BaseModel):
    """Request to export model/canvas content as a downloadable document."""

    title: str = Field(default="Mindforge artifact")
    content: str = Field(..., min_length=1)
    format: ArtifactFormat
    source_task_id: str | None = None


class ArtifactSummary(BaseModel):
    """Generated document artifact metadata."""

    artifact_id: str
    title: str
    format: ArtifactFormat
    filename: str
    mime_type: str
    size_bytes: int
    created_at: str
    source_task_id: str | None = None
    download_url: str
