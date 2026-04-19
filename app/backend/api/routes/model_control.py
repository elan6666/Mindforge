"""Editable model control and rule-template endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.backend.schemas.model import ModelControlUpdate, ModelSummary
from app.backend.schemas.rule_template import RuleTemplateSummary, RuleTemplateUpsert
from app.backend.services.model_control_service import (
    ModelControlError,
    ModelControlService,
    get_model_control_service,
)
from app.backend.services.rule_template_service import (
    RuleTemplateError,
    RuleTemplateService,
    get_rule_template_service,
)

router = APIRouter(prefix="/control")


@router.get("/models", response_model=list[ModelSummary])
def list_editable_models(
    service: ModelControlService = Depends(get_model_control_service),
) -> list[ModelSummary]:
    """Return current editable model state."""
    return service.list_models()


@router.put("/models/{model_id}", response_model=ModelSummary)
def update_editable_model(
    model_id: str,
    payload: ModelControlUpdate,
    service: ModelControlService = Depends(get_model_control_service),
) -> ModelSummary:
    """Persist editable fields for one model."""
    try:
        return service.update_model(model_id, payload)
    except ModelControlError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/rule-templates", response_model=list[RuleTemplateSummary])
def list_rule_templates(
    service: RuleTemplateService = Depends(get_rule_template_service),
) -> list[RuleTemplateSummary]:
    """Return all configured rule templates."""
    return service.list_templates()


@router.post(
    "/rule-templates",
    response_model=RuleTemplateSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_rule_template(
    payload: RuleTemplateUpsert,
    service: RuleTemplateService = Depends(get_rule_template_service),
) -> RuleTemplateSummary:
    """Create or replace a rule template."""
    try:
        return service.upsert_template(payload)
    except RuleTemplateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/rule-templates/{template_id}", response_model=RuleTemplateSummary)
def update_rule_template(
    template_id: str,
    payload: RuleTemplateUpsert,
    service: RuleTemplateService = Depends(get_rule_template_service),
) -> RuleTemplateSummary:
    """Update an existing rule template."""
    if template_id != payload.template_id:
        payload = payload.model_copy(update={"template_id": template_id})
    try:
        return service.upsert_template(payload)
    except RuleTemplateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/rule-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule_template(
    template_id: str,
    service: RuleTemplateService = Depends(get_rule_template_service),
) -> Response:
    """Delete a rule template."""
    try:
        service.delete_template(template_id)
    except RuleTemplateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
