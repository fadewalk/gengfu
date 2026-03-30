"""add group_id to rule, alertdeduplicationrule, extractionrule, mappingrule, maintenancewindowrule

Revision ID: e3f4g5h6i7j8
Revises: d2e3f4g5h6i7
Create Date: 2026-03-30 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "e3f4g5h6i7j8"
down_revision = "d2e3f4g5h6i7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table("rule", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.String(), nullable=True))
        batch_op.create_index("ix_rule_group_id", ["group_id"])

    with op.batch_alter_table("alertdeduplicationrule", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.String(), nullable=True))
        batch_op.create_index("ix_alertdeduplicationrule_group_id", ["group_id"])

    with op.batch_alter_table("extractionrule", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.String(), nullable=True))
        batch_op.create_index("ix_extractionrule_group_id", ["group_id"])

    with op.batch_alter_table("mappingrule", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.String(), nullable=True))
        batch_op.create_index("ix_mappingrule_group_id", ["group_id"])

    with op.batch_alter_table("maintenancewindowrule", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.String(), nullable=True))
        batch_op.create_index("ix_maintenancewindowrule_group_id", ["group_id"])


def downgrade() -> None:
    with op.batch_alter_table("maintenancewindowrule", schema=None) as batch_op:
        batch_op.drop_index("ix_maintenancewindowrule_group_id")
        batch_op.drop_column("group_id")

    with op.batch_alter_table("mappingrule", schema=None) as batch_op:
        batch_op.drop_index("ix_mappingrule_group_id")
        batch_op.drop_column("group_id")

    with op.batch_alter_table("extractionrule", schema=None) as batch_op:
        batch_op.drop_index("ix_extractionrule_group_id")
        batch_op.drop_column("group_id")

    with op.batch_alter_table("alertdeduplicationrule", schema=None) as batch_op:
        batch_op.drop_index("ix_alertdeduplicationrule_group_id")
        batch_op.drop_column("group_id")

    with op.batch_alter_table("rule", schema=None) as batch_op:
        batch_op.drop_index("ix_rule_group_id")
        batch_op.drop_column("group_id")
