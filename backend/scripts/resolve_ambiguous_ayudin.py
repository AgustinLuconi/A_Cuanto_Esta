"""
Resuelve a mano los 2 casos que quedaron AMBIGUOS en
merge_coto_strict_matches.py: para "Lavandina Ayudín Floral/Lavanda 700ml"
había 2 candidatos porque el catálogo ya tenía un duplicado propio (un
producto aislado de Chango Más con un EAN real pero distinto al del
producto canónico — no es el bug de barcode falso de Coto, son códigos de
barra genuinos distintos para lo que es el mismo producto desde la
perspectiva de un comprador).

Para cada caso: fusiona el aislado de Chango Más Y el aislado de Coto,
ambos contra el mismo producto canónico ya compartido. Mismo mecanismo de
backup que merge_coto_strict_matches.py (ver ese script).

Uso:
    python scripts/resolve_ambiguous_ayudin.py            # dry-run
    python scripts/resolve_ambiguous_ayudin.py --apply     # ejecuta de verdad
"""
import argparse
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import SessionLocal
from app.models.product import Product
from app.models.price_history import PriceHistory
from app.models.product_alias import ProductAlias, MatchType
from app.utils.time import utcnow_naive

# (aislado_a_borrar, canonico) x 2 casos, cada uno con su fuente de alias (o None)
CASES = [
    {
        "isolated_id": "78621bd4-46eb-410d-adc0-084068a616ad",  # Chango Más, EAN real distinto
        "canonical_id": "2d3b6b66-2543-4ddd-9243-00a3b887b8c8",
        "alias_source": None,  # no tiene alias propio (llegó por EAN real, no por alias)
    },
    {
        "isolated_id": "6c2ec602-6704-4e66-a1fc-dd4694067159",  # Coto, ya re-keyed
        "canonical_id": "2d3b6b66-2543-4ddd-9243-00a3b887b8c8",
        "alias_source": "coto",
    },
    {
        "isolated_id": "f993d61d-cb15-449c-a7f1-eb0b6bb2c844",  # Chango Más, EAN real distinto
        "canonical_id": "c7a33c21-f757-4dd5-b97f-d35134a831f3",
        "alias_source": None,
    },
    {
        "isolated_id": "a600243d-853e-4441-aa2c-6e4d7770d401",  # Coto, ya re-keyed
        "canonical_id": "c7a33c21-f757-4dd5-b97f-d35134a831f3",
        "alias_source": "coto",
    },
]


def _snapshot(product, price_rows, alias):
    return {
        "product": {
            "id": str(product.id), "name": product.name, "normalized_name": product.normalized_name,
            "brand": product.brand, "category": product.category.value, "unit": product.unit.value,
            "quantity": product.quantity, "description": product.description,
            "image_url": product.image_url, "barcode": product.barcode,
        },
        "price_history_ids": [str(p.id) for p in price_rows],
        "alias": ({"id": str(alias.id), "alias_source": alias.alias_source, "alias_id": alias.alias_id} if alias else None),
    }


def main(apply: bool):
    session = SessionLocal()
    backup_entries = []
    try:
        for case in CASES:
            isolated_id = uuid.UUID(case["isolated_id"])
            canonical_id = uuid.UUID(case["canonical_id"])
            product = session.get(Product, isolated_id)
            canonical = session.get(Product, canonical_id)
            if product is None or canonical is None:
                print(f"  SKIP (ya no existe) {case}")
                continue

            print(f"  MERGE '{product.name}' (barcode={product.barcode}) -> '{canonical.name}' (id={canonical.id})")

            if apply:
                price_rows = session.query(PriceHistory).filter(PriceHistory.product_id == product.id).all()
                alias = None
                if case["alias_source"]:
                    alias = session.query(ProductAlias).filter_by(
                        alias_source=case["alias_source"], alias_id=product.barcode
                    ).first()
                backup_entries.append(_snapshot(product, price_rows, alias))

                session.query(PriceHistory).filter(PriceHistory.product_id == product.id).update(
                    {PriceHistory.product_id: canonical.id}
                )
                if alias:
                    alias.canonical_product_id = canonical.id
                    alias.match_type = MatchType.MANUAL
                elif case["alias_source"]:
                    session.add(ProductAlias(
                        alias_source=case["alias_source"], alias_id=product.barcode,
                        canonical_product_id=canonical.id, match_type=MatchType.MANUAL, confidence=1.0,
                    ))
                session.delete(product)
                session.commit()

        if not apply:
            print("(dry-run: no se escribió nada — corré con --apply para ejecutar de verdad)")
        else:
            backup_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                f"ayudin_merge_backup_{utcnow_naive().strftime('%Y%m%d_%H%M%S')}.json",
            )
            with open(backup_path, "w") as f:
                json.dump(backup_entries, f, ensure_ascii=False, indent=2)
            print(f"Backup escrito en: {backup_path}")
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    main(args.apply)
