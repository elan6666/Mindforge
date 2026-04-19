"""YAML/JSON loaders for provider-model configuration and mutable overrides."""

import json
from pathlib import Path

import yaml

from app.backend.schemas.model import ModelCatalog, ModelOverridesDocument

MODEL_REGISTRY_DIR = Path(__file__).resolve().parents[2] / "model_registry"
CATALOG_PATH = MODEL_REGISTRY_DIR / "catalog.yaml"
MODEL_CONTROL_DIR = Path(__file__).resolve().parents[2] / "model_control"
MODEL_OVERRIDES_PATH = MODEL_CONTROL_DIR / "model_overrides.json"


def load_model_catalog() -> ModelCatalog:
    """Load the full model catalog from YAML."""
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Model catalog not found: {CATALOG_PATH}")
    with CATALOG_PATH.open("r", encoding="utf-8") as handle:
        raw_data = yaml.safe_load(handle) or {}
    return ModelCatalog.model_validate(raw_data)


def load_model_overrides() -> ModelOverridesDocument:
    """Load user-editable model overrides from JSON."""
    if not MODEL_OVERRIDES_PATH.exists():
        return ModelOverridesDocument()
    with MODEL_OVERRIDES_PATH.open("r", encoding="utf-8") as handle:
        raw_data = json.load(handle) or {}
    return ModelOverridesDocument.model_validate(raw_data)


def save_model_overrides(document: ModelOverridesDocument) -> None:
    """Persist user-editable model overrides to JSON."""
    MODEL_CONTROL_DIR.mkdir(parents=True, exist_ok=True)
    with MODEL_OVERRIDES_PATH.open("w", encoding="utf-8") as handle:
        json.dump(document.model_dump(), handle, ensure_ascii=False, indent=2)
