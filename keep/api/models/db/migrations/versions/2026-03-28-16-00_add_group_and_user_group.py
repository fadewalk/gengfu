"""feat: Add Group and UserGroup tables for group-level data isolation

Revision ID: a1b2c3d4e5f6
Revises: 9dd1be4539e0
Create Date: 2026-03-28 16:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "9dd1be4539e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    import logging
    from sqlalchemy import inspect as sa_inspect

    logger = logging.getLogger(__name__)
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    existing_tables = inspector.get_table_names()

    if "tenant_group" not in existing_tables:
        op.create_table(
            "tenant_group",
            sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column(
                "tenant_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False
            ),
            sa.Column(
                "name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False
            ),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "created_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
            sa.UniqueConstraint("tenant_id", "name", name="uq_group_tenant_name"),
        )
        op.create_index("ix_tenant_group_tenant_id", "tenant_group", ["tenant_id"])
    else:
        logger.info("Table 'tenant_group' already exists, skipping creation")

    if "user_group" not in existing_tables:
        op.create_table(
            "user_group",
            sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column(
                "user_email", sqlmodel.sql.sqltypes.AutoString(), nullable=False
            ),
            sa.Column(
                "group_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False
            ),
            sa.Column(
                "role", sqlmodel.sql.sqltypes.AutoString(), nullable=False
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["group_id"], ["tenant_group.id"]),
            sa.UniqueConstraint("user_email", "group_id", name="uq_user_group"),
        )
        op.create_index("ix_user_group_user_email", "user_group", ["user_email"])
        op.create_index("ix_user_group_group_id", "user_group", ["group_id"])
    else:
        logger.info("Table 'user_group' already exists, skipping creation")


def downgrade() -> None:
    op.drop_table("user_group")
    op.drop_table("tenant_group")
