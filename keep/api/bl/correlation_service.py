"""
Reusable correlation service.

Extracts the core correlation logic from the /correlate endpoint
so it can be called both from the API and from scheduled cron tasks.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session

from keep.api.core.db import (
    get_last_alerts,
    get_or_create_external_ai_settings,
    get_session_sync,
    update_extrnal_ai_settings,
)

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    """Structured result of a correlation run."""

    status: str
    alerts_analyzed: int = 0
    incidents_suggested: int = 0
    incidents_above_threshold: int = 0
    incidents_created: int = 0
    suggestion_id: Optional[str] = None
    message: str = ""


def get_correlation_settings(tenant_id: str) -> dict:
    """Read LLM correlation settings for a tenant.

    Returns a dict with typed values:
        enabled, max_alerts, include_topology, confidence_threshold,
        auto_create, auto_correlation, correlation_interval
    """
    ai_settings = get_or_create_external_ai_settings(tenant_id)
    internal_config = None
    for cfg in ai_settings:
        if "LLM" in cfg.algorithm_id:
            internal_config = cfg
            break

    if not internal_config:
        return {
            "enabled": False,
            "max_alerts": 20,
            "include_topology": False,
            "confidence_threshold": 0.5,
            "auto_create": True,
            "auto_correlation": False,
            "correlation_interval": 15,
        }

    settings = internal_config.settings
    if isinstance(settings, str):
        settings = json.loads(settings)
    settings_map = {s["name"]: s["value"] for s in settings}

    return {
        "enabled": bool(settings_map.get("Enabled", True)),
        "max_alerts": int(settings_map.get("Max Alerts Per Batch", 20) or 20),
        "include_topology": bool(settings_map.get("Include Topology Context", False)),
        "confidence_threshold": float(settings_map.get("Confidence Threshold", 0.5) or 0.5),
        "auto_create": bool(settings_map.get("Auto Create Incidents", True)),
        "auto_correlation": bool(settings_map.get("Auto Correlation", False)),
        "correlation_interval": int(settings_map.get("Correlation Interval (min)", 15) or 15),
    }


def run_correlation(
    tenant_id: str,
    session: Optional[Session] = None,
    user_id: Optional[str] = None,
) -> CorrelationResult:
    """Execute a single correlation run for a tenant.

    This is the shared core logic used by both the manual API endpoint
    and the scheduled auto-correlation cron task.

    Args:
        tenant_id: The tenant to run correlation for.
        session: Optional existing DB session. If None, a new one is created.
        user_id: Optional user identifier for AI suggestion tracking.

    Returns:
        CorrelationResult with statistics of the run.
    """
    from keep.api.bl.ai_model_service import list_configs

    # Check AI model availability
    configs = list_configs(tenant_id)
    enabled_configs = [c for c in configs if c.enabled]
    if not enabled_configs:
        return CorrelationResult(
            status="no_model",
            message="AI model is not configured",
        )

    own_session = session is None
    if own_session:
        session = get_session_sync()

    try:
        settings = get_correlation_settings(tenant_id)

        if not settings["enabled"]:
            return CorrelationResult(status="disabled", message="LLM Correlation is disabled")

        # Get recent alerts
        alerts = get_last_alerts(tenant_id, limit=settings["max_alerts"])
        if not alerts:
            return CorrelationResult(
                status="no_alerts",
                message="No alerts to correlate",
            )

        from keep.api.bl.ai_suggestion_bl import AISuggestionBl
        from keep.api.utils.enrichment_helpers import convert_db_alerts_to_dto_alerts

        alerts_dto = convert_db_alerts_to_dto_alerts(alerts)

        # Get topology if enabled
        topology_data = []
        if settings["include_topology"]:
            try:
                from keep.topologies.topologies_service import TopologiesService

                topology_data = TopologiesService.get_all_topology_data(tenant_id, session)
            except Exception:
                logger.warning("Failed to load topology data for AI correlation")

        # Run AI suggestion
        suggestion_bl = AISuggestionBl(tenant_id, session)
        result = suggestion_bl.suggest_incidents(
            alerts_dto=alerts_dto,
            topology_data=topology_data,
            user_id=user_id or "auto-correlation",
        )

        # Filter by confidence threshold
        high_confidence_incidents = [
            inc
            for inc in result.incident_suggestion
            if getattr(inc, "confidence_score", 1.0) >= settings["confidence_threshold"]
        ]

        # Auto-create incidents if enabled
        incidents_created = 0
        if settings["auto_create"] and high_confidence_incidents:
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
        _update_feedback_logs(
            tenant_id,
            alerts_analyzed=len(alerts_dto),
            incidents_suggested=len(result.incident_suggestion),
            incidents_above_threshold=len(high_confidence_incidents),
            incidents_created=incidents_created,
        )

        return CorrelationResult(
            status="success",
            alerts_analyzed=len(alerts_dto),
            incidents_suggested=len(result.incident_suggestion),
            incidents_above_threshold=len(high_confidence_incidents),
            incidents_created=incidents_created,
            suggestion_id=str(result.suggestion_id),
        )

    except Exception as e:
        logger.error(f"AI correlation failed: {e}")
        return CorrelationResult(
            status="error",
            message=str(e),
        )
    finally:
        if own_session:
            session.close()


def _update_feedback_logs(
    tenant_id: str,
    alerts_analyzed: int,
    incidents_suggested: int,
    incidents_above_threshold: int,
    incidents_created: int,
) -> None:
    """Append a correlation run summary to the feedback logs."""
    ai_settings = get_or_create_external_ai_settings(tenant_id)
    internal_config = None
    for cfg in ai_settings:
        if "LLM" in cfg.algorithm_id:
            internal_config = cfg
            break

    if not internal_config:
        return

    log_entry = (
        f"[{datetime.now(timezone.utc).isoformat()}] "
        f"Correlation run: {alerts_analyzed} alerts analyzed, "
        f"{incidents_suggested} incidents suggested, "
        f"{incidents_above_threshold} above threshold, "
        f"{incidents_created} auto-created\n"
    )
    if internal_config.feedback_logs:
        log_entry = internal_config.feedback_logs + log_entry
    internal_config.feedback_logs = log_entry[-5000:]
    update_extrnal_ai_settings(tenant_id, internal_config)
