"""
Servicio de fuzzy matching para deduplicación de productos.
Usado por scrapers que no tienen EAN/barcode real (ej: La Anónima).
"""
import re

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.models.product import Product
from app.scrapers.utils.normalizer import normalize_name, normalize_product_name

_THRESHOLD = 85

_NUMERIC_TOKEN_RE = re.compile(r"\d+[.,]?\d*")


def _numeric_tokens(text: str) -> set[str]:
    """
    Extrae números del texto (coma decimal normalizada a punto) — proxy para
    detectar tamaños/cantidades/modelos distintos embebidos en el nombre
    (ej. "500 Ml" vs "2.25 L", "700g" vs "1100g").
    """
    return {t.replace(",", ".") for t in _NUMERIC_TOKEN_RE.findall(text)}


def _quantity_conflict(name_a: str, name_b: str) -> bool:
    """
    True si ambos nombres tienen números extraíbles y el conjunto NO
    coincide exactamente — señal fuerte de presentaciones/tamaños/modelos
    distintos, no el mismo producto, sin importar cuán similar sea el resto
    del texto. Si a alguno le falta un número extraíble, no hay señal
    suficiente para descartar por esta vía.
    """
    tokens_a = _numeric_tokens(name_a)
    tokens_b = _numeric_tokens(name_b)
    return bool(tokens_a) and bool(tokens_b) and tokens_a != tokens_b


# Palabras de sabor/aroma/variante que aparecen en pares mutuamente excluyentes
# en nombres de producto (un limpiador es "lavanda" O "limón", nunca ambos) —
# lo bastante parecidas entre sí como para no bajar mucho el fuzzy score, pero
# describen variantes distintas del mismo producto base. Lista acotada a los
# patrones observados, no exhaustiva.
_VARIANT_WORDS = {
    "limon", "lima", "naranja", "mandarina", "pomelo", "frutilla", "banana",
    "manzana", "durazno", "anana", "ananas", "uva", "cereza", "vainilla",
    "chocolate", "coco", "manzanilla", "menta", "mango", "maracuya",
    "lavanda", "jazmin", "floral", "marino", "brisa", "eucalipto",
}


def _variant_word_conflict(name_a: str, name_b: str) -> bool:
    """
    True si ambos nombres contienen alguna palabra de _VARIANT_WORDS y el
    conjunto encontrado NO coincide — señal de sabores/aromas distintos
    (ej. "Detergente ... Limón" vs "Detergente ... Lima") que el fuzzy score
    no penaliza lo suficiente porque el resto del nombre es casi idéntico.
    """
    words_a = {w for w in _VARIANT_WORDS if w in name_a}
    words_b = {w for w in _VARIANT_WORDS if w in name_b}
    return bool(words_a) and bool(words_b) and words_a != words_b


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

    Descarta candidatos cuyo nombre tenga números que no coincidan con los
    del producto buscado (ver _quantity_conflict) — evita fusionar
    presentaciones/tamaños distintos que igual puntúan alto por similitud
    de texto (ej. "Agua 500 Ml" con "Agua 2.25 L").

    Returns:
        (Product, confidence) si score >= 85, (None, 0.0) si no hay match suficiente.
        confidence es float entre 0.0 y 1.0.
    """
    name_norm = normalize_name(name)
    if not name_norm:
        return None, 0.0

    # Pre-filtro: usa la misma normalización que la columna products.normalized_name
    name_for_qty_check = normalize_product_name(name)
    prefix = name_for_qty_check[:15]
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
        if _quantity_conflict(name_for_qty_check, c.normalized_name):
            continue
        if _variant_word_conflict(name_for_qty_check, c.normalized_name):
            continue
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
