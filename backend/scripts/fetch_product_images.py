"""
Enriquecimiento de imágenes de productos via Open Food Facts.

Consulta la API pública de Open Food Facts para obtener image_front_url
de los productos que tienen EAN real (barcode numérico) pero image_url=NULL.

Uso:
    cd backend && source venv/bin/activate
    python scripts/fetch_product_images.py
    python scripts/fetch_product_images.py --dry-run
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from app.config.database import SessionLocal
from app.models.product import Product

OFF_URL  = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
DELAY    = 1.0


def fetch_image(barcode: str, session: requests.Session) -> str | None:
    """Consulta Open Food Facts. Retorna image_front_url o None."""
    try:
        r = session.get(OFF_URL.format(barcode=barcode), timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("status") == 1:
            return data.get("product", {}).get("image_front_url")
    except Exception:
        pass
    return None


def run(dry_run: bool = False) -> None:
    db = SessionLocal()
    http = requests.Session()
    http.headers["User-Agent"] = "ACuantoEsta/1.0 (github.com/AgustinLuconi/A_Cuanto_Esta)"

    try:
        # Productos con EAN real (sin guión bajo) y sin imagen
        candidates: list[Product] = (
            db.query(Product)
            .filter(Product.image_url.is_(None))
            .filter(Product.barcode.isnot(None))
            .filter(~Product.barcode.contains("_"))
            .all()
        )

        total     = len(candidates)
        found     = 0
        not_found = 0

        print("=== Enriquecimiento de imágenes — Open Food Facts ===")
        print(f"Productos con EAN sin imagen : {total}")
        if dry_run:
            print("(DRY RUN — no se guarda nada)\n")
        else:
            print()

        for product in candidates:
            image_url = fetch_image(product.barcode, http)
            time.sleep(DELAY)

            if image_url:
                found += 1
                print(f"  FOUND  {product.barcode:<14} | {product.name[:50]}")
                if not dry_run:
                    product.image_url = image_url
                    db.commit()
            else:
                not_found += 1

        total_with_image = (
            db.query(Product)
            .filter(Product.image_url.isnot(None))
            .count()
        )
        total_products = db.query(Product).count()
        coverage = total_with_image / total_products * 100 if total_products else 0

        print(f"\n=== Resumen ===")
        print(f"Procesados              : {total}")
        print(f"Imágenes encontradas    : {found}")
        print(f"Sin imagen en OFF       : {not_found}")
        if not dry_run:
            print(f"Cobertura total de BD   : {coverage:.1f}%  ({total_with_image}/{total_products})")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()
        http.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run(dry_run=dry_run)
