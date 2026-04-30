"""Academic paper context used by paper-revision tasks."""

from pydantic import BaseModel, Field


class JournalGuidelineSummary(BaseModel):
    """Journal-level guideline context supplied by the user or fetched from a URL."""

    journal_name: str | None = None
    journal_url: str | None = None
    title: str | None = None
    excerpt: str = ""
    status: str = "skipped"
    error_message: str | None = None


class ReferencePaperSummary(BaseModel):
    """Reference paper style signal used by paper revision stages."""

    url: str
    title: str | None = None
    excerpt: str = ""
    status: str = "skipped"
    error_message: str | None = None


class AcademicContextSummary(BaseModel):
    """Structured context for journal-aware academic paper revision."""

    journal: JournalGuidelineSummary | None = None
    reference_papers: list[ReferencePaperSummary] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
