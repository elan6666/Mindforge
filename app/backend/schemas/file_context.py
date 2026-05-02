"""Schemas for uploaded file parsing and retrieval context."""

from typing import Any

from pydantic import BaseModel, Field


class FileChunk(BaseModel):
    """One searchable chunk extracted from an uploaded file."""

    chunk_id: str
    file_id: str
    order: int
    text: str
    char_start: int = 0
    char_end: int = 0
    score: float = 0


class UploadedFileSummary(BaseModel):
    """Public metadata for one uploaded and parsed file."""

    file_id: str
    name: str
    mime_type: str | None = None
    size_bytes: int
    sha256: str
    status: str
    parser: str
    text_excerpt: str = ""
    char_count: int = 0
    chunk_count: int = 0
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FileContextSummary(BaseModel):
    """Task-ready retrieval context selected from uploaded files."""

    status: str
    file_ids: list[str] = Field(default_factory=list)
    files: list[UploadedFileSummary] = Field(default_factory=list)
    chunks: list[FileChunk] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
