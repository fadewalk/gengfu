"""AI Model Configuration API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from keep.api.bl.ai_model_service import (
    list_configs,
    get_config,
    create_config,
    update_config,
    delete_config,
    get_assignments,
    update_assignments,
    test_connection,
)
from keep.api.core.db import get_session
from keep.api.i18n import t
from keep.api.models.db.ai_model_config import (
    AIModelConfigCreate,
    AIModelConfigUpdate,
    AIModelAssignmentUpdate,
    AI_SCENARIOS,
)
from keep.identitymanager.authenticatedentity import AuthenticatedEntity
from keep.identitymanager.identitymanagerfactory import IdentityManagerFactory

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model Config CRUD
# ---------------------------------------------------------------------------


@router.get("/models", description="List all AI model configurations")
def list_model_configs(
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:settings"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id: str = authenticated_entity.tenant_id
    return list_configs(tenant_id)


@router.post("/models", description="Create a new AI model configuration")
def create_model_config(
    data: AIModelConfigCreate,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:settings"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id: str = authenticated_entity.tenant_id
    created_by = authenticated_entity.email
    try:
        return create_config(tenant_id, data, created_by)
    except ValueError as e:
        logger.error(f"Failed to create AI model config: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/models/{config_id}", description="Update an AI model configuration")
def update_model_config(
    config_id: str,
    data: AIModelConfigUpdate,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:settings"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id: str = authenticated_entity.tenant_id
    try:
        return update_config(tenant_id, config_id, data)
    except ValueError as e:
        logger.error(f"Failed to update AI model config: {e}")
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/models/{config_id}", description="Delete an AI model configuration"
)
def delete_model_config(
    config_id: str,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["delete:settings"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id: str = authenticated_entity.tenant_id
    try:
        deleted = delete_config(tenant_id, config_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=t("AI model configuration not found"),
            )
        return {"message": t("AI model configuration deleted")}
    except ValueError as e:
        logger.error(f"Failed to delete AI model config: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/models/{config_id}/test",
    description="Test connection to an AI model endpoint",
)
def test_model_connection_endpoint(
    config_id: str,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:settings"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id: str = authenticated_entity.tenant_id
    try:
        return test_connection(tenant_id, config_id)
    except ValueError as e:
        logger.error(f"Failed to test AI model connection: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Scenario Assignments
# ---------------------------------------------------------------------------


@router.get(
    "/assignments", description="Get all scenario-to-model assignments"
)
def list_assignments(
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:settings"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id: str = authenticated_entity.tenant_id
    return get_assignments(tenant_id)


@router.put(
    "/assignments", description="Update scenario-to-model assignments"
)
def update_assignment_list(
    body: dict,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:settings"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id: str = authenticated_entity.tenant_id
    try:
        raw = body.get("assignments", [])
        assignments = [AIModelAssignmentUpdate(**a) for a in raw]
        return update_assignments(tenant_id, assignments)
    except ValueError as e:
        logger.error(f"Failed to update assignments: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Scenario Definitions
# ---------------------------------------------------------------------------


@router.get("/scenarios", description="List predefined AI scenarios")
def list_scenarios(
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:settings"])
    ),
):
    """Scenarios are static and not tenant-specific."""
    return [scenario.model_dump() for scenario in AI_SCENARIOS]
