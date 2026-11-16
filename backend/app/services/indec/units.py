"""
Convertidores de unidades para el cruce de precios INDEC vs. supermercados.

Dos entradas distintas, mismo resultado (`Size`, en unidades base):
- la descripción de referencia que publica el INDEC ("Valor por 390 g")
- el tamaño que figura en el nombre de un producto ("Azúcar La Campechana 1kg")

Unidades base: kg (masa), litro (volumen) y unidad (conteo).
"""
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

Kind = Literal["mass", "volume", "count"]


@dataclass(frozen=True)
class Size:
    kind: Kind
    amount: Decimal  # en kg, litros o unidades


# unidad escrita -> (tipo, factor a la unidad base)
_UNITS: dict[str, tuple[Kind, Decimal]] = {
    "kg": ("mass", Decimal("1")), "kgs": ("mass", Decimal("1")),
    "kilo": ("mass", Decimal("1")), "kilos": ("mass", Decimal("1")),
    "g": ("mass", Decimal("0.001")), "gr": ("mass", Decimal("0.001")),
    "grs": ("mass", Decimal("0.001")), "gramos": ("mass", Decimal("0.001")),
    "l": ("volume", Decimal("1")), "lt": ("volume", Decimal("1")),
    "lts": ("volume", Decimal("1")), "litro": ("volume", Decimal("1")),
    "litros": ("volume", Decimal("1")),
    "ml": ("volume", Decimal("0.001")), "cc": ("volume", Decimal("0.001")),
    "cm3": ("volume", Decimal("0.001")),
    "u": ("count", Decimal("1")), "un": ("count", Decimal("1")),
    "uni": ("count", Decimal("1")), "unid": ("count", Decimal("1")),
    "unids": ("count", Decimal("1")), "unidad": ("count", Decimal("1")),
    "unidades": ("count", Decimal("1")),
    "docena": ("count", Decimal("12")),
}

_UNIT_ALT = "|".join(sorted(map(re.escape, _UNITS), key=len, reverse=True))
# número + unidad pegada o separada: "1kg", "1,5 litros", "1.000 cc", "X500 Gr"
_NUMBER_UNIT = re.compile(rf"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*({_UNIT_ALT})(?![a-z])", re.IGNORECASE)
# "x kg", "por litro": una unidad sola vale 1
_BARE_UNIT = re.compile(rf"\b(?:x|por)\s+(kg|kgs|kilo|kilos|l|lt|lts|litro|litros|docena)(?![a-z])", re.IGNORECASE)


def _parse_number(raw: str) -> Decimal:
    """'1,5' -> 1.5 ; '1.000' -> 1000 (punto de miles) ; '0.500' -> 0.5."""
    if "," in raw:
        return Decimal(raw.replace(".", "").replace(",", "."))
    if re.fullmatch(r"[1-9]\d*\.\d{3}", raw):  # punto seguido de exactamente 3 dígitos
        return Decimal(raw.replace(".", ""))
    return Decimal(raw)


def _to_size(number: str, unit: str) -> Size:
    kind, factor = _UNITS[unit.lower()]
    return Size(kind, (_parse_number(number) * factor).normalize())


def parse_reference_description(text: str | None) -> Size | None:
    """'Valor por 390 g' -> Size(mass, 0.39). None si no se puede (ej. 'por 8 porciones')."""
    if not text:
        return None
    match = _NUMBER_UNIT.search(text)
    if match:
        return _to_size(match.group(1), match.group(2))
    # "Valor por kg" / "Valor por Litro" / "Valor por Docena": una unidad sola vale 1
    bare = re.search(rf"\bpor\s+({_UNIT_ALT})\s*$", text.strip(), re.IGNORECASE)
    if bare:
        return _to_size("1", bare.group(1))
    return None


def parse_size_from_name(name: str | None, kind: Kind | None = None) -> Size | None:
    """
    Tamaño que figura en el nombre de un producto, en unidades base. None si no
    hay tamaño o si hay dos distintos (mejor no adivinar).

    Con `kind` solo se consideran los tamaños de ese tipo: así "Hamburguesas 4 U
    400 g" se resuelve a 4 unidades o a 0,4 kg según lo que se esté comparando.
    """
    if not name:
        return None
    sizes = {_to_size(m.group(1), m.group(2)) for m in _NUMBER_UNIT.finditer(name)}
    sizes |= {_to_size("1", m.group(1)) for m in _BARE_UNIT.finditer(name)}
    if kind is not None:
        sizes = {s for s in sizes if s.kind == kind}
    return next(iter(sizes)) if len(sizes) == 1 else None


# Multipacks y promociones: el precio es por varias unidades y el nombre solo
# trae el tamaño de una ("3 x 125 g", "pack x 2", "2x1", "combo").
_MULTIPACK = re.compile(r"\bpack\b|\bcombo\b|\bpromo(?:cion)?\b|\b\d+\s*[x×]\s*\d", re.IGNORECASE)
# "x 4 unidades": multipack para pesos y litros, pero para un artículo que se mide
# en unidades (huevos, pañales) la cantidad ES el tamaño.
_UNIT_COUNT_PACK = re.compile(r"\b[x×]\s*\d{1,3}\s*(?:u|un|uni|unid|unids|unidades)\b", re.IGNORECASE)


def is_multipack(name: str, *, allow_count: bool = False) -> bool:
    """True si el nombre describe un multipack o una promoción; su precio no es el de una unidad."""
    if _MULTIPACK.search(name):
        return True
    return not allow_count and bool(_UNIT_COUNT_PACK.search(name))
