"""Collect lightweight journal and reference-paper context."""

from __future__ import annotations

import re
from functools import lru_cache
from html import unescape

import requests

from app.backend.core.config import Settings, get_settings
from app.backend.schemas.academic_context import (
    AcademicContextSummary,
    JournalGuidelineSummary,
    ReferencePaperSummary,
)
from app.backend.schemas.task import TaskRequest

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


class AcademicContextService:
    """Fetch small, read-only paper context without turning Phase 10 into a crawler."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def resolve_context(self, payload: TaskRequest) -> AcademicContextSummary | None:
        """Resolve academic context when paper-related fields are present."""
        if not (
            payload.journal_name
            or payload.journal_url
            or payload.reference_paper_urls
        ):
            return None

        warnings: list[str] = []
        journal = self._build_journal_summary(payload, warnings)
        references = [
            self._fetch_reference_summary(url, warnings)
            for url in payload.reference_paper_urls
            if url.strip()
        ]
        return AcademicContextSummary(
            journal=journal,
            reference_papers=references,
            warnings=warnings,
        )

    def _build_journal_summary(
        self,
        payload: TaskRequest,
        warnings: list[str],
    ) -> JournalGuidelineSummary | None:
        if not payload.journal_name and not payload.journal_url:
            return None
        if not payload.journal_url:
            warnings.append(
                "Journal name was provided without a URL; standards-editor should ask for or infer missing guidelines explicitly."
            )
            return JournalGuidelineSummary(
                journal_name=payload.journal_name,
                journal_url=None,
                status="name-only",
            )
        page = self._fetch_page_excerpt(payload.journal_url)
        if page["status"] != "fetched":
            warnings.append(f"Journal guideline URL could not be fetched: {payload.journal_url}")
        return JournalGuidelineSummary(
            journal_name=payload.journal_name,
            journal_url=payload.journal_url,
            title=page["title"],
            excerpt=page["excerpt"],
            status=page["status"],
            error_message=page["error_message"],
        )

    def _fetch_reference_summary(
        self,
        url: str,
        warnings: list[str],
    ) -> ReferencePaperSummary:
        page = self._fetch_page_excerpt(url)
        if page["status"] != "fetched":
            warnings.append(f"Reference paper URL could not be fetched: {url}")
        return ReferencePaperSummary(
            url=url,
            title=page["title"],
            excerpt=page["excerpt"],
            status=page["status"],
            error_message=page["error_message"],
        )

    def _fetch_page_excerpt(self, url: str, limit: int = 1400) -> dict[str, str | None]:
        try:
            response = requests.get(
                url,
                timeout=self.settings.academic_context_timeout_seconds,
                headers={"User-Agent": "Mindforge/0.1 academic-context"},
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return {
                "status": "failed",
                "title": None,
                "excerpt": "",
                "error_message": str(exc),
            }

        text = response.text or ""
        title_match = TITLE_RE.search(text)
        title = self._clean_text(title_match.group(1)) if title_match else None
        excerpt = self._clean_text(text)[:limit]
        return {
            "status": "fetched",
            "title": title,
            "excerpt": excerpt,
            "error_message": None,
        }

    @staticmethod
    def _clean_text(raw_text: str) -> str:
        text = TAG_RE.sub(" ", raw_text)
        return SPACE_RE.sub(" ", unescape(text)).strip()


@lru_cache(maxsize=1)
def get_academic_context_service() -> AcademicContextService:
    """Return cached academic context service."""
    return AcademicContextService(get_settings())


def clear_academic_context_service_cache() -> None:
    """Clear cached academic context service after settings changes."""
    get_academic_context_service.cache_clear()
