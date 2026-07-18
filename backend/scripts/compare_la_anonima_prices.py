"""
Compara precios viejos vs nuevos de La Anónima en la BD.

Old: registros scraped_at < CUTOFF (datos del 2026-03-21)
New: registros scraped_at >= CUTOFF (datos del re-scraping)

Uso:
    cd backend
    source venv/bin/activate
    python scripts/compare_la_anonima_prices.py
"""
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import and_, func, text
from app.config.database import SessionLocal
from app.models.price_history import PriceHistory, Supermarket
from app.models.product import Product
from app.scrapers.la_anonima import MIN_VALID_PRICE

CUTOFF = datetime(2026, 4, 1, tzinfo=timezone.utc)


def get_prices_around_cutoff(session):
    """Devuelve el precio de referencia old y new para cada producto.

    Usa MAX(price) sobre todo el período (no solo el último scraped_at) para
    evitar que un registro posterior con precio corrupto bajo tape a uno anterior
    con precio correcto más alto. Esto es robusto ante sesiones de scraping que
    insertan el mismo producto varias veces con distintos timestamps.
    """

    # old_price: el precio más alto registrado antes del corte
    old_prices = (
        session.query(
            PriceHistory.product_id,
            func.max(PriceHistory.price).label("old_price"),
        )
        .filter(
            PriceHistory.supermarket == Supermarket.LA_ANONIMA,
            PriceHistory.scraped_at < CUTOFF,
        )
        .group_by(PriceHistory.product_id)
        .subquery()
    )

    # new_price: el precio más alto registrado desde el corte
    new_prices = (
        session.query(
            PriceHistory.product_id,
            func.max(PriceHistory.price).label("new_price"),
        )
        .filter(
            PriceHistory.supermarket == Supermarket.LA_ANONIMA,
            PriceHistory.scraped_at >= CUTOFF,
        )
        .group_by(PriceHistory.product_id)
        .subquery()
    )

    # Join: productos con precio en AMBOS períodos
    rows = (
        session.query(
            Product.name,
            old_prices.c.old_price,
            new_prices.c.new_price,
        )
        .join(old_prices, Product.id == old_prices.c.product_id)
        .join(new_prices, Product.id == new_prices.c.product_id)
        .order_by(Product.name)
        .all()
    )
    return rows


def main():
    session = SessionLocal()
    try:
        # Resumen de registros en cada período
        old_count = (
            session.query(func.count(PriceHistory.id))
            .filter(
                PriceHistory.supermarket == Supermarket.LA_ANONIMA,
                PriceHistory.scraped_at < CUTOFF,
            )
            .scalar()
        )
        new_count = (
            session.query(func.count(PriceHistory.id))
            .filter(
                PriceHistory.supermarket == Supermarket.LA_ANONIMA,
                PriceHistory.scraped_at >= CUTOFF,
            )
            .scalar()
        )

        print(f"=== Comparación La Anónima (corte: {CUTOFF.date()}) ===")
        print(f"Registros old (antes del corte) : {old_count:,}")
        print(f"Registros new (desde el corte)  : {new_count:,}")

        if new_count == 0:
            print("\n⚠️  No hay datos nuevos — correr populate_la_anonima_products.py primero")
            return

        rows = get_prices_around_cutoff(session)
        print(f"Productos con precio en ambos períodos: {len(rows)}\n")

        if not rows:
            print("Sin productos en común para comparar.")
            return

        # Tabla de resultados
        header = f"{'Producto':<52} {'Old':>10} {'New':>10} {'Cambio':>8}  Flag"
        print(header)
        print("-" * len(header))

        flagged = []
        for name, old_price, new_price in rows:
            old_f = float(old_price)
            new_f = float(new_price)
            pct = (new_f - old_f) / old_f * 100 if old_f else 0
            flag = ""
            if new_f < MIN_VALID_PRICE:
                flag = "⚠️  PRECIO INVÁLIDO"
                flagged.append((name, old_f, new_f))
            elif old_f < MIN_VALID_PRICE:
                flag = "✅ OLD ERA INVÁLIDO"
            print(f"{name[:51]:<52} ${old_f:>9,.0f} ${new_f:>9,.0f} {pct:>+7.0f}%  {flag}")

        print()
        if flagged:
            print(f"⚠️  {len(flagged)} producto(s) con nuevo precio < ${MIN_VALID_PRICE:,.0f}:")
            for name, old_f, new_f in flagged:
                print(f"   {name[:55]} old=${old_f:,.0f} new=${new_f:,.0f}")
        else:
            print("✅ Todos los nuevos precios superan el mínimo válido.")

    finally:
        session.close()


if __name__ == "__main__":
    main()
