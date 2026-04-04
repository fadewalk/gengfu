"""add ai_model_config and ai_model_assignment tables

Revision ID: a1b2c3d4e5f6
Revises: h6i7j8k9l0m1
Create Date: 2026-04-01 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "h6i7j8k9l0m1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_model_config",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(256), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, server_default="openai_compatible"),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("api_key_secret", sa.String(200), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("fallback_models", sa.Text, nullable=True),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("extra_config", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_ai_model_config_tenant_name"),
    )

    op.create_table(
        "ai_model_assignment",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(256), nullable=False, index=True),
        sa.Column("scenario", sa.String(50), nullable=False),
        sa.Column("model_config_id", sa.String(36), sa.ForeignKey("ai_model_config.id", ondelete="CASCADE"), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "tenant_id", "scenario", "model_config_id",
            name="uq_ai_model_assignment_tenant_scenario_model",
        ),
    )


def downgrade() -> None:
    op.drop_table("ai_model_assignment")
    op.drop_table("ai_model_config")
