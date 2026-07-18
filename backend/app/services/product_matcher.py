"""
Servicio de fuzzy matching para deduplicación de productos.
Usado por scrapers que no tienen EAN/barcode real (ej: La Anónima).
"""
from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.models.product import Product
from app.scrapers.utils.normalizer import normalize_name, normalize_product_name

_THRESHOLD = 85


def find_matching_product(
    name: str,
    brand: str | None,
    quantity: str | None,
    unit,
    db: Session,
) -> tuple[Product | None, float]:
    """
    Busca un producto canónico que corresponda a los datos dados.

    El pre-filtro ILIKE usa normalize_product_name (la misma normalización que la DB).
    El scoring usa normalize_name (normalización agresiva, guiones→espacios) para
    maximizar la precisión de fuzz.token_sort_ratio.

    Returns:
        (Product, confidence) si score >= 85, (None, 0.0) si no hay match suficiente.
        confidence es float entre 0.0 y 1.0.
    """
    name_norm = normalize_name(name)
    if not name_norm:
        return None, 0.0

    # Pre-filtro: usa la misma normalización que la columna products.normalized_name
    prefix = normalize_product_name(name)[:15]
    candidates: list[Product] = (
        db.query(Product)
        .filter(Product.normalized_name.ilike(f"%{prefix}%"))
        .limit(50)
        .all()
    )

    if not candidates:
        return None, 0.0

    best_product: Product | None = None
    best_score: float = 0.0

    brand_norm = normalize_name(brand) if brand else None
    qty_norm   = normalize_name(quantity) if quantity else None

    for c in candidates:
        base  = fuzz.token_sort_ratio(name_norm, normalize_name(c.normalized_name))
        bonus = 0
        if brand_norm and c.brand and normalize_name(c.brand) == brand_norm:
            bonus += 5
        if qty_norm and c.quantity and normalize_name(c.quantity) == qty_norm:
            bonus += 5
        score = min(base + bonus, 100)
        if score > best_score:
            best_score, best_product = score, c

    if best_score >= _THRESHOLD:
        return best_product, best_score / 100.0

    return None, 0.0
