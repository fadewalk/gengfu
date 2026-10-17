"""merge gengfu custom migrations with upstream 0.54.3

Revision ID: 466878c0f7b5
Revises: c1h2a3t4m5s6g7, 67ff7efffed4
Create Date: 2026-10-17 13:12:32.438060

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
import sqlalchemy_utils



# revision identifiers, used by Alembic.
revision = '466878c0f7b5'
down_revision = ('c1h2a3t4m5s6g7', '67ff7efffed4')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
