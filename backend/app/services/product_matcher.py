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


# ============================================================================
# Matcher estricto por atributos estructurados — para fusiones en batch
# (backfills), no para el scraping en vivo de find_matching_product.
#
# Se diseñó después de que el fuzzy-score original (arriba) fusionara ~50%
# de pares incorrectos en una prueba real contra el catálogo de Coto (marcas
# distintas, "Zero" vs "Original", "Adultos" vs "Gatitos"). En vez de subir
# el umbral de un score de similitud de caracteres, compara tres señales
# estructurales por separado y exige que las tres coincidan — no una más:
#   1. Categoría igual.
#   2. Marca idéntica (normalizada), cuando ambos productos la tienen.
#   3. El conjunto de "tokens significativos" (nombre normalizado menos
#      marca, menos números, menos palabras de empaque sin valor
#      discriminante) debe ser IDÉNTICO entre ambos — no una similitud
#      aproximada. Validado contra una muestra real: con esta exigencia
#      (jaccard == 1.0) la tasa de falsos positivos observada fue 0/19 en
#      una muestra manual; bajar la exigencia a partir de ahí (0.6–0.8)
#      dejó pasar pares reales de productos distintos ("Pasta Dental
#      Colgate Triple Beneficio" vs "...Triple Acción").
#
# "con"/"sin"/"no" se excluyen a propósito de las palabras de empaque: son
# negaciones reales ("sin azúcar" vs "con azúcar" son productos opuestos).
# ============================================================================

_PACKAGING_STOPWORDS = {
    "x", "un", "de", "la", "el", "los", "las", "y", "en", "del",
    "bot", "botella", "pack", "caja", "bolsa", "sobre", "lata", "frasco", "sachet",
    "ml", "mls", "lt", "ltr", "ltrs", "kg", "kgs", "grs", "gr", "g", "l", "cc",
    "u", "uni", "unid", "unidad", "unidades", "cja", "doy", "pouch", "tapa", "rosca",
}

_NUMBER_LETTER_RE = re.compile(r"(\d)([a-z])")
_LETTER_NUMBER_RE = re.compile(r"([a-z])(\d)")


def _split_number_unit(text: str) -> str:
    """'750ml' y '750 ml' deben tokenizar igual — separa dígito pegado a letra."""
    text = _NUMBER_LETTER_RE.sub(r"\1 \2", text)
    text = _LETTER_NUMBER_RE.sub(r"\1 \2", text)
    return text


def _significant_tokens(name_norm: str, brand_norm: str | None) -> set[str]:
    """Tokens del nombre que aportan identidad del producto: sin marca, sin
    números (se comparan aparte), sin relleno de empaque sin valor discriminante."""
    tokens = set(_split_number_unit(name_norm).split())
    if brand_norm:
        tokens -= set(brand_norm.split())
    tokens -= _PACKAGING_STOPWORDS
    return {t for t in tokens if not _NUMERIC_TOKEN_RE.fullmatch(t)}


def find_strict_match_candidates(
    product: Product,
    db: Session,
    exclude_ids: set | None = None,
) -> list[Product]:
    """
    Candidatos de fusión para `product` entre el resto del catálogo, exigiendo
    coincidencia estructural exacta (ver docstring del módulo más arriba) en
    vez de un score aproximado. Devuelve 0, 1 o más candidatos — más de uno
    significa ambigüedad real (ej. dos productos ya separados que
    accidentalmente comparten los mismos tokens) y debe tratarse como "no
    fusionar", no como "elegir el primero".

    No escribe nada en la base — solo lee. La decisión de aplicar una fusión
    queda en el llamador (script de backfill), con revisión humana de la
    lista antes de escribir.

    Exige que `product` tenga marca propia: si no la declara, no hay forma
    de verificar que el candidato (que puede aportar su propia marca vía
    fallback) sea realmente el mismo fabricante — visto en la práctica con
    "Leche Reducida en Lactosa Sachet 1l" (sin marca del lado de Coto)
    fusionándose con un producto La Serenísima sin poder confirmarlo.
    """
    if not product.brand:
        return []

    name_norm = normalize_name(product.normalized_name)
    brand_norm = normalize_name(product.brand)
    nums = _numeric_tokens(name_norm)
    sig = _significant_tokens(name_norm, brand_norm)

    # Sin prefiltro por prefijo de nombre: un prefijo de 15 caracteres se
    # rompe apenas el orden de las palabras difiere entre fuentes (ej. "Chocolate
    # Shot Con Maní" vs "Chocolate Con Maní Shot" — mismo producto, prefijo
    # distinto), y se confirmó en la práctica que eso descarta matches reales.
    # La categoría ya acota lo suficiente (cientos de filas, no miles); el
    # filtrado real lo hacen la marca, los números y los tokens exactos abajo.
    query = db.query(Product).filter(
        Product.category == product.category,
        Product.id != product.id,
    )
    if exclude_ids:
        query = query.filter(~Product.id.in_(exclude_ids))

    matches = []
    for c in query.all():
        c_name_norm = normalize_name(c.normalized_name)
        c_brand_norm = normalize_name(c.brand) if c.brand else None

        if brand_norm and c_brand_norm and brand_norm != c_brand_norm:
            continue

        c_nums = _numeric_tokens(c_name_norm)
        if nums and c_nums and nums != c_nums:
            continue

        # Si a un lado le falta la marca estructurada, usar la del otro lado
        # como fallback: si de verdad es el mismo producto, la marca suele
        # seguir apareciendo dentro del nombre aunque el campo quedó vacío.
        c_sig = _significant_tokens(c_name_norm, c_brand_norm or brand_norm)
        if sig == c_sig:
            matches.append(c)

    return matches
