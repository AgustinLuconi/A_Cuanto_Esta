"""add_indec_indicator_to_key

Revision ID: b7a2c9e5d014
Revises: 8d3f1b6a9c41
Create Date: 2026-11-15
"""
from alembic import op
import sqlalchemy as sa

revision = 'b7a2c9e5d014'
down_revision = '8d3f1b6a9c41'
branch_labels = None
depends_on = None

_OLD_KEY = ['dataset', 'classifier', 'level', 'series_code', 'region', 'indicator_type', 'period']
_NEW_KEY = ['dataset', 'classifier', 'level', 'series_code', 'region', 'indicator', 'indicator_type', 'period']


def upgrade():
    # Los datasets ya cargados quedan con indicator = '' (no lo usan). El mayorista
    # lo necesita: IPP, IPIB e IPIM comparten códigos de serie.
    op.add_column(
        'indec_observations',
        sa.Column('indicator', sa.String(length=60), nullable=False, server_default=''),
    )
    op.drop_constraint('uq_indec_observation_key', 'indec_observations', type_='unique')
    op.create_unique_constraint('uq_indec_observation_key', 'indec_observations', _NEW_KEY)


def downgrade():
    op.drop_constraint('uq_indec_observation_key', 'indec_observations', type_='unique')
    op.create_unique_constraint('uq_indec_observation_key', 'indec_observations', _OLD_KEY)
    op.drop_column('indec_observations', 'indicator')
