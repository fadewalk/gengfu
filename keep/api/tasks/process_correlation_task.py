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


async def auto_correlation_loop() -> None:
    """Asyncio background loop for auto-correlation.

    Runs independently of ARQ/Redis. Periodically checks all tenants
    and runs correlation for those with Auto Correlation enabled.
    Uses the per-tenant correlation_interval setting.

    Uses a file-based lock to ensure only one gunicorn worker runs
    the correlation loop, preventing duplicate work.
    """
    import asyncio
    import fcntl
    import os
    import tempfile

    from keep.api.core.db import engine

    # Wait for DB to be ready on startup
    for attempt in range(30):
        try:
            from sqlmodel import Session

            with Session(engine) as _:
                break
        except Exception:
            logger.info(f"Waiting for database... (attempt {attempt + 1})")
            await asyncio.sleep(2)

    # Default check interval: poll every 60 seconds to pick up interval changes
    POLL_INTERVAL = 60
    # Track last run time per tenant
    last_run: dict[str, float] = {}

    lock_path = os.path.join(tempfile.gettempdir(), "keep_auto_correlation.lock")

    try:
        lock_fd = open(lock_path, "w")
        # Try non-blocking lock: only one worker wins
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info(
            f"Auto-correlation background loop started (PID {os.getpid()} acquired lock)"
        )
    except (IOError, OSError):
        logger.info(
            f"Auto-correlation background loop skipped (PID {os.getpid()}, "
            f"another worker holds the lock)"
        )
        return

    try:
        while True:
            try:
                await asyncio.get_running_loop().run_in_executor(
                    None, _run_auto_correlation_tick, last_run
                )
            except Exception as e:
                logger.error(f"Auto-correlation tick failed: {e}", exc_info=True)

            await asyncio.sleep(POLL_INTERVAL)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def _run_auto_correlation_tick(last_run: dict[str, float]) -> None:
    """Single tick: check each tenant and run correlation if interval elapsed."""
    import time

    from keep.api.bl.correlation_service import get_correlation_settings, run_correlation

    now = time.time()
    tenant_ids = _get_all_tenant_ids()

    for tenant_id in tenant_ids:
        try:
            settings = get_correlation_settings(tenant_id)

            if not settings.get("auto_correlation") or not settings.get("enabled"):
                continue

            interval_sec = (settings.get("correlation_interval") or 15) * 60
            prev = last_run.get(tenant_id, 0)

            if now - prev < interval_sec:
                continue

            logger.info(f"Auto-correlation tick: running for tenant {tenant_id}")
            result = run_correlation(tenant_id=tenant_id)

            if result.status == "success":
                logger.info(
                    f"Auto-correlation completed for tenant {tenant_id}: "
                    f"{result.alerts_analyzed} alerts, "
                    f"{result.incidents_created} incidents created"
                )
            elif result.status in ("no_alerts", "disabled", "no_model"):
                logger.info(
                    f"Auto-correlation skipped for tenant {tenant_id}: "
                    f"status={result.status}, message={result.message}"
                )
            else:
                logger.warning(
                    f"Auto-correlation issue for tenant {tenant_id}: "
                    f"status={result.status}"
                )

            last_run[tenant_id] = now

        except Exception as e:
            logger.error(
                f"Auto-correlation tick failed for tenant {tenant_id}: {e}",
                exc_info=True,
            )
