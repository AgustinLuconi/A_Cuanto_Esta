"""add atomo to supermarket enum

Revision ID: 2a4b6c8d0e1f
Revises: 0f616895f3d4
Create Date: 2026-03-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2a4b6c8d0e1f'
down_revision = '0f616895f3d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLAlchemy serializa enums por nombre (uppercase), así que el valor en PG es 'ATOMO'.
    # IF NOT EXISTS previene error si ya fue aplicado manualmente.
    op.execute("ALTER TYPE supermarket ADD VALUE IF NOT EXISTS 'ATOMO'")


def downgrade() -> None:
    # PostgreSQL no soporta DROP VALUE en enums — downgrade no disponible.
    pass
