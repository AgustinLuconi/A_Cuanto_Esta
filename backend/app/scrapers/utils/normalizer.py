"""
Funciones de normalización de productos para el scraper.
Mapean datos crudos de APIs/HTML a los enums y formatos de la DB.
"""
import re
import unicodedata

from app.models.product import ProductCategory, ProductUnit


# Mapeo de categorías de Coto → ProductCategory
# Se busca coincidencia en el path_list de los grupos (de más general a más específico)
_CATEGORY_MAP: dict[str, ProductCategory] = {
    "lácteos": ProductCategory.LACTEOS,
    "lacteos": ProductCategory.LACTEOS,
    "leches": ProductCategory.LACTEOS,
    "bebidas": ProductCategory.BEBIDAS,
    "aguas": ProductCategory.BEBIDAS,
    "jugos": ProductCategory.BEBIDAS,
    "gaseosas": ProductCategory.BEBIDAS,
    "cervezas": ProductCategory.BEBIDAS,
    "vinos": ProductCategory.BEBIDAS,
    "limpieza": ProductCategory.LIMPIEZA,
    "higiene personal": ProductCategory.HIGIENE_PERSONAL,
    "higiene": ProductCategory.HIGIENE_PERSONAL,
    "cuidado personal": ProductCategory.HIGIENE_PERSONAL,
    "carnes": ProductCategory.CARNES,
    "aves": ProductCategory.CARNES,
    "pescados": ProductCategory.CARNES,
    "frutas": ProductCategory.FRUTAS_VERDURAS,
    "verduras": ProductCategory.FRUTAS_VERDURAS,
    "frutas y verduras": ProductCategory.FRUTAS_VERDURAS,
    "panadería": ProductCategory.PANADERIA,
    "panaderia": ProductCategory.PANADERIA,
    "congelados": ProductCategory.CONGELADOS,
    "snacks": ProductCategory.SNACKS,
    "golosinas": ProductCategory.SNACKS,
    "desayuno": ProductCategory.DESAYUNO,
    "desayuno y merienda": ProductCategory.DESAYUNO,
    "cereales": ProductCategory.DESAYUNO,
    "alimentos": ProductCategory.ALIMENTOS,
    "aceites": ProductCategory.ALIMENTOS,
    "harinas": ProductCategory.ALIMENTOS,
    "pastas": ProductCategory.ALIMENTOS,
    "conservas": ProductCategory.ALIMENTOS,
    # Categorías específicas de VTEX Carrefour
    "almacen": ProductCategory.ALIMENTOS,
    "almacén": ProductCategory.ALIMENTOS,
    "desayuno y merienda": ProductCategory.DESAYUNO,
    "panificacion": ProductCategory.PANADERIA,
    "panificación": ProductCategory.PANADERIA,
}

# Mapeo de formato de Coto → ProductUnit
_UNIT_MAP: dict[str, ProductUnit] = {
    "litro": ProductUnit.L,
    "litros": ProductUnit.L,
    "mililitro": ProductUnit.ML,
    "mililitros": ProductUnit.ML,
    "kilogramo": ProductUnit.KG,
    "kilogramos": ProductUnit.KG,
    "kilo": ProductUnit.KG,
    "gramo": ProductUnit.G,
    "gramos": ProductUnit.G,
    "unidad": ProductUnit.UNIDAD,
    "unidades": ProductUnit.UNIDAD,
    "uni": ProductUnit.UNIDAD,
    "pack": ProductUnit.PACK,
}

# Abreviaciones para build_quantity_str
_FORMAT_ABBR: dict[str, str] = {
    "Litro": "L",
    "Litros": "L",
    "Mililitro": "ml",
    "Mililitros": "ml",
    "Kilogramo": "kg",
    "Kilogramos": "kg",
    "Gramo": "g",
    "Gramos": "g",
    "Unidad": "un",
    "Unidades": "un",
    "Pack": "pack",
}


def normalize_product_name(name: str) -> str:
    """Normaliza un nombre de producto para búsquedas: lowercase, sin acentos, sin espacios extra."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_name.lower()).strip()


def normalize_name(text: str) -> str:
    """Normalización agresiva para fuzzy matching: además reemplaza guiones, comas y puntos por espacios."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"[-,.]", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def map_category(groups: list[dict]) -> ProductCategory:
    """
    Mapea los grupos de Coto (Constructor.io) a ProductCategory.
    Itera el path_list de cada grupo buscando la primera coincidencia.
    """
    for group in groups:
        for path_entry in group.get("path_list", []):
            display = path_entry.get("display_name", "").lower()
            if display in _CATEGORY_MAP:
                return _CATEGORY_MAP[display]
        # También intentar con el display_name del grupo directamente
        group_display = group.get("display_name", "").lower()
        if group_display in _CATEGORY_MAP:
            return _CATEGORY_MAP[group_display]
    return ProductCategory.OTROS


def map_unit(product_format: str, unit_of_measure: str = "") -> ProductUnit:
    """
    Mapea el formato de Coto a ProductUnit.
    Intenta product_format primero, luego unit_of_measure como fallback.
    """
    for candidate in [product_format, unit_of_measure]:
        if candidate:
            mapped = _UNIT_MAP.get(candidate.lower())
            if mapped:
                return mapped
    return ProductUnit.UNIDAD


def parse_discount_price(price_str: str) -> float | None:
    """Convierte "$1898.97" o "$ 1.898,97" → float."""
    if not price_str:
        return None
    cleaned = re.sub(r"[^\d.,]", "", price_str)
    # Maneja tanto "1898.97" como "1.898,97"
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def build_quantity_str(qty: float, product_format: str) -> str:
    """
    Construye string de cantidad legible.
    Ej: 1.0, "Litro" → "1L" | 900.0, "Gramo" → "900g"
    """
    abbr = _FORMAT_ABBR.get(product_format, "")
    qty_str = f"{qty:g}"  # elimina trailing zeros: 1.0→"1", 0.9→"0.9"
    return f"{qty_str}{abbr}" if abbr else qty_str
