"""feat: Add group_id to alert, incident, and workflow tables

Revision ID: c1d2e3f4g5h6
Revises: b1c2d3e4f5g7
Create Date: 2026-03-28 16:20:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c1d2e3f4g5h6"
down_revision = "b1c2d3e4f5g7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect

    import logging
    logger = logging.getLogger(__name__)

    conn = op.get_bind()
    inspector = sa_inspect(conn)

    # Add group_id to alert table
    alert_columns = [c["name"] for c in inspector.get_columns("alert")]
    if "group_id" not in alert_columns:
        op.add_column(
            "alert",
            sa.Column("group_id", sa.String(36), sa.ForeignKey("tenant_group.id"), nullable=True),
        )
        op.create_index("ix_alert_group_id", "alert", ["group_id"])
    else:
        logger.info("Column 'group_id' already exists in 'alert'")

    # Add group_id to incident table
    incident_columns = [c["name"] for c in inspector.get_columns("incident")]
    if "group_id" not in incident_columns:
        op.add_column(
            "incident",
            sa.Column("group_id", sa.String(36), sa.ForeignKey("tenant_group.id"), nullable=True),
        )
        op.create_index("ix_incident_group_id", "incident", ["group_id"])
    else:
        logger.info("Column 'group_id' already exists in 'incident'")

    # Add group_id to workflow table
    workflow_columns = [c["name"] for c in inspector.get_columns("workflow")]
    if "group_id" not in workflow_columns:
        op.add_column(
            "workflow",
            sa.Column("group_id", sa.String(36), sa.ForeignKey("tenant_group.id"), nullable=True),
        )
        op.create_index("ix_workflow_group_id", "workflow", ["group_id"])
    else:
        logger.info("Column 'group_id' already exists in 'workflow'")


def downgrade() -> None:
    op.drop_index("ix_workflow_group_id", "workflow")
    op.drop_column("workflow", "group_id")
    op.drop_index("ix_incident_group_id", "incident")
    op.drop_column("incident", "group_id")
    op.drop_index("ix_alert_group_id", "alert")
    op.drop_column("alert", "group_id")
