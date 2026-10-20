"""feat: add ackrecord table for on-call claim tracking

Revision ID: 8b9c0d1e2f3a
Revises: 7a8b9c0d1e2f
Create Date: 2026-10-19 16:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "8b9c0d1e2f3a"
down_revision = "7a8b9c0d1e2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ackrecord",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=256), nullable=False),
        sa.Column("schedule_name", sqlmodel.sql.sqltypes.AutoString(length=256), nullable=False),
        sa.Column("alert_name", sqlmodel.sql.sqltypes.AutoString(length=512), nullable=False, server_default=""),
        sa.Column("notified_member_name", sqlmodel.sql.sqltypes.AutoString(length=256), nullable=False, server_default=""),
        sa.Column("notified_phone", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False, server_default=""),
        sa.Column("notified_email", sqlmodel.sql.sqltypes.AutoString(length=256), nullable=False, server_default=""),
        sa.Column("ack_token", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("acked_at", sa.DateTime(), nullable=True),
        sa.Column("acked_by", sqlmodel.sql.sqltypes.AutoString(length=256), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_ackrecord"),
    )
    op.create_index("ix_ackrecord_token", "ackrecord", ["ack_token"], unique=True)
    op.create_index("ix_ackrecord_tenant_created", "ackrecord", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_ackrecord_tenant_created", table_name="ackrecord")
    op.drop_index("ix_ackrecord_token", table_name="ackrecord")
    op.drop_table("ackrecord")
