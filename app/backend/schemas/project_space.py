"""Schemas for project-level context spaces."""

from pydantic import BaseModel, Field

from app.backend.schemas.file_context import FileContextSummary


class ProjectSpaceUpsert(BaseModel):
    """Create or update a reusable project context space."""

    project_id: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    description: str = ""
    instructions: str = ""
    memory: str = ""
    default_preset_mode: str | None = None
    repo_path: str | None = None
    github_repo: str | None = None
    skill_ids: list[str] = Field(default_factory=list)
    mcp_server_ids: list[str] = Field(default_factory=list)
    file_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    enabled: bool = True


class ProjectSpaceSummary(ProjectSpaceUpsert):
    """Stored project space metadata."""

    file_count: int = 0
    created_at: str
    updated_at: str


class ProjectSpaceContext(BaseModel):
    """Prompt-ready project context for one task."""

    status: str
    project: ProjectSpaceSummary | None = None
    file_context: FileContextSummary | None = None
    warnings: list[str] = Field(default_factory=list)
