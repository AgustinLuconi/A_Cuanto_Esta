"""
Consolidación retroactiva de productos La Anónima.

Resuelve duplicados existentes en la tabla products con barcode 'la_anonima_*'.
Para cada producto:
  - Si ya tiene alias → skip (idempotente).
  - Si hay fuzzy match ≥85% con otro producto: reasigna price_history al canónico,
    crea alias FUZZY y elimina el duplicado.
  - Si no hay match: crea alias FUZZY con confidence=1.0 apuntando a sí mismo.

Uso:
    cd backend && source venv/bin/activate
    python scripts/resolve_la_anonima_aliases.py
    python scripts/resolve_la_anonima_aliases.py --dry-run
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import SessionLocal
from app.models.product import Product
from app.models.price_history import PriceHistory
from app.models.product_alias import ProductAlias, MatchType
from app.services.product_matcher import find_matching_product


def resolve_aliases(dry_run: bool = False) -> None:
    db = SessionLocal()
    try:
        la_anonima_products: list[Product] = (
            db.query(Product)
            .filter(Product.barcode.like("la_anonima_%"))
            .all()
        )

        total        = len(la_anonima_products)
        already_done = 0
        matched      = 0
        self_aliased = 0

        print("=== Consolidación retroactiva La Anónima ===")
        print(f"Productos a procesar: {total}")
        if dry_run:
            print("(DRY RUN — no se guarda nada)\n")
        else:
            print()

        for product in la_anonima_products:
            barcode = product.barcode

            # Idempotencia: saltar si el alias ya existe
            existing = (
                db.query(ProductAlias)
                .filter_by(alias_source="la_anonima", alias_id=barcode)
                .first()
            )
            if existing:
                already_done += 1
                continue

            match, confidence = find_matching_product(
                name=product.name,
                brand=product.brand,
                quantity=product.quantity,
                unit=product.unit,
                db=db,
            )

            # Prevenir auto-match (el producto encontrándose a sí mismo)
            if match and match.id == product.id:
                match = None
                confidence = 0.0

            if match and confidence >= 0.85:
                print(
                    f"  MATCH  '{product.name[:50]}'\n"
                    f"       → '{match.name[:50]}' (conf={confidence:.2f})"
                )
                if not dry_run:
                    # Reasignar price_history ANTES de eliminar (evita cascade-delete)
                    db.query(PriceHistory).filter_by(product_id=product.id).update(
                        {"product_id": match.id}
                    )
                    db.flush()
                    db.add(ProductAlias(
                        alias_source="la_anonima",
                        alias_id=barcode,
                        canonical_product_id=match.id,
                        match_type=MatchType.FUZZY,
                        confidence=confidence,
                    ))
                    db.delete(product)
                    db.commit()
                matched += 1
            else:
                print(f"  SELF   '{product.name[:50]}' (sin match)")
                if not dry_run:
                    db.add(ProductAlias(
                        alias_source="la_anonima",
                        alias_id=barcode,
                        canonical_product_id=product.id,
                        match_type=MatchType.FUZZY,
                        confidence=1.0,
                    ))
                    db.commit()
                self_aliased += 1

        print(f"\n=== Resumen ===")
        print(f"Total procesados : {total}")
        print(f"Ya resueltos     : {already_done}")
        print(f"Matcheados       : {matched}")
        print(f"Self-aliased     : {self_aliased}")
        if not dry_run and (matched + self_aliased) > 0:
            overlap_pct = matched / (matched + self_aliased) * 100
            print(f"Overlap estimado : {overlap_pct:.1f}%")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    resolve_aliases(dry_run=dry_run)
