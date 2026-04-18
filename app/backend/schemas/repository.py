"""Schemas for local repository analysis and prompt injection."""

from pydantic import BaseModel, Field


class RepoKeyFile(BaseModel):
    """A repository file identified as important context."""

    path: str
    category: str


class RepoSummary(BaseModel):
    """Structured repository summary for metadata and prompt injection."""

    repo_path: str
    resolved_path: str
    repository_name: str
    detected_stack: list[str] = Field(default_factory=list)
    top_level_directories: list[str] = Field(default_factory=list)
    key_files: list[RepoKeyFile] = Field(default_factory=list)
    entrypoints: list[str] = Field(default_factory=list)
    summary_text: str


class RepoAnalysisResult(BaseModel):
    """Analysis outcome returned by the repository service."""

    status: str
    repo_summary: RepoSummary | None = None
    warnings: list[str] = Field(default_factory=list)
    error_message: str | None = None
