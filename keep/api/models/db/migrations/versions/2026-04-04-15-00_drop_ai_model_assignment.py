"""drop unused ai_model_assignment table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-04 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("ai_model_assignment")


def downgrade() -> None:
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
