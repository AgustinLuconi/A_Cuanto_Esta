"""
Deshace una corrida de merge_coto_strict_matches.py --apply usando el JSON
de backup que ese script escribe antes de tocar la base.

Por cada entrada del backup: recrea el Product original (mismo id), mueve
de vuelta los price_history (por id) a ese producto, y restaura el alias
a su estado original (apuntando a sí mismo).

Uso:
    python scripts/undo_coto_merge.py scripts/coto_merge_backup_XXXXXXXX.json            # dry-run
    python scripts/undo_coto_merge.py scripts/coto_merge_backup_XXXXXXXX.json --apply     # ejecuta de verdad
"""
import argparse
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import SessionLocal
from app.models.product import Product, ProductCategory, ProductUnit
from app.models.price_history import PriceHistory
from app.models.product_alias import ProductAlias, MatchType


def main(backup_path: str, apply: bool):
    with open(backup_path) as f:
        entries = json.load(f)
    print(f"{len(entries)} fusiones en el backup")

    session = SessionLocal()
    try:
        restored = 0
        for entry in entries:
            pdata = entry["product"]
            pid = uuid.UUID(pdata["id"])

            if session.get(Product, pid) is not None:
                print(f"  SKIP (ya existe) {pdata['name'][:60]!r}")
                continue

            print(f"  RESTORE {pdata['name'][:60]!r} ({len(entry['price_history_ids'])} precios)")
            if apply:
                product = Product(
                    id=pid,
                    name=pdata["name"],
                    normalized_name=pdata["normalized_name"],
                    brand=pdata["brand"],
                    category=ProductCategory(pdata["category"]),
                    unit=ProductUnit(pdata["unit"]),
                    quantity=pdata["quantity"],
                    description=pdata["description"],
                    image_url=pdata["image_url"],
                    barcode=pdata["barcode"],
                )
                session.add(product)
                session.flush()

                ph_ids = [uuid.UUID(x) for x in entry["price_history_ids"]]
                if ph_ids:
                    session.query(PriceHistory).filter(PriceHistory.id.in_(ph_ids)).update(
                        {PriceHistory.product_id: pid}, synchronize_session=False
                    )

                if entry["alias"]:
                    alias = session.get(ProductAlias, uuid.UUID(entry["alias"]["id"]))
                    if alias:
                        alias.canonical_product_id = pid
                        alias.match_type = MatchType.MANUAL
                    else:
                        session.add(ProductAlias(
                            id=uuid.UUID(entry["alias"]["id"]),
                            alias_source=entry["alias"]["alias_source"],
                            alias_id=entry["alias"]["alias_id"],
                            canonical_product_id=pid,
                            match_type=MatchType.MANUAL,
                            confidence=1.0,
                        ))
                session.commit()
            restored += 1

        print(f"\n{'Restaurados' if apply else 'A restaurar'}: {restored}")
        if not apply:
            print("(dry-run: no se escribió nada — corré con --apply para ejecutar de verdad)")
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("backup_path")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    main(args.backup_path, args.apply)
