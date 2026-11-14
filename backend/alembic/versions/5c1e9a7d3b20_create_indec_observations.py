"""create_indec_observations

Revision ID: 5c1e9a7d3b20
Revises: 089f6eb41b51
Create Date: 2026-11-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '5c1e9a7d3b20'
down_revision = '089f6eb41b51'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'indec_observations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dataset', sa.String(length=80), nullable=False),
        sa.Column('classifier', sa.String(length=120), nullable=False),
        sa.Column('level', sa.String(length=60), nullable=False),
        sa.Column('series_code', sa.String(length=40), nullable=False),
        sa.Column('series_name', sa.Text(), nullable=False),
        sa.Column('region', sa.String(length=40), nullable=False),
        sa.Column('indicator_type', sa.String(length=60), nullable=False),
        sa.Column('unit', sa.Text(), nullable=True),
        sa.Column('period', sa.Date(), nullable=False),
        sa.Column('value', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'dataset', 'classifier', 'level', 'series_code',
            'region', 'indicator_type', 'period',
            name='uq_indec_observation_key',
        ),
    )
    op.create_index(
        'ix_indec_observation_lookup',
        'indec_observations',
        ['dataset', 'series_code', 'region', 'indicator_type', 'period'],
    )


def downgrade():
    op.drop_index('ix_indec_observation_lookup', table_name='indec_observations')
    op.drop_table('indec_observations')
