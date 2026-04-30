"""Editable model control and rule-template endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.backend.schemas.model import (
    ModelCreateRequest,
    ModelControlUpdate,
    ModelSummary,
    ProviderConnectionTestResult,
    ProviderCreateRequest,
    ProviderControlUpdate,
    ProviderSummary,
)
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


@router.get("/user-models", response_model=list[ModelSummary])
def list_user_models(
    service: ModelControlService = Depends(get_model_control_service),
) -> list[ModelSummary]:
    """Return user-created models for the control center."""
    return service.list_custom_models()


@router.post(
    "/models",
    response_model=ModelSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_editable_model(
    payload: ModelCreateRequest,
    service: ModelControlService = Depends(get_model_control_service),
) -> ModelSummary:
    """Create a user-managed model."""
    try:
        return service.create_model(payload)
    except ModelControlError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_editable_model(
    model_id: str,
    service: ModelControlService = Depends(get_model_control_service),
) -> Response:
    """Delete a user-managed model."""
    try:
        service.delete_model(model_id)
    except ModelControlError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/providers", response_model=list[ProviderSummary])
def list_editable_providers(
    service: ModelControlService = Depends(get_model_control_service),
) -> list[ProviderSummary]:
    """Return current editable provider state."""
    return service.list_providers()


@router.get("/user-providers", response_model=list[ProviderSummary])
def list_user_providers(
    service: ModelControlService = Depends(get_model_control_service),
) -> list[ProviderSummary]:
    """Return user-created providers for the API management UI."""
    return service.list_custom_providers()


@router.post(
    "/providers",
    response_model=ProviderSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_editable_provider(
    payload: ProviderCreateRequest,
    service: ModelControlService = Depends(get_model_control_service),
) -> ProviderSummary:
    """Create a user-managed provider."""
    try:
        return service.create_provider(payload)
    except ModelControlError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/providers/{provider_id}", response_model=ProviderSummary)
def update_editable_provider(
    provider_id: str,
    payload: ProviderControlUpdate,
    service: ModelControlService = Depends(get_model_control_service),
) -> ProviderSummary:
    """Persist editable fields for one provider."""
    try:
        return service.update_provider(provider_id, payload)
    except ModelControlError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_editable_provider(
    provider_id: str,
    service: ModelControlService = Depends(get_model_control_service),
) -> Response:
    """Delete a user-managed provider."""
    try:
        service.delete_provider(provider_id)
    except ModelControlError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/providers/{provider_id}/test", response_model=ProviderConnectionTestResult)
def test_provider_connection(
    provider_id: str,
    service: ModelControlService = Depends(get_model_control_service),
) -> ProviderConnectionTestResult:
    """Check local connectivity/configuration for one provider."""
    try:
        return service.test_provider_connection(provider_id)
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
