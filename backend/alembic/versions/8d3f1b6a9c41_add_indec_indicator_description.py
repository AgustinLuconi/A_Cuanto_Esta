"""add_indec_indicator_description

Revision ID: 8d3f1b6a9c41
Revises: 5c1e9a7d3b20
Create Date: 2026-11-14
"""
from alembic import op
import sqlalchemy as sa

revision = '8d3f1b6a9c41'
down_revision = '5c1e9a7d3b20'
branch_labels = None
depends_on = None


def upgrade():
    # Unidad de referencia de los precios promedio ("Valor por 390 g"). Nullable:
    # las filas ya cargadas se completan corriendo `fetch_indec_data.py --full`.
    op.add_column('indec_observations', sa.Column('indicator_description', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('indec_observations', 'indicator_description')
