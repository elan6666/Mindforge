from pathlib import Path

import pytest

from app.backend.services.preset_loader import (
    get_presets_dir,
    load_all_presets,
    load_preset_file,
)
from app.backend.services.preset_service import PresetNotFoundError, PresetService


def test_get_presets_dir_points_to_existing_directory():
    presets_dir = get_presets_dir()

    assert presets_dir.exists()
    assert presets_dir.is_dir()


def test_load_preset_file_reads_code_engineering_template():
    preset = load_preset_file(Path("app/presets/code-engineering.yaml"))

    assert preset.preset_mode == "code-engineering"
    assert preset.requires_repo_analysis is True
    assert preset.agent_roles == [
        "project-manager",
        "backend",
        "frontend",
        "reviewer",
    ]


def test_load_all_presets_includes_expected_modes():
    presets = load_all_presets()

    assert {"default", "code-engineering", "code-review", "doc-organize"}.issubset(
        presets.keys()
    )


def test_preset_service_lists_presets_with_summary_fields():
    service = PresetService()

    presets = service.list_presets()
    preset_modes = {preset.preset_mode for preset in presets}

    assert "default" in preset_modes
    assert "code-engineering" in preset_modes
    assert all(hasattr(preset, "display_name") for preset in presets)


def test_preset_service_resolve_uses_default_for_missing_mode():
    service = PresetService()

    preset, used_default = service.resolve(None)

    assert preset.preset_mode == "default"
    assert used_default is True


def test_preset_service_resolve_raises_for_unknown_mode():
    service = PresetService()

    with pytest.raises(PresetNotFoundError):
        service.resolve("missing-mode")
