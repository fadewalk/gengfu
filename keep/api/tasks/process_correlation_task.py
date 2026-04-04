"""
Scheduled auto-correlation task.

Runs periodically via ARQ cron to automatically correlate unassigned alerts
for tenants that have Auto Correlation enabled.
"""

import logging

logger = logging.getLogger(__name__)


def _get_all_tenant_ids() -> list[str]:
    """Query all tenant IDs from the database."""
    from sqlmodel import Session, select

    from keep.api.models.db.tenant import Tenant
    from keep.api.core.db import engine

    with Session(engine) as session:
        tenants = session.exec(select(Tenant.id)).all()
    return list(tenants)


def _run_auto_correlation_sync() -> None:
    """Synchronous entry point for auto-correlation, runs in thread pool."""
    from keep.api.bl.correlation_service import get_correlation_settings, run_correlation

    tenant_ids = _get_all_tenant_ids()
    if not tenant_ids:
        logger.debug("No tenants found, skipping auto-correlation")
        return

    for tenant_id in tenant_ids:
        try:
            settings = get_correlation_settings(tenant_id)

            if not settings.get("auto_correlation"):
                continue

            if not settings.get("enabled"):
                continue

            logger.info(f"Running auto-correlation for tenant {tenant_id}")
            result = run_correlation(tenant_id=tenant_id)

            if result.status == "success":
                logger.info(
                    f"Auto-correlation completed for tenant {tenant_id}: "
                    f"{result.alerts_analyzed} alerts analyzed, "
                    f"{result.incidents_created} incidents created"
                )
            elif result.status in ("no_alerts", "disabled", "no_model"):
                logger.debug(
                    f"Auto-correlation skipped for tenant {tenant_id}: {result.message}"
                )
            else:
                logger.warning(
                    f"Auto-correlation issue for tenant {tenant_id}: "
                    f"status={result.status}, message={result.message}"
                )

        except Exception as e:
            logger.error(
                f"Auto-correlation failed for tenant {tenant_id}: {e}",
                exc_info=True,
            )


async def async_process_auto_correlation(ctx) -> None:
    """ARQ cron job entry point for auto-correlation.

    Iterates all tenants and runs correlation for those with
    Auto Correlation enabled.
    """
    import asyncio

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(ctx.get("pool"), _run_auto_correlation_sync)
