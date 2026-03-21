"""add_la_anonima_to_supermarket_enum

Revision ID: 7f9a1b3c5e6d
Revises: 6e8f0a2b4c5d
Create Date: 2026-03-21
"""
from alembic import op

revision = '7f9a1b3c5e6d'
down_revision = '6e8f0a2b4c5d'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE supermarket ADD VALUE IF NOT EXISTS 'LA_ANONIMA'")


def downgrade():
    pass  # PostgreSQL no soporta DROP VALUE de un enum
