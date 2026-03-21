"""Add location fields to price_history

Revision ID: 8a0b2c4d6e7f
Revises: 7f9a1b3c5e6d
Create Date: 2026-03-21

Agrega province, city, region, store_id a price_history para soportar
diferenciación geográfica de precios. Backfill Átomo → mendoza/cuyo.
"""
from alembic import op
import sqlalchemy as sa

revision = '8a0b2c4d6e7f'
down_revision = '7f9a1b3c5e6d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('price_history', sa.Column('province', sa.String(50), nullable=True))
    op.add_column('price_history', sa.Column('city', sa.String(100), nullable=True))
    op.add_column('price_history', sa.Column('region', sa.String(50), nullable=True))
    op.add_column('price_history', sa.Column('store_id', sa.String(100), nullable=True))

    op.create_index('idx_price_province_date', 'price_history', ['province', 'scraped_at'])
    op.create_index('idx_price_region_supermarket', 'price_history', ['region', 'supermarket'])

    # Backfill: Átomo opera exclusivamente en Mendoza, Cuyo
    op.execute("UPDATE price_history SET province = 'mendoza', region = 'cuyo', city = 'Mendoza' WHERE supermarket = 'ATOMO'")


def downgrade():
    op.drop_index('idx_price_region_supermarket', table_name='price_history')
    op.drop_index('idx_price_province_date', table_name='price_history')
    op.drop_column('price_history', 'store_id')
    op.drop_column('price_history', 'region')
    op.drop_column('price_history', 'city')
    op.drop_column('price_history', 'province')
