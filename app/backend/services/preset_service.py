"""Registry service for preset template resolution."""

from functools import lru_cache

from app.backend.schemas.preset import PresetDefinition, PresetSummary
from app.backend.services.preset_loader import load_all_presets


class PresetNotFoundError(ValueError):
    """Raised when an explicit preset mode is unknown."""


class PresetService:
    """Provide preset listing and resolution over YAML-backed templates."""

    def __init__(self) -> None:
        self._presets = load_all_presets()
        if "default" not in self._presets:
            raise PresetNotFoundError("Default preset is missing.")

    def list_presets(self) -> list[PresetSummary]:
        """Return lightweight preset descriptions for API clients."""
        return [
            PresetSummary(
                preset_mode=preset.preset_mode,
                display_name=preset.display_name,
                description=preset.description,
                requires_repo_analysis=preset.requires_repo_analysis,
                requires_approval=preset.requires_approval,
            )
            for preset in self._presets.values()
        ]

    def resolve(self, requested_mode: str | None) -> tuple[PresetDefinition, bool]:
        """Resolve a preset by mode, with default fallback for missing values."""
        if not requested_mode:
            return self._presets["default"], True
        preset = self._presets.get(requested_mode)
        if preset is None:
            raise PresetNotFoundError(
                f"Unknown preset_mode '{requested_mode}'. Available presets: "
                + ", ".join(sorted(self._presets))
            )
        return preset, False


@lru_cache(maxsize=1)
def get_preset_service() -> PresetService:
    """Return a cached preset registry."""
    return PresetService()

