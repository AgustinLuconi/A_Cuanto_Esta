"""
Análisis (solo lectura, no escribe nada) de un matcher de productos más
estricto que el fuzzy-score original: exige marca exacta (cuando ambos
lados la tienen), mismas categorías, sin conflicto de cantidad numérica
extraída del nombre, y compara el conjunto de tokens "significativos"
(nombre normalizado menos marca menos stopwords de empaque menos números)
por similitud de Jaccard en vez de un score de caracteres.

Uso:
    python scripts/analyze_coto_matching_v2.py [--sample N] [--jaccard-min X]

Imprime, para una muestra de productos aislados de Coto, el mejor candidato
de fusión encontrado en el resto del catálogo junto con el desglose de
señales (marca, cantidad, jaccard) para revisión manual — no aplica nada.
"""
import argparse
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func

from app.config.database import SessionLocal
from app.models.product import Product
from app.models.price_history import PriceHistory, Supermarket
from app.scrapers.utils.normalizer import normalize_name

_NUMERIC_TOKEN_RE = re.compile(r"\d+[.,]?\d*")

# OJO: "con"/"sin"/"no" quedan afuera a propósito — son negaciones reales
# ("sin azúcar" vs "con azúcar" son productos OPUESTOS), no ruido de empaque.
_PACKAGING_STOPWORDS = {
    "x", "un", "de", "la", "el", "los", "las", "y", "en", "del",
    "bot", "botella", "pack", "caja", "bolsa", "sobre", "lata", "frasco", "sachet",
    "ml", "mls", "lt", "ltr", "ltrs", "kg", "kgs", "grs", "gr", "g", "l", "cc",
    "u", "uni", "unid", "unidad", "unidades", "cja", "doy", "pouch", "tapa", "rosca",
}


def split_number_unit(text: str) -> str:
    """'750ml' y '750 ml' deben tokenizar igual — separa dígito pegado a letra."""
    text = re.sub(r"(\d)([a-z])", r"\1 \2", text)
    text = re.sub(r"([a-z])(\d)", r"\1 \2", text)
    return text


def numeric_tokens(text: str) -> set[str]:
    return {t.replace(",", ".") for t in _NUMERIC_TOKEN_RE.findall(text)}


def significant_tokens(name_norm: str, brand_norm: str | None) -> set[str]:
    tokens = set(split_number_unit(name_norm).split())
    if brand_norm:
        tokens -= set(brand_norm.split())
    tokens -= _PACKAGING_STOPWORDS
    tokens = {t for t in tokens if not _NUMERIC_TOKEN_RE.fullmatch(t)}
    return tokens


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def main(sample_size: int, jaccard_min: float, seed: int):
    db = SessionLocal()
    try:
        coto_ids = {
            r[0] for r in db.query(PriceHistory.product_id)
            .filter(PriceHistory.supermarket == Supermarket.COTO)
            .distinct().all()
        }
        isolated_ids = []
        for pid in coto_ids:
            sm_count = (
                db.query(func.count(func.distinct(PriceHistory.supermarket)))
                .filter(PriceHistory.product_id == pid).scalar()
            )
            if sm_count == 1:
                isolated_ids.append(pid)

        print(f"Productos aislados de Coto: {len(isolated_ids)}")
        random.seed(seed)
        sample_ids = random.sample(isolated_ids, min(sample_size, len(isolated_ids)))

        found = 0
        for pid in sample_ids:
            p = db.get(Product, pid)
            if p is None:
                continue

            name_norm = normalize_name(p.normalized_name)
            brand_norm = normalize_name(p.brand) if p.brand else None
            nums = numeric_tokens(name_norm)
            sig = significant_tokens(name_norm, brand_norm)

            prefix = p.normalized_name[:15]
            candidates = (
                db.query(Product)
                .filter(
                    Product.normalized_name.ilike(f"%{prefix}%"),
                    Product.category == p.category,
                    Product.id != p.id,
                    ~Product.id.in_(isolated_ids),  # solo comparar contra productos YA compartidos (no otro aislado de coto)
                )
                .limit(80)
                .all()
            )

            best = None
            best_j = -1.0
            for c in candidates:
                c_name_norm = normalize_name(c.normalized_name)
                c_brand_norm = normalize_name(c.brand) if c.brand else None

                if brand_norm and c_brand_norm and brand_norm != c_brand_norm:
                    continue

                c_nums = numeric_tokens(c_name_norm)
                if nums and c_nums and nums != c_nums:
                    continue

                c_sig = significant_tokens(c_name_norm, c_brand_norm)
                j = jaccard(sig, c_sig)
                if j > best_j:
                    best_j, best = j, c

            if best is not None and best_j >= jaccard_min:
                found += 1
                print(f"\n[{found}] COTO: {p.name!r} (brand={p.brand!r}, qty={p.quantity!r})")
                print(f"     ->  {best.name!r} (brand={best.brand!r}, qty={best.quantity!r})")
                print(f"     jaccard={best_j:.2f}  coto_sig={sorted(sig)}  other_sig={sorted(significant_tokens(normalize_name(best.normalized_name), normalize_name(best.brand) if best.brand else None))}")

        print(f"\nTotal con candidato >= jaccard {jaccard_min}: {found} / {len(sample_ids)} muestreados")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=60)
    parser.add_argument("--jaccard-min", type=float, default=0.6)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    main(args.sample, args.jaccard_min, args.seed)
