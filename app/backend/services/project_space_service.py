"""Project space registry and prompt-context assembly."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
import json
import os
from pathlib import Path

from app.backend.core.config import Settings, get_settings
from app.backend.schemas.project_space import (
    ProjectSpaceContext,
    ProjectSpaceSummary,
    ProjectSpaceUpsert,
)
from app.backend.services.file_context_service import FileContextService


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ProjectSpaceService:
    """Manage reusable project context, memory, and file references."""

    def __init__(
        self,
        settings: Settings,
        file_context_service: FileContextService | None = None,
    ) -> None:
        self.settings = settings
        self.registry_path = Path(settings.project_spaces_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_context_service = file_context_service or FileContextService(settings)

    def list_spaces(self) -> list[ProjectSpaceSummary]:
        """Return all project spaces, newest first."""
        spaces = list(self._load().values())
        return sorted(spaces, key=lambda item: item.updated_at, reverse=True)

    def get_space(self, project_id: str) -> ProjectSpaceSummary | None:
        """Return one project space."""
        return self._load().get(project_id)

    def upsert_space(self, payload: ProjectSpaceUpsert) -> ProjectSpaceSummary:
        """Create or update one project space."""
        spaces = self._load()
        now = _utc_now()
        existing = spaces.get(payload.project_id)
        normalized = payload.model_copy(
            update={
                "skill_ids": self._dedupe(payload.skill_ids),
                "mcp_server_ids": self._dedupe(payload.mcp_server_ids),
                "file_ids": self._dedupe(payload.file_ids),
                "tags": self._dedupe(payload.tags),
            }
        )
        summary = ProjectSpaceSummary(
            **normalized.model_dump(),
            file_count=len(normalized.file_ids),
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        spaces[summary.project_id] = summary
        self._save(spaces)
        return summary

    def delete_space(self, project_id: str) -> bool:
        """Delete one project space without deleting referenced files."""
        spaces = self._load()
        if project_id not in spaces:
            return False
        spaces.pop(project_id)
        self._save(spaces)
        return True

    def prompt_context(
        self,
        project_id: str | None,
        *,
        query: str,
    ) -> ProjectSpaceContext:
        """Return task-ready project context and relevant project file chunks."""
        if not project_id:
            return ProjectSpaceContext(status="skipped")
        project = self.get_space(project_id)
        if project is None:
            return ProjectSpaceContext(
                status="not_found",
                warnings=[f"Unknown project space '{project_id}'."],
            )
        if not project.enabled:
            return ProjectSpaceContext(
                status="disabled",
                project=project,
                warnings=[f"Project space '{project_id}' is disabled."],
            )
        file_context = None
        if project.file_ids:
            file_context = self.file_context_service.resolve_context(
                file_ids=project.file_ids,
                query=query,
                limit=10,
            )
        return ProjectSpaceContext(
            status="ready",
            project=project,
            file_context=file_context,
        )

    def _load(self) -> dict[str, ProjectSpaceSummary]:
        if not self.registry_path.exists():
            return {}
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        return {
            project_id: ProjectSpaceSummary.model_validate(item)
            for project_id, item in payload.get("projects", {}).items()
        }

    def _save(self, spaces: dict[str, ProjectSpaceSummary]) -> None:
        temp_path = self.registry_path.with_suffix(self.registry_path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(
                {
                    "projects": {
                        project_id: space.model_dump(mode="json")
                        for project_id, space in spaces.items()
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(temp_path, self.registry_path)

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for value in values:
            item = str(value).strip()
            if not item or item in seen:
                continue
            seen.add(item)
            normalized.append(item)
        return normalized


@lru_cache(maxsize=1)
def get_project_space_service() -> ProjectSpaceService:
    """Return cached project space service."""
    return ProjectSpaceService(get_settings())


def clear_project_space_service_cache() -> None:
    """Clear cached project space service after settings changes."""
    get_project_space_service.cache_clear()
