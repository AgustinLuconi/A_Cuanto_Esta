"""
Cruce de precios: precio promedio oficial del INDEC vs. ofertas de los
supermercados de la app.

Todo se normaliza a precio por unidad base (kg, litro o unidad) para que
tamaños de envase distintos sean comparables. La comparación es contra la
MEDIANA de las ofertas equivalentes: el INDEC publica un promedio genérico
("Leche fresca entera sachet") y los supermercados venden muchas marcas.

Este módulo es lógica pura (sin base de datos): recibe ofertas ya elegidas.
"""
import statistics
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.services.indec.reference_rules import ReferenceRule
from app.services.indec.units import Size, parse_reference_description, parse_size_from_name

# Con menos ofertas válidas el resultado no es representativo y no se muestra
MIN_OFFERS = 3

# Un precio por unidad base fuera de esta banda respecto del INDEC se descarta
# como dato roto (precios en 0,00, valores absurdos) o producto mal emparejado.
PLAUSIBLE_BAND = (Decimal("0.2"), Decimal("5"))

# Solo cuentan envases de 0,5x a 2x el tamaño de referencia del INDEC: un sachet
# de 200 cc o un bidón de 5 L tienen otro precio por litro y sesgan la mediana.
SIZE_BAND = (Decimal("0.5"), Decimal("2"))

_PCT = Decimal("0.0001")


@dataclass(frozen=True)
class Offer:
    product_id: str
    name: str
    supermarket: str
    price: Decimal
    quantity: str | None = None  # campo `quantity` del producto, a veces trae el tamaño
    normalized_name: str = ""    # minúsculas y sin tildes; es lo que miran las reglas


@dataclass(frozen=True)
class Comparison:
    n_offers: int            # ofertas (producto x supermercado) usadas
    n_products: int
    n_supermarkets: int
    n_unparsed: int          # sin tamaño en el nombre, o de otro tipo (ej. volumen vs masa)
    n_discarded: int         # descartadas por tamaño de envase o precio fuera de banda
    indec_unit_price: Decimal   # INDEC por kg / litro / unidad
    ours_median: Decimal        # mediana nuestra, por kg / litro / unidad
    ours_min: Decimal
    ours_max: Decimal
    ours_p25: Decimal            # la mitad central de las ofertas va de p25 a p75 (por kg / litro / unidad)
    ours_p75: Decimal
    ours_for_reference: Decimal  # mediana nuestra llevada al tamaño de referencia del INDEC
    diff_pct: Decimal            # (nuestra / INDEC) - 1 ; 0.1 = 10% más caro


def compare_rule(
    indec_price: Decimal, indec_size: Size, offers: list[Offer]
) -> Comparison | None:
    """
    Compara el precio del INDEC (válido para `indec_size`) con las ofertas.
    None si quedan menos de MIN_OFFERS ofertas válidas.
    """
    indec_unit = indec_price / indec_size.amount
    low, high = (indec_unit * f for f in PLAUSIBLE_BAND)

    valid: list[tuple[Offer, Decimal]] = []
    unparsed = discarded = 0
    for offer in offers:
        size = parse_size_from_name(f"{offer.name} {offer.quantity or ''}")
        if size is None or size.kind != indec_size.kind:
            unparsed += 1
            continue
        unit_price = offer.price / size.amount
        ratio = size.amount / indec_size.amount
        out_of_size = not (SIZE_BAND[0] <= ratio <= SIZE_BAND[1])
        if offer.price <= 0 or out_of_size or not (low <= unit_price <= high):
            discarded += 1
            continue
        valid.append((offer, unit_price))

    if len(valid) < MIN_OFFERS:
        return None

    prices = [p for _, p in valid]
    median = statistics.median(prices)
    p25, _, p75 = statistics.quantiles(prices, n=4, method="inclusive")
    return Comparison(
        n_offers=len(valid),
        n_products=len({o.product_id for o, _ in valid}),
        n_supermarkets=len({o.supermarket for o, _ in valid}),
        n_unparsed=unparsed,
        n_discarded=discarded,
        indec_unit_price=indec_unit,
        ours_median=median,
        ours_min=min(prices),
        ours_max=max(prices),
        ours_p25=p25,
        ours_p75=p75,
        ours_for_reference=median * indec_size.amount,
        diff_pct=(median / indec_unit - 1).quantize(_PCT),
    )


@dataclass(frozen=True)
class IndecPoint:
    """Último precio promedio del INDEC para un artículo."""

    code: str
    price: Decimal
    description: str  # "Valor por 390 g"
    period: date


@dataclass(frozen=True)
class ReferenceItem:
    """Resultado del cruce para un artículo, todo expresado en el tamaño de referencia del INDEC."""

    code: str
    label: str
    reference_unit: str      # "kg", "500 g", "1,5 litros"... (lo que dice el INDEC)
    indec_period: date
    indec_price: Decimal
    ours_median: Decimal
    ours_p25: Decimal        # la mitad central de las ofertas va de p25 a p75
    ours_p75: Decimal
    diff_pct: Decimal        # 0.1 = nuestros supermercados un 10% más caros
    n_offers: int
    n_products: int
    n_supermarkets: int


def _reference_unit_label(description: str) -> str:
    """'Valor por 390 g' -> '390 g'."""
    return description.removeprefix("Valor por").strip()


def assemble_price_reference(
    rules: tuple[ReferenceRule, ...],
    points: dict[str, IndecPoint],
    offers: list[Offer],
) -> list[ReferenceItem]:
    """
    Aplica cada regla: toma el precio del INDEC, elige las ofertas equivalentes y
    las compara. Omite los artículos sin dato del INDEC, con una unidad que no se
    sabe convertir, o con menos de MIN_OFFERS ofertas válidas.
    """
    items: list[ReferenceItem] = []
    for rule in rules:
        point = points.get(rule.indec_code)
        if point is None:
            continue
        size = parse_reference_description(point.description)
        if size is None:
            continue
        matched = [o for o in offers if rule.matches(o.normalized_name)]
        comparison = compare_rule(point.price, size, matched)
        if comparison is None:
            continue
        items.append(
            ReferenceItem(
                code=rule.indec_code,
                label=rule.label,
                reference_unit=_reference_unit_label(point.description),
                indec_period=point.period,
                indec_price=point.price,
                ours_median=comparison.ours_for_reference,
                ours_p25=comparison.ours_p25 * size.amount,
                ours_p75=comparison.ours_p75 * size.amount,
                diff_pct=comparison.diff_pct,
                n_offers=comparison.n_offers,
                n_products=comparison.n_products,
                n_supermarkets=comparison.n_supermarkets,
            )
        )
    return items
