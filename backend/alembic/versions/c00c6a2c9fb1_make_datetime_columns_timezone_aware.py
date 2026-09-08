"""make datetime columns timezone-aware

Revision ID: c00c6a2c9fb1
Revises: c29f9fcc3d77
Create Date: 2026-09-07 23:20:48.169115

Todas las columnas DateTime del proyecto eran naive (sin timezone=True),
pero se escribían siempre en UTC (datetime.utcnow() / utcnow_naive()). Esta
migración las convierte a timestamptz interpretando los valores existentes
como UTC (`AT TIME ZONE 'UTC'`), sin perder ni alterar ningún dato — solo
etiqueta explícitamente lo que ya era cierto implícitamente. A partir de
acá, el código usa datetime.now(timezone.utc) (utils.time.utcnow_aware)
en vez de mezclar naive y aware.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c00c6a2c9fb1'
down_revision = 'c29f9fcc3d77'
branch_labels = None
depends_on = None

_COLUMNS = [
    ("price_history", "scraped_at"),
    ("price_history", "created_at"),
    ("products", "created_at"),
    ("products", "updated_at"),
    ("product_aliases", "created_at"),
    ("economic_indicators", "created_at"),
    ("economic_indicators", "updated_at"),
]


def upgrade() -> None:
    for table, column in _COLUMNS:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN {column} '
            f"TYPE timestamptz USING {column} AT TIME ZONE 'UTC'"
        )


def downgrade() -> None:
    for table, column in _COLUMNS:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN {column} '
            f"TYPE timestamp USING {column} AT TIME ZONE 'UTC'"
        )
