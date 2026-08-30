"""
Backfill de re-keying para productos de Coto creados antes del fix de
is_real_barcode() en app/scrapers/coto.py.

Antes del fix, el SKU interno de 8 dígitos de Coto (ej. "00251876") pasaba
la regex de is_real_barcode() como si fuera un EAN real, así que Coto casi
nunca entraba al camino de alias/fuzzy matching y quedó aislado del resto
del catálogo (49 de 1.417 productos compartidos con otro supermercado).

Este script SOLO re-etiqueta los productos que hoy tienen precio exclusivo
de Coto: cambia su barcode al formato nuevo ("coto_<sku>") y crea el alias
de identidad correspondiente, para que el próximo scrape los reconozca sin
crear otro producto duplicado. No fusiona productos.

La fusión real de estos productos aislados con sus equivalentes en otros
supermercados (ej. "Leche La Serenísima 1L" de Coto con la misma leche de
Carrefour) requeriría un matcher más confiable que fuzz.token_sort_ratio +
umbral: se probó y, incluso con guardas de cantidad/sabor
(product_matcher._quantity_conflict / _variant_word_conflict), cerca de la
mitad de los matches propuestos fusionaban productos distintos (marcas
distintas, variantes "Zero" vs "Original", "Adultos" vs "Gatitos", aromas
sin cubrir por la lista de palabras). Necesita comparar atributos
estructurados (marca, sabor, formulación, tamaño) por separado en vez de
un score de similitud sobre el nombre completo — trabajo de diseño
aparte, no un fix rápido. Queda pendiente para otra sesión.

Uso:
    python scripts/backfill_coto_matching.py            # dry-run, no escribe nada
    python scripts/backfill_coto_matching.py --apply     # ejecuta de verdad
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func

from app.config.database import SessionLocal
from app.models.product import Product
from app.models.price_history import PriceHistory, Supermarket
from app.models.product_alias import ProductAlias, MatchType


def alias_key_for(product: Product) -> str:
    """Clave estable para alias_id — usa el barcode viejo si existe, sino el id."""
    if product.barcode:
        return f"coto_{product.barcode}"
    return f"coto_{product.id}"


def main(apply: bool):
    session = SessionLocal()
    try:
        coto_product_ids = {
            row[0]
            for row in session.query(PriceHistory.product_id)
            .filter(PriceHistory.supermarket == Supermarket.COTO)
            .distinct()
            .all()
        }
        print(f"Productos con precio de Coto: {len(coto_product_ids)}")

        isolated_ids = []
        for pid in coto_product_ids:
            sm_count = (
                session.query(func.count(func.distinct(PriceHistory.supermarket)))
                .filter(PriceHistory.product_id == pid)
                .scalar()
            )
            if sm_count == 1:
                isolated_ids.append(pid)

        print(f"Aislados (solo Coto, candidatos a re-key): {len(isolated_ids)}")
        print()

        rekeyed = 0
        already_migrated = 0

        for pid in isolated_ids:
            product = session.get(Product, pid)
            if product is None:
                continue
            if product.barcode and product.barcode.startswith("coto_"):
                already_migrated += 1
                continue

            rekeyed += 1
            new_barcode = alias_key_for(product)
            print(f"  REKEY  '{product.name[:55]:<55}' ({product.barcode}) -> {new_barcode}")
            if apply:
                session.add(ProductAlias(
                    alias_source="coto",
                    alias_id=new_barcode,
                    canonical_product_id=product.id,
                    match_type=MatchType.FUZZY,
                    confidence=1.0,
                ))
                product.barcode = new_barcode
                session.commit()

        print()
        print(f"Resumen: {rekeyed} re-keyed, {already_migrated} ya migrados en una corrida anterior")
        if not apply:
            print("(dry-run: no se escribió nada en la base — corré con --apply para ejecutar de verdad)")
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Ejecuta de verdad (por defecto es dry-run)")
    args = parser.parse_args()
    main(apply=args.apply)
