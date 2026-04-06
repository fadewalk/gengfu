"""add incident_report table

Revision ID: h1a2i3d4r5e6
Revises: g2a3i4m5o6d7
Create Date: 2026-04-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

revision = "h1a2i3d4r5e6"
down_revision = "g2a3i4m5o6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = conn.inspector
    if "incident_report" not in inspector.get_table_names():
        op.create_table(
            "incident_report",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=256), nullable=False),
            sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=256), nullable=False),
            sa.Column("filter_cel", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("incident_ids", sa.JSON(), nullable=True),
            sa.Column("result", sa.JSON(), nullable=True),
            sa.Column("error", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.PrimaryKeyConstraint("id", name="pk_incident_report"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_incident_report_tenant", ondelete="CASCADE"),
        )
        op.create_index("ix_incident_report_tenant_created", "incident_report", ["tenant_id", "created_at"])
        op.create_index("ix_incident_report_status", "incident_report", ["status"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = conn.inspector
    if "incident_report" in inspector.get_table_names():
        op.drop_table("incident_report")