"""add_dollar_mayorista_cripto_tarjeta

Revision ID: d2e4f6a8b0c2
Revises: 7aadc53c1d48
Create Date: 2026-07-26
"""
from alembic import op

revision = 'd2e4f6a8b0c2'
down_revision = '7aadc53c1d48'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE indicatortype ADD VALUE IF NOT EXISTS 'DOLLAR_MAYORISTA'")
    op.execute("ALTER TYPE indicatortype ADD VALUE IF NOT EXISTS 'DOLLAR_CRIPTO'")
    op.execute("ALTER TYPE indicatortype ADD VALUE IF NOT EXISTS 'DOLLAR_TARJETA'")


def downgrade():
    pass  # PostgreSQL no soporta DROP VALUE de un enum
