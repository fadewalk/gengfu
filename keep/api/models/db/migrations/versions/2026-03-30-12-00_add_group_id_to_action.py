"""add group_id to action

Revision ID: g5h6i7j8k9l0
Revises: f4g5h6i7j8k9
Create Date: 2026-03-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "g5h6i7j8k9l0"
down_revision = "f4g5h6i7j8k9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("action", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.String(), nullable=True))
        batch_op.create_index("ix_action_group_id", ["group_id"])


def downgrade() -> None:
    with op.batch_alter_table("action", schema=None) as batch_op:
        batch_op.drop_index("ix_action_group_id")
        batch_op.drop_column("group_id")
