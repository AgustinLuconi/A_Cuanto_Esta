"""drop location fields from price_history

Revision ID: c29f9fcc3d77
Revises: d2e4f6a8b0c2
Create Date: 2026-09-06 20:37:40.182693

province/city/region/store_id (agregados en 8a0b2c4d6e7f) quedaron sin
consumidor: solo Átomo los escribía (siempre "mendoza"/"cuyo"/"Mendoza"), y
ningún endpoint ni el frontend los leía. La feature de cobertura geográfica
que iba a usarlos se investigó y se descartó (8 de 9 supermercados no
tienen variación de precio real por región) — ver memoria del proyecto,
sesión 2026-09-06.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c29f9fcc3d77'
down_revision = 'd2e4f6a8b0c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index('idx_price_region_supermarket', table_name='price_history')
    op.drop_index('idx_price_province_date', table_name='price_history')
    op.drop_column('price_history', 'store_id')
    op.drop_column('price_history', 'region')
    op.drop_column('price_history', 'city')
    op.drop_column('price_history', 'province')


def downgrade() -> None:
    op.add_column('price_history', sa.Column('province', sa.String(50), nullable=True))
    op.add_column('price_history', sa.Column('city', sa.String(100), nullable=True))
    op.add_column('price_history', sa.Column('region', sa.String(50), nullable=True))
    op.add_column('price_history', sa.Column('store_id', sa.String(100), nullable=True))

    op.create_index('idx_price_province_date', 'price_history', ['province', 'scraped_at'])
    op.create_index('idx_price_region_supermarket', 'price_history', ['region', 'supermarket'])
