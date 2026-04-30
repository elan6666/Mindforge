"""GitHub read-only context endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.backend.schemas.github_context import (
    GitHubIssueSummary,
    GitHubPullRequestSummary,
    GitHubRepositorySummary,
)
from app.backend.services.github_context_service import (
    GitHubContextError,
    GitHubContextService,
    get_github_context_service,
)

router = APIRouter(prefix="/github")


@router.get("/repositories/{owner}/{repo}", response_model=GitHubRepositorySummary)
def get_repository_summary(
    owner: str,
    repo: str,
    service: GitHubContextService = Depends(get_github_context_service),
) -> GitHubRepositorySummary:
    """Return one GitHub repository summary."""
    try:
        return service.fetch_repository_summary(owner, repo)
    except GitHubContextError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/repositories/{owner}/{repo}/issues/{issue_number}",
    response_model=GitHubIssueSummary,
)
def get_issue_summary(
    owner: str,
    repo: str,
    issue_number: int,
    service: GitHubContextService = Depends(get_github_context_service),
) -> GitHubIssueSummary:
    """Return one GitHub issue summary."""
    try:
        return service.fetch_issue_summary(owner, repo, issue_number)
    except GitHubContextError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/repositories/{owner}/{repo}/pulls/{pr_number}",
    response_model=GitHubPullRequestSummary,
)
def get_pull_request_summary(
    owner: str,
    repo: str,
    pr_number: int,
    service: GitHubContextService = Depends(get_github_context_service),
) -> GitHubPullRequestSummary:
    """Return one GitHub pull request summary."""
    try:
        return service.fetch_pull_request_summary(owner, repo, pr_number)
    except GitHubContextError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
