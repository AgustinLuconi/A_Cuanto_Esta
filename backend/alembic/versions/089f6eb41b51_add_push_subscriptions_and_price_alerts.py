"""add push subscriptions and price alerts

Revision ID: 089f6eb41b51
Revises: c00c6a2c9fb1
Create Date: 2026-09-09 16:28:01.976190

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '089f6eb41b51'
down_revision = 'c00c6a2c9fb1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'push_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('endpoint', sa.String(length=500), nullable=False),
        sa.Column('p256dh_key', sa.String(length=255), nullable=False),
        sa.Column('auth_key', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_push_subscriptions_endpoint'), 'push_subscriptions', ['endpoint'], unique=True)

    op.create_table(
        'price_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notified_at_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['subscription_id'], ['push_subscriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subscription_id', 'product_id', name='uq_subscription_product'),
    )
    op.create_index(op.f('ix_price_alerts_subscription_id'), 'price_alerts', ['subscription_id'], unique=False)
    op.create_index(op.f('ix_price_alerts_product_id'), 'price_alerts', ['product_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_price_alerts_product_id'), table_name='price_alerts')
    op.drop_index(op.f('ix_price_alerts_subscription_id'), table_name='price_alerts')
    op.drop_table('price_alerts')
    op.drop_index(op.f('ix_push_subscriptions_endpoint'), table_name='push_subscriptions')
    op.drop_table('push_subscriptions')
