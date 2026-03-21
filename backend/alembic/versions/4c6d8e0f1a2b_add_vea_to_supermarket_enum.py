"""add vea to supermarket enum

Revision ID: 4c6d8e0f1a2b
Revises: 2a4b6c8d0e1f
Create Date: 2026-03-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4c6d8e0f1a2b'
down_revision = '2a4b6c8d0e1f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLAlchemy serializa enums por nombre (uppercase), así que el valor en PG es 'VEA'.
    # IF NOT EXISTS previene error si ya fue aplicado manualmente.
    op.execute("ALTER TYPE supermarket ADD VALUE IF NOT EXISTS 'VEA'")


def downgrade() -> None:
    # PostgreSQL no soporta DROP VALUE en enums — downgrade no disponible.
    pass
