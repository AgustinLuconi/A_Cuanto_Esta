"""add_dia_to_supermarket_enum

Revision ID: 6e8f0a2b4c5d
Revises: 5d7e9f1a3b4c
Create Date: 2026-03-21
"""
from alembic import op

revision = '6e8f0a2b4c5d'
down_revision = '5d7e9f1a3b4c'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE supermarket ADD VALUE IF NOT EXISTS 'DIA'")


def downgrade():
    pass  # PostgreSQL no soporta DROP VALUE de un enum
