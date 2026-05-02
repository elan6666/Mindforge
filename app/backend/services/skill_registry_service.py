"""Local skill discovery and loading."""

from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import re

from app.backend.core.config import Settings, get_settings
from app.backend.schemas.skills import SkillDetail, SkillSettingsUpdate, SkillSummary

FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*\n", re.DOTALL)
SKILL_EXCERPT_LIMIT = 5000


class SkillRegistryService:
    """Scan configured roots for SKILL.md files and expose prompt-ready content."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings_path = Path(settings.skill_settings_path)
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)

    def list_skills(self) -> list[SkillSummary]:
        """Return all discovered skills, deduplicated by skill id."""
        return [self._to_summary(item) for item in self._discover().values()]

    def get_skill(self, skill_id: str) -> SkillDetail | None:
        """Return full details for one discovered skill."""
        item = self._discover().get(skill_id)
        if item is None:
            return None
        content = item["content"]
        return SkillDetail(
            **self._to_summary(item).model_dump(),
            content_excerpt=content[:SKILL_EXCERPT_LIMIT],
        )

    def load_prompt_context(self, skill_ids: list[str]) -> list[SkillDetail]:
        """Load selected skills as bounded prompt context."""
        details: list[SkillDetail] = []
        seen: set[str] = set()
        for skill_id in skill_ids:
            normalized = skill_id.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            detail = self.get_skill(normalized)
            if detail is not None and detail.enabled:
                details.append(detail)
        return details

    def update_skill_settings(
        self,
        skill_id: str,
        payload: SkillSettingsUpdate,
    ) -> SkillSummary | None:
        """Update user-controlled settings for one discovered skill."""
        discovered = self._discover()
        if skill_id not in discovered:
            return None
        settings = self._load_settings()
        current = dict(settings.get(skill_id, {}))
        updates = payload.model_dump(exclude_none=True)
        if "trust_level" in updates:
            updates["trust_level"] = str(updates["trust_level"]).strip() or "local"
        current.update(updates)
        settings[skill_id] = current
        self._save_settings(settings)
        return self._to_summary(discovered[skill_id])

    def _discover(self) -> dict[str, dict[str, str]]:
        discovered: dict[str, dict[str, str]] = {}
        used_ids: set[str] = set()
        for root_value in self.settings.skill_roots:
            root = Path(root_value).expanduser()
            if not root.exists():
                continue
            for skill_file in root.rglob("SKILL.md"):
                content = skill_file.read_text(encoding="utf-8", errors="replace")
                metadata = self._parse_frontmatter(content)
                base_id = str(metadata.get("name") or skill_file.parent.name).strip()
                skill_id = self._unique_id(self._slug(base_id), used_ids)
                used_ids.add(skill_id)
                discovered[skill_id] = {
                    "skill_id": skill_id,
                    "name": base_id or skill_id,
                    "description": str(metadata.get("description") or "").strip(),
                    "path": str(skill_file),
                    "source_root": str(root),
                    "content": content,
                }
        return dict(sorted(discovered.items(), key=lambda item: item[0]))

    @staticmethod
    def _parse_frontmatter(content: str) -> dict[str, str]:
        match = FRONTMATTER_PATTERN.match(content)
        if match is None:
            return {}
        metadata: dict[str, str] = {}
        for line in match.group("body").splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"')
        return metadata

    def _to_summary(self, item: dict[str, str]) -> SkillSummary:
        settings = self._load_settings()
        overrides = settings.get(item["skill_id"], {})
        return SkillSummary(
            skill_id=item["skill_id"],
            name=item["name"],
            description=item["description"],
            path=item["path"],
            source_root=item["source_root"],
            enabled=bool(overrides.get("enabled", True)),
            trust_level=str(overrides.get("trust_level") or "local"),
            notes=str(overrides.get("notes") or ""),
        )

    def _load_settings(self) -> dict[str, dict[str, object]]:
        if not self.settings_path.exists():
            return {}
        payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        values = payload.get("skills", {})
        return values if isinstance(values, dict) else {}

    def _save_settings(self, settings: dict[str, dict[str, object]]) -> None:
        temp_path = self.settings_path.with_suffix(self.settings_path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps({"skills": settings}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temp_path, self.settings_path)

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-")
        return slug or "skill"

    @staticmethod
    def _unique_id(base: str, used_ids: set[str]) -> str:
        if base not in used_ids:
            return base
        index = 2
        while f"{base}-{index}" in used_ids:
            index += 1
        return f"{base}-{index}"


@lru_cache(maxsize=1)
def get_skill_registry_service() -> SkillRegistryService:
    """Return cached skill registry service."""
    return SkillRegistryService(get_settings())


def clear_skill_registry_service_cache() -> None:
    """Clear cached skill registry after settings changes."""
    get_skill_registry_service.cache_clear()
