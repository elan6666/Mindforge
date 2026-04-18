"""Load preset definitions from YAML files."""

from pathlib import Path

import yaml

from app.backend.schemas.preset import PresetDefinition


def get_presets_dir() -> Path:
    """Return the preset directory path."""
    return Path(__file__).resolve().parents[2] / "presets"


def load_preset_file(path: Path) -> PresetDefinition:
    """Read and validate a single preset file."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return PresetDefinition.model_validate(data)


def load_all_presets() -> dict[str, PresetDefinition]:
    """Load every preset file from the preset directory."""
    presets_dir = get_presets_dir()
    presets: dict[str, PresetDefinition] = {}
    for path in sorted(presets_dir.glob("*.yaml")):
        preset = load_preset_file(path)
        presets[preset.preset_mode] = preset
    return presets

