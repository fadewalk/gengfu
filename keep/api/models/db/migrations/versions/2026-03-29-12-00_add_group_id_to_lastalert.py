"""feat: Add group_id to lastalert table

Revision ID: d2e3f4g5h6i7
Revises: c1d2e3f4g5h6
Create Date: 2026-03-29 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d2e3f4g5h6i7"
down_revision = "c1d2e3f4g5h6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect

    import logging

    logger = logging.getLogger(__name__)

    conn = op.get_bind()
    inspector = sa_inspect(conn)

    lastalert_columns = [c["name"] for c in inspector.get_columns("lastalert")]
    if "group_id" not in lastalert_columns:
        op.add_column(
            "lastalert",
            sa.Column("group_id", sa.String(36), nullable=True),
        )
        op.create_index("ix_lastalert_group_id", "lastalert", ["group_id"])
    else:
        logger.info("Column 'group_id' already exists in 'lastalert'")

    # Backfill group_id from alert table
    op.execute(
        """
        UPDATE lastalert
        SET group_id = (
            SELECT a.group_id FROM alert a
            WHERE a.id = lastalert.alert_id
        )
        WHERE EXISTS (
            SELECT 1 FROM alert a
            WHERE a.id = lastalert.alert_id AND a.group_id IS NOT NULL
        )
    """
    )


def downgrade() -> None:
    op.drop_index("ix_lastalert_group_id", "lastalert")
    op.drop_column("lastalert", "group_id")
