import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import JSON, TEXT, Column, Field, Index, Relationship, SQLModel

from keep.api.models.db.tenant import Tenant


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class IncidentReport(SQLModel, table=True):
    __tablename__ = "incident_report"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: str = Field(foreign_key="tenant.id", index=True)
    tenant: Tenant = Relationship()

    # Report name/description
    name: str = Field(default="", sa_column=Column(TEXT))

    # Status tracking
    status: str = Field(
        default=ReportStatus.PENDING.value,
        sa_column=Column(TEXT),
    )

    # Filter criteria used to generate the report
    filter_cel: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    # Specific incident IDs (when generating for selected incidents)
    incident_ids: Optional[list[str]] = Field(
        default=None, sa_column=Column(JSON)
    )

    # Result stored when completed
    result: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Error message if failed
    error: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)

    # User who created the report
    created_by: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    __table_args__ = (
        Index("ix_incident_report_tenant_created", "tenant_id", "created_at"),
        Index("ix_incident_report_status", "status"),
    )
