"""
Fusiona productos aislados de Coto con su equivalente ya existente en el
resto del catálogo, usando el matcher estructural estricto
(app.services.product_matcher.find_strict_match_candidates) en vez del
fuzzy-score original — ver el docstring de ese módulo para el porqué y la
validación (34/34 candidatos correctos en dos muestras manuales
independientes con la exigencia jaccard==1.0 de tokens significativos, y
69/70 correctos en la revisión manual completa de la corrida real — el
caso restante llevó a agregar la exigencia de marca propia).

Para cada producto aislado de Coto (precio solo en Coto, ya re-keyed por
backfill_coto_matching.py):
  - 0 candidatos  -> se deja como está (sin match seguro).
  - 1 candidato   -> se fusiona: el precio histórico de Coto pasa al producto
                     canónico, el alias existente (coto_<sku> -> sí mismo) se
                     actualiza para apuntar al canónico, y el producto aislado
                     (ya sin precios ni alias propios) se borra.
  - 2+ candidatos -> AMBIGUO, no se fusiona (más de un producto ya separado
                     comparte los mismos tokens — tratar manualmente aparte).

Antes de escribir nada, con --apply, vuelca a un JSON el estado "antes" de
cada fusión (producto a borrar, sus price_history, su alias) para poder
deshacer con precisión sin depender de un branch de Neon.

Uso:
    python scripts/merge_coto_strict_matches.py             # dry-run, no escribe nada
    python scripts/merge_coto_strict_matches.py --apply      # ejecuta de verdad
    python scripts/merge_coto_strict_matches.py --limit 50   # probar con pocos primero
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func

from app.config.database import SessionLocal
from app.models.product import Product
from app.models.price_history import PriceHistory, Supermarket
from app.models.product_alias import ProductAlias, MatchType
from app.services.product_matcher import find_strict_match_candidates


def _snapshot(product: Product, price_rows: list[PriceHistory], alias: ProductAlias | None) -> dict:
    """Estado completo necesario para deshacer esta fusión."""
    return {
        "product": {
            "id": str(product.id),
            "name": product.name,
            "normalized_name": product.normalized_name,
            "brand": product.brand,
            "category": product.category.value,
            "unit": product.unit.value,
            "quantity": product.quantity,
            "description": product.description,
            "image_url": product.image_url,
            "barcode": product.barcode,
        },
        "price_history_ids": [str(p.id) for p in price_rows],
        "alias": (
            {"id": str(alias.id), "alias_source": alias.alias_source, "alias_id": alias.alias_id}
            if alias else None
        ),
    }


def main(apply: bool, limit: int | None):
    session = SessionLocal()
    backup_entries = []
    try:
        coto_ids = {
            row[0]
            for row in session.query(PriceHistory.product_id)
            .filter(PriceHistory.supermarket == Supermarket.COTO)
            .distinct()
            .all()
        }
        isolated_ids = [
            pid for pid in coto_ids
            if session.query(func.count(func.distinct(PriceHistory.supermarket)))
            .filter(PriceHistory.product_id == pid).scalar() == 1
        ]
        print(f"Productos aislados de Coto: {len(isolated_ids)}")
        if limit:
            isolated_ids = isolated_ids[:limit]
            print(f"(limitado a los primeros {limit} para esta corrida)")

        merged = 0
        ambiguous = 0
        no_match = 0

        for pid in isolated_ids:
            product = session.get(Product, pid)
            if product is None:
                continue

            candidates = find_strict_match_candidates(product, session, exclude_ids=set(isolated_ids))
            if len(candidates) == 0:
                no_match += 1
                continue
            if len(candidates) > 1:
                ambiguous += 1
                print(f"  AMBIGUO ({len(candidates)} candidatos) '{product.name[:60]}'")
                for c in candidates:
                    print(f"      - {c.name[:60]!r} (id={c.id})")
                continue

            canonical = candidates[0]
            merged += 1
            print(f"  MERGE  '{product.name[:55]:<55}' -> '{canonical.name[:55]}' (canonical={canonical.id})")

            if apply:
                price_rows = (
                    session.query(PriceHistory)
                    .filter(PriceHistory.product_id == product.id)
                    .all()
                )
                alias = (
                    session.query(ProductAlias)
                    .filter_by(alias_source="coto", alias_id=product.barcode)
                    .first()
                )
                backup_entries.append(_snapshot(product, price_rows, alias))

                # 1. Reasignar el historial de precios de Coto al producto canónico.
                (
                    session.query(PriceHistory)
                    .filter(PriceHistory.product_id == product.id)
                    .update({PriceHistory.product_id: canonical.id})
                )
                # 2. Actualizar el alias existente (creado por el rekey) para que
                #    apunte al canónico en vez de a sí mismo.
                if alias:
                    alias.canonical_product_id = canonical.id
                    alias.match_type = MatchType.FUZZY
                else:
                    session.add(ProductAlias(
                        alias_source="coto",
                        alias_id=product.barcode,
                        canonical_product_id=canonical.id,
                        match_type=MatchType.FUZZY,
                        confidence=1.0,
                    ))
                # 3. Borrar el producto aislado, ya sin precios ni alias propios.
                session.delete(product)
                session.commit()

        print()
        print(f"Resumen: {merged} fusionados, {ambiguous} ambiguos (sin tocar), {no_match} sin candidato (sin tocar)")
        if not apply:
            print("(dry-run: no se escribió nada en la base — corré con --apply para ejecutar de verdad)")
        else:
            backup_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                f"coto_merge_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
            )
            with open(backup_path, "w") as f:
                json.dump(backup_entries, f, ensure_ascii=False, indent=2)
            print(f"Backup de {len(backup_entries)} fusiones escrito en: {backup_path}")
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Ejecuta de verdad (por defecto es dry-run)")
    parser.add_argument("--limit", type=int, default=None, help="Procesar solo los primeros N aislados (para probar)")
    args = parser.parse_args()
    main(apply=args.apply, limit=args.limit)
