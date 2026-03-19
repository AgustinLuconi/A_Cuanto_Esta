"""add dolarapi to datasource enum

Revision ID: 0f616895f3d4
Revises: fb80705162b3
Create Date: 2026-03-18 22:33:41.623363

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0f616895f3d4'
down_revision = 'fb80705162b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLAlchemy serializa enums por nombre (uppercase), así que el valor en PG también va en uppercase.
    # IF NOT EXISTS previene error si ya fue aplicado manualmente.
    op.execute("ALTER TYPE datasource ADD VALUE IF NOT EXISTS 'DOLARAPI'")


def downgrade() -> None:
    # PostgreSQL no soporta DROP VALUE en enums — downgrade no disponible.
    pass
