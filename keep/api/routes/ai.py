import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from keep.api.core.db import (
    get_alerts_count,
    get_first_alert_datetime,
    get_incidents_count,
    get_or_create_external_ai_settings,
    get_session_sync,
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
    external_ai_settings = get_or_create_external_ai_settings(tenant_id)

    for setting in external_ai_settings:
        setting.algorithm.remind_about_the_client(tenant_id)

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

    # Verify AI model is configured via Settings > AI Configuration
    from keep.api.bl.ai_model_service import get_config, list_configs
    enabled_configs = [c for c in configs if c.enabled]
    if not enabled_configs:
        raise HTTPException(
            status_code=400,
            detail="AI model is not configured. Please configure AI models in Settings > AI Configuration.",
        )

    session = None
    try:
        from keep.api.bl.ai_suggestion_bl import AISuggestionBl
        from keep.api.core.db import get_last_alerts
        from keep.api.utils.enrichment_helpers import convert_db_alerts_to_dto_alerts
        from keep.topologies.topologies_service import TopologiesService

        session = get_session_sync()

        # Get settings
        ai_settings = get_or_create_external_ai_settings(tenant_id)
        internal_config = None
        for cfg in ai_settings:
            if "LLM" in cfg.algorithm_id:
                internal_config = cfg
                break

        if not internal_config:
            raise HTTPException(status_code=404, detail="LLM Correlation algorithm not found")

        # Parse settings with type safety
        settings = internal_config.settings
        if isinstance(settings, str):
            settings = json.loads(settings)
        settings_map = {s["name"]: s["value"] for s in settings}

        if not settings_map.get("Enabled", True):
            raise HTTPException(status_code=400, detail="LLM Correlation is disabled")

        max_alerts = int(settings_map.get("Max Alerts Per Batch", 20) or 20)
        include_topology = bool(settings_map.get("Include Topology Context", False))
        confidence_threshold = float(settings_map.get("Confidence Threshold", 0.5) or 0.5)
        auto_create = bool(settings_map.get("Auto Create Incidents", True))

        # Get recent alerts
        alerts = get_last_alerts(tenant_id, limit=max_alerts)
        if not alerts:
            return {
                "status": "no_alerts",
                "message": "No alerts to correlate",
                "alerts_analyzed": 0,
                "incidents_suggested": 0,
                "incidents_created": 0,
            }

        alerts_dto = convert_db_alerts_to_dto_alerts(alerts)

        # Get topology if enabled
        topology_data = []
        if include_topology:
            try:
                topology_data = TopologiesService.get_all_topology_data(tenant_id, session)
            except Exception:
                logger.warning("Failed to load topology data for AI correlation")

        # Run AI suggestion
        suggestion_bl = AISuggestionBl(tenant_id, session)
        result = suggestion_bl.suggest_incidents(
            alerts_dto=alerts_dto,
            topology_data=topology_data,
            user_id=authenticated_entity.email,
        )

        # Filter by confidence threshold
        high_confidence_incidents = [
            inc for inc in result.incident_suggestion
            if getattr(inc, "confidence_score", 1.0) >= confidence_threshold
        ]

        # Auto-create incidents if enabled
        incidents_created = 0
        if auto_create and high_confidence_incidents:
            try:
                from keep.api.bl.incidents_bl import IncidentBl
                incident_bl = IncidentBl(tenant_id=tenant_id, session=session)
                for incident in high_confidence_incidents:
                    incident_bl.create_incident(
                        incident_dto=incident,
                        generated_from_ai=True,
                    )
                    incidents_created += 1
            except Exception as e:
                logger.error(f"Failed to auto-create incidents: {e}")

        # Update feedback logs
        log_entry = (
            f"[{datetime.now(timezone.utc).isoformat()}] "
            f"Correlation run: {len(alerts_dto)} alerts analyzed, "
            f"{len(result.incident_suggestion)} incidents suggested, "
            f"{len(high_confidence_incidents)} above threshold, "
            f"{incidents_created} auto-created\n"
        )
        if internal_config.feedback_logs:
            log_entry = internal_config.feedback_logs + log_entry
        internal_config.feedback_logs = log_entry[-5000:]  # Keep last 5000 chars
        update_extrnal_ai_settings(tenant_id, internal_config)

        return {
            "status": "success",
            "alerts_analyzed": len(alerts_dto),
            "incidents_suggested": len(result.incident_suggestion),
            "incidents_above_threshold": len(high_confidence_incidents),
            "incidents_created": incidents_created,
            "suggestion_id": str(result.suggestion_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI correlation failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI correlation failed: {str(e)}")
    finally:
        if session:
            session.close()
