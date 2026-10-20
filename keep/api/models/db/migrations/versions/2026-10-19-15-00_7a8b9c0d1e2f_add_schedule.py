"""feat: add schedule and schedule_member tables for on-call rotation

Revision ID: 7a8b9c0d1e2f
Revises: 466878c0f7b5
Create Date: 2026-10-19 15:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "7a8b9c0d1e2f"
down_revision = "466878c0f7b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schedule",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=256), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=256), nullable=False),
        sa.Column("timezone", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False, server_default="Asia/Shanghai"),
        sa.Column("rotation_type", sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False, server_default="daily"),
        sa.Column("rotation_starts_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_schedule"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_schedule_tenant", ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_schedule_tenant_name"),
    )
    op.create_index("ix_schedule_tenant", "schedule", ["tenant_id"])

    op.create_table(
        "schedule_member",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=256), nullable=False),
        sa.Column("phone", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(length=256), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id", name="pk_schedule_member"),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedule.id"], name="fk_schedule_member_schedule", ondelete="CASCADE"),
    )
    op.create_index("ix_schedule_member_schedule_position", "schedule_member", ["schedule_id", "position"])


def downgrade() -> None:
    op.drop_table("schedule_member")
    op.drop_index("ix_schedule_tenant", table_name="schedule")
    op.drop_table("schedule")
