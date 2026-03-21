"""add_chango_mas_to_supermarket_enum

Revision ID: 9b1c3d5e7f8a
Revises: 8a0b2c4d6e7f
Create Date: 2026-03-21
"""
from alembic import op

revision = '9b1c3d5e7f8a'
down_revision = '8a0b2c4d6e7f'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE supermarket ADD VALUE IF NOT EXISTS 'CHANGO_MAS'")


def downgrade():
    pass  # PostgreSQL no soporta DROP VALUE de un enum
