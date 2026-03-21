"""add_jumbo_to_supermarket_enum

Revision ID: 5d7e9f1a3b4c
Revises: 4c6d8e0f1a2b
Create Date: 2026-03-20
"""
from alembic import op

revision = '5d7e9f1a3b4c'
down_revision = '4c6d8e0f1a2b'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE supermarket ADD VALUE IF NOT EXISTS 'JUMBO'")


def downgrade():
    pass  # PostgreSQL no soporta DROP VALUE de un enum
