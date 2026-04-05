import json
import logging

from fastapi import APIRouter, Depends, HTTPException

from keep.api.bl.correlation_service import run_correlation
from keep.api.core.db import (
    get_alerts_count,
    get_first_alert_datetime,
    get_incidents_count,
    get_or_create_external_ai_settings,
    update_extrnal_ai_settings,
)
from keep.api.models.ai_external import ExternalAIConfigAndMetadataDto
from keep.identitymanager.authenticatedentity import AuthenticatedEntity
from keep.identitymanager.identitymanagerfactory import IdentityManagerFactory

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/stats",
    description="Get stats for the AI Landing Page",
    include_in_schema=False,
)
def get_stats(
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:alert"])
    ),
):
    tenant_id = authenticated_entity.tenant_id
    try:
        external_ai_settings = get_or_create_external_ai_settings(tenant_id)
    except Exception:
        logger.exception("Failed to get external AI settings")
        external_ai_settings = []

    for setting in external_ai_settings:
        try:
            setting.algorithm.remind_about_the_client(tenant_id)
        except Exception:
            logger.warning(f"Failed to remind algorithm {setting.algorithm_id} about client")

    return {
        "alerts_count": get_alerts_count(tenant_id),
        "first_alert_datetime": get_first_alert_datetime(tenant_id),
        "incidents_count": get_incidents_count(tenant_id),
        "algorithm_configs": external_ai_settings,
    }


@router.put(
    "/{algorithm_id}/settings",
    description="Update settings for an external AI",
    include_in_schema=False,
)
def update_settings(
    algorithm_id: str,
    body: ExternalAIConfigAndMetadataDto,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:alert"])
    ),
):
    tenant_id = authenticated_entity.tenant_id
    return update_extrnal_ai_settings(tenant_id, body)


@router.post(
    "/correlate",
    description="Manually trigger AI correlation for unassigned alerts",
    include_in_schema=False,
)
def trigger_correlation(
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:alert"])
    ),
):
    """Run LLM-based correlation on unassigned alerts."""
    tenant_id = authenticated_entity.tenant_id

    result = run_correlation(
        tenant_id=tenant_id,
        user_id=authenticated_entity.email,
    )

    if result.status == "no_model":
        raise HTTPException(
            status_code=400,
            detail="AI model is not configured. Please configure AI models in Settings > AI Configuration.",
        )
    if result.status == "disabled":
        raise HTTPException(status_code=400, detail="LLM Correlation is disabled")
    if result.status == "error":
        raise HTTPException(status_code=500, detail=result.message)

    return {
        "status": result.status,
        "alerts_analyzed": result.alerts_analyzed,
        "incidents_suggested": result.incidents_suggested,
        "incidents_above_threshold": result.incidents_above_threshold,
        "incidents_created": result.incidents_created,
        "suggestion_id": result.suggestion_id,
    }
