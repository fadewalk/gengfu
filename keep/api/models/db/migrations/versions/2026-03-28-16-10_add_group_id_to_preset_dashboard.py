"""feat: Add group_id to preset and dashboard tables

Revision ID: b1c2d3e4f5g7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-28 16:10:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5g7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    import sqlalchemy as sa
    from sqlalchemy import inspect as sa_inspect

    import logging
    logger = logging.getLogger(__name__)

    conn = op.get_bind()
    inspector = sa_inspect(conn)

    # Add group_id to preset table
    preset_columns = [c["name"] for c in inspector.get_columns("preset")]
    if "group_id" not in preset_columns:
        op.add_column(
            "preset",
            sa.Column("group_id", sa.String(36), sa.ForeignKey("tenant_group.id"), nullable=True),
        )
        op.create_index("ix_preset_group_id", "preset", ["group_id"])
    else:
        logger.info("Column 'group_id' already exists in 'preset',")

    # Add group_id to dashboard table
    dashboard_columns = [c["name"] for c in inspector.get_columns("dashboard")]
    if "group_id" not in dashboard_columns:
        op.add_column(
            "dashboard",
            sa.Column("group_id", sa.String(36), sa.ForeignKey("tenant_group.id"), nullable=True),
        )
        op.create_index("ix_dashboard_group_id", "dashboard", ["group_id"])
    else:
        logger.info("Column 'group_id' already exists in 'dashboard'")


def downgrade() -> None:
    op.drop_index("ix_dashboard_group_id", "dashboard")
    op.drop_column("dashboard", "group_id")
    op.drop_index("ix_preset_group_id", "preset")
    op.drop_column("preset", "group_id")
