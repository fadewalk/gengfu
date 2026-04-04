"""add group_id to provider

Revision ID: f4g5h6i7j8k9
Revises: e3f4g5h6i7j8
Create Date: 2026-03-30 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "f4g5h6i7j8k9"
down_revision = "e3f4g5h6i7j8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("provider", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.String(), nullable=True))
        batch_op.create_index("ix_provider_group_id", ["group_id"])


def downgrade() -> None:
    with op.batch_alter_table("provider", schema=None) as batch_op:
        batch_op.drop_index("ix_provider_group_id")
        batch_op.drop_column("group_id")
