"""GitHub read-only context retrieval service."""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlparse

import requests

from app.backend.core.config import Settings, get_settings
from app.backend.schemas.github_context import (
    GitHubContextSummary,
    GitHubIssueSummary,
    GitHubPullRequestSummary,
    GitHubRepositorySummary,
)


class GitHubContextError(ValueError):
    """Raised when GitHub context resolution fails."""


def _truncate_text(value: str | None, limit: int = 280) -> str:
    if not value:
        return ""
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


class GitHubContextService:
    """Retrieve repository, issue, and pull request summaries from GitHub."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def resolve_context(
        self,
        *,
        github_repo: str | None,
        github_issue_number: int | None,
        github_pr_number: int | None,
    ) -> GitHubContextSummary | None:
        """Resolve GitHub context when task input includes GitHub references."""
        if not github_repo and not github_issue_number and not github_pr_number:
            return None
        if (github_issue_number or github_pr_number) and not github_repo:
            raise GitHubContextError(
                "GitHub issue/pr retrieval requires a repository reference."
            )
        owner, repo = self._parse_repo_ref(github_repo) if github_repo else (None, None)
        repository = (
            self.fetch_repository_summary(owner, repo) if owner is not None and repo is not None else None
        )
        issue = (
            self.fetch_issue_summary(owner, repo, github_issue_number)
            if github_issue_number is not None and owner is not None and repo is not None
            else None
        )
        pull_request = (
            self.fetch_pull_request_summary(owner, repo, github_pr_number)
            if github_pr_number is not None and owner is not None and repo is not None
            else None
        )
        return GitHubContextSummary(
            repository=repository,
            issue=issue,
            pull_request=pull_request,
        )

    def fetch_repository_summary(self, owner: str, repo: str) -> GitHubRepositorySummary:
        """Fetch repository metadata from GitHub."""
        body = self._get_json(f"/repos/{owner}/{repo}")
        return GitHubRepositorySummary(
            owner=owner,
            name=repo,
            full_name=body["full_name"],
            description=body.get("description"),
            html_url=body["html_url"],
            default_branch=body["default_branch"],
            primary_language=body.get("language"),
            stargazers_count=body.get("stargazers_count", 0),
            forks_count=body.get("forks_count", 0),
            open_issues_count=body.get("open_issues_count", 0),
            visibility=body.get("visibility"),
        )

    def fetch_issue_summary(self, owner: str, repo: str, issue_number: int) -> GitHubIssueSummary:
        """Fetch issue metadata from GitHub."""
        body = self._get_json(f"/repos/{owner}/{repo}/issues/{issue_number}")
        if "pull_request" in body:
            raise GitHubContextError(
                f"#{issue_number} in {owner}/{repo} is a pull request, not a pure issue."
            )
        return GitHubIssueSummary(
            number=body["number"],
            title=body["title"],
            state=body["state"],
            html_url=body["html_url"],
            author=(body.get("user") or {}).get("login"),
            labels=[label.get("name", "") for label in body.get("labels", []) if label.get("name")],
            comment_count=body.get("comments", 0),
            body_excerpt=_truncate_text(body.get("body")),
        )

    def fetch_pull_request_summary(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> GitHubPullRequestSummary:
        """Fetch pull request metadata from GitHub."""
        body = self._get_json(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        return GitHubPullRequestSummary(
            number=body["number"],
            title=body["title"],
            state=body["state"],
            html_url=body["html_url"],
            author=(body.get("user") or {}).get("login"),
            labels=[label.get("name", "") for label in body.get("labels", []) if label.get("name")],
            comment_count=body.get("comments", 0),
            review_comment_count=body.get("review_comments", 0),
            draft=bool(body.get("draft", False)),
            merged=bool(body.get("merged", False)),
            head_ref=(body.get("head") or {}).get("ref"),
            base_ref=(body.get("base") or {}).get("ref"),
            body_excerpt=_truncate_text(body.get("body")),
        )

    def _get_json(self, path: str) -> dict:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "mindforge-readonly-context",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        url = self.settings.github_api_base_url.rstrip("/") + path
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=self.settings.github_timeout_seconds,
            )
        except requests.RequestException as exc:
            raise GitHubContextError(f"GitHub request failed: {exc}") from exc
        if response.status_code == 404:
            raise GitHubContextError("GitHub resource not found.")
        if response.status_code >= 400:
            raise GitHubContextError(
                f"GitHub request failed with status {response.status_code}."
            )
        return response.json()

    @staticmethod
    def _parse_repo_ref(repo_ref: str | None) -> tuple[str, str]:
        if not repo_ref:
            raise GitHubContextError("GitHub repository reference is required.")
        trimmed = repo_ref.strip()
        if trimmed.startswith("http://") or trimmed.startswith("https://"):
            parsed = urlparse(trimmed)
            parts = [part for part in parsed.path.strip("/").split("/") if part]
            if len(parts) < 2:
                raise GitHubContextError("Invalid GitHub repository URL.")
            owner, repo = parts[0], parts[1]
        else:
            parts = [part for part in trimmed.split("/") if part]
            if len(parts) != 2:
                raise GitHubContextError(
                    "GitHub repository reference must look like owner/repo."
                )
            owner, repo = parts
        if repo.endswith(".git"):
            repo = repo[:-4]
        return owner, repo


@lru_cache(maxsize=1)
def get_github_context_service() -> GitHubContextService:
    """Return cached GitHub context service."""
    return GitHubContextService(get_settings())


def clear_github_context_service_cache() -> None:
    """Clear cached GitHub context service."""
    get_github_context_service.cache_clear()
