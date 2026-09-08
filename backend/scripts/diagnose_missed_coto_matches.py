"""
Diagnóstico (solo lectura): para una muestra de productos aislados de Coto
SIN candidato bajo find_strict_match_candidates, busca en TODO el catálogo
(sin el prefiltro ILIKE por prefijo) si existe algún producto con marca
idéntica y tokens significativos idénticos — para saber si el prefiltro por
prefijo de 15 caracteres está descartando matches reales por diferencias de
orden de palabras (ej. Coto pone la marca primero, el resto del catálogo
pone el tipo de producto primero).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func

from app.config.database import SessionLocal
from app.models.product import Product
from app.models.price_history import PriceHistory, Supermarket
from app.services.product_matcher import (
    find_strict_match_candidates,
    _significant_tokens,
    _numeric_tokens,
)
from app.scrapers.utils.normalizer import normalize_name


def main(sample_size: int, seed: int):
    db = SessionLocal()
    try:
        coto_ids = {
            r[0] for r in db.query(PriceHistory.product_id)
            .filter(PriceHistory.supermarket == Supermarket.COTO).distinct().all()
        }
        isolated_ids = [
            pid for pid in coto_ids
            if db.query(func.count(func.distinct(PriceHistory.supermarket)))
            .filter(PriceHistory.product_id == pid).scalar() == 1
        ]

        random.seed(seed)
        candidate_pool = random.sample(isolated_ids, min(sample_size * 3, len(isolated_ids)))

        found_without_prefilter = 0
        checked = 0
        for pid in candidate_pool:
            if checked >= sample_size:
                break
            p = db.get(Product, pid)
            if not p or not p.brand:
                continue
            if find_strict_match_candidates(p, db, exclude_ids=set(isolated_ids)):
                continue  # ya tiene candidato con el matcher normal, no es interesante para este diagnóstico
            checked += 1
            name_norm = normalize_name(p.normalized_name)
            brand_norm = normalize_name(p.brand)
            nums = _numeric_tokens(name_norm)
            sig = _significant_tokens(name_norm, brand_norm)

            # Búsqueda SIN prefiltro de prefijo: solo por categoría (para no escanear
            # las 6000+ filas del catálogo entero en este diagnóstico puntual).
            candidates = (
                db.query(Product)
                .filter(Product.category == p.category, Product.id != p.id)
                .filter(~Product.id.in_(isolated_ids))
                .all()
            )
            for c in candidates:
                if not c.brand or normalize_name(c.brand) != brand_norm:
                    continue
                c_name_norm = normalize_name(c.normalized_name)
                c_nums = _numeric_tokens(c_name_norm)
                if nums and c_nums and nums != c_nums:
                    continue
                c_sig = _significant_tokens(c_name_norm, brand_norm)
                if sig == c_sig:
                    found_without_prefilter += 1
                    print(f"  PERDIDO POR PREFIJO: '{p.name}' <-> '{c.name}'")
                    print(f"      prefijo coto: {p.normalized_name[:15]!r}  prefijo candidato: {c.normalized_name[:15]!r}")
                    break

        print(f"\nEncontrados sin prefiltro que el prefiltro normal no encuentra: {found_without_prefilter} / {checked} muestreados (sin candidato)")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=150)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    main(args.sample, args.seed)
