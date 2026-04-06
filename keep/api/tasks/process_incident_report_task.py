import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from arq import Retry
from sqlmodel import Session

from keep.api.bl.incident_reports import IncidentReportsBl
from keep.api.core.db import engine
from keep.api.models.db.incident_report import IncidentReport, ReportStatus

TIMES_TO_RETRY_JOB = 3
logger = logging.getLogger(__name__)


def process_incident_report(
    ctx: dict,
    tenant_id: str,
    report_id: UUID,
    filter_cel: Optional[str] = None,
    incident_ids: Optional[list[str]] = None,
    allowed_incident_ids: Optional[list[str]] = None,
):
    extra = {
        "tenant_id": tenant_id,
        "report_id": str(report_id),
    }

    if ctx and isinstance(ctx, dict):
        extra["job_try"] = ctx.get("job_try", 0)
        extra["job_id"] = ctx.get("job_id", None)

    logger.info(f"Processing incident report: {report_id}", extra=extra)

    try:
        with Session(engine) as session:
            # Get the report record
            report = session.get(IncidentReport, report_id)
            if not report:
                logger.error(f"Report not found: {report_id}", extra=extra)
                return

            # Update status to processing (already pending from creation)
            report.status = ReportStatus.PENDING.value
            session.commit()

            # Generate the report
            reports_bl = IncidentReportsBl(tenant_id)
            result = reports_bl.get_incident_reports(
                incidents_query_cel=filter_cel or "true",
                allowed_incident_ids=allowed_incident_ids or [],
                incident_ids=incident_ids,
            )

            # Store the result — ensure JSON-serializable (convert any enum keys etc.)
            result_dict = result.model_dump() if hasattr(result, 'model_dump') else vars(result)
            report.result = json.loads(json.dumps(result_dict, default=str))
            report.status = ReportStatus.COMPLETED.value
            report.completed_at = datetime.utcnow()
            session.commit()

            logger.info(f"Completed incident report: {report_id}", extra=extra)

    except Exception as e:
        logger.exception(f"Error processing incident report: {report_id}", extra=extra)

        # Update status to failed
        try:
            with Session(engine) as session:
                report = session.get(IncidentReport, report_id)
                if report:
                    report.status = ReportStatus.FAILED.value
                    report.error = str(e)
                    report.completed_at = datetime.utcnow()
                    session.commit()
        except Exception:
            pass

        # Retrying only if context is present (running in arq worker)
        if bool(ctx):
            raise Retry(defer=ctx["job_try"] * TIMES_TO_RETRY_JOB)


async def async_process_incident_report(*args, **kwargs):
    return process_incident_report(*args, **kwargs)
