"""add group_id to topology service and topology application

Revision ID: h6i7j8k9l0m1
Revises: g5h6i7j8k9l0
Create Date: 2026-03-30 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "h6i7j8k9l0m1"
down_revision = "g5h6i7j8k9l0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("topologyservice", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.String(), nullable=True))
        batch_op.create_index("ix_topologyservice_group_id", ["group_id"])

    with op.batch_alter_table("topologyapplication", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.String(), nullable=True))
        batch_op.create_index("ix_topologyapplication_group_id", ["group_id"])


def downgrade() -> None:
    with op.batch_alter_table("topologyapplication", schema=None) as batch_op:
        batch_op.drop_index("ix_topologyapplication_group_id")
        batch_op.drop_column("group_id")

    with op.batch_alter_table("topologyservice", schema=None) as batch_op:
        batch_op.drop_index("ix_topologyservice_group_id")
        batch_op.drop_column("group_id")
