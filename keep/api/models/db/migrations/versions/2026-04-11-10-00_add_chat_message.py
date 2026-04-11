"""add chat_message table

Revision ID: c1h2a3t4m5s6g7
Revises: h1a2i3d4r5e6
Create Date: 2026-04-11 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

revision = "c1h2a3t4m5s6g7"
down_revision = "h1a2i3d4r5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = conn.inspector
    if "chat_message" not in inspector.get_table_names():
        op.create_table(
            "chat_message",
            sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=256), nullable=False),
            sa.Column("user_email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("session_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("role", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id", name="pk_chat_message"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_chat_message_tenant", ondelete="CASCADE"),
        )
        op.create_index("ix_chat_message_session_created", "chat_message", ["session_id", "created_at"])
        op.create_index("ix_chat_message_user_email", "chat_message", ["user_email"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = conn.inspector
    if "chat_message" in inspector.get_table_names():
        op.drop_table("chat_message")
