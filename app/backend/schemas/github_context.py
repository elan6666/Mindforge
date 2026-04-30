"""GitHub read-only context schemas."""

from pydantic import BaseModel, Field


class GitHubRepositorySummary(BaseModel):
    """Summary of one GitHub repository."""

    owner: str
    name: str
    full_name: str
    description: str | None = None
    html_url: str
    default_branch: str
    primary_language: str | None = None
    stargazers_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0
    visibility: str | None = None


class GitHubIssueSummary(BaseModel):
    """Summary of one GitHub issue."""

    number: int
    title: str
    state: str
    html_url: str
    author: str | None = None
    labels: list[str] = Field(default_factory=list)
    comment_count: int = 0
    body_excerpt: str = ""


class GitHubPullRequestSummary(BaseModel):
    """Summary of one GitHub pull request."""

    number: int
    title: str
    state: str
    html_url: str
    author: str | None = None
    labels: list[str] = Field(default_factory=list)
    comment_count: int = 0
    review_comment_count: int = 0
    draft: bool = False
    merged: bool = False
    head_ref: str | None = None
    base_ref: str | None = None
    body_excerpt: str = ""


class GitHubContextSummary(BaseModel):
    """Aggregated GitHub read-only context attached to one task."""

    repository: GitHubRepositorySummary | None = None
    issue: GitHubIssueSummary | None = None
    pull_request: GitHubPullRequestSummary | None = None
