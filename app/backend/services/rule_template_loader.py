"""JSON loader for user-editable rule templates."""

import json
from pathlib import Path

from app.backend.schemas.rule_template import RuleTemplateCatalog
from app.backend.services.model_loader import MODEL_CONTROL_DIR

RULE_TEMPLATES_PATH = MODEL_CONTROL_DIR / "rule_templates.json"


def load_rule_template_catalog() -> RuleTemplateCatalog:
    """Load rule templates from JSON."""
    if not RULE_TEMPLATES_PATH.exists():
        return RuleTemplateCatalog()
    with RULE_TEMPLATES_PATH.open("r", encoding="utf-8") as handle:
        raw_data = json.load(handle) or {}
    return RuleTemplateCatalog.model_validate(raw_data)


def save_rule_template_catalog(catalog: RuleTemplateCatalog) -> None:
    """Persist rule templates to JSON."""
    MODEL_CONTROL_DIR.mkdir(parents=True, exist_ok=True)
    with RULE_TEMPLATES_PATH.open("w", encoding="utf-8") as handle:
        json.dump(catalog.model_dump(), handle, ensure_ascii=False, indent=2)
