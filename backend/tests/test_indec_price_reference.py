"""
Pruebas del cruce de precios: precio promedio del INDEC vs. ofertas de los
supermercados, normalizadas a precio por kg / litro / unidad.
"""
import itertools
from decimal import Decimal

import pytest

from app.services.indec.price_reference import MIN_OFFERS, MIN_SUPERMARKETS, Offer, compare_rule
from app.services.indec.units import Size

KG = Size("mass", Decimal("1"))
# INDEC: azúcar a $1.600 el kg
INDEC_PRICE = Decimal("1600")


_SUPERMARKETS = itertools.cycle(["COTO", "DIA", "JUMBO"])


def _offer(name, price, sm=None, pid=None):
    # Por defecto cada oferta es de un supermercado distinto: el cruce exige varios.
    return Offer(product_id=pid or name, name=name, supermarket=sm or next(_SUPERMARKETS),
                 price=Decimal(str(price)))


def test_compares_median_unit_price_against_indec():
    offers = [
        _offer("Azúcar A 1kg", 1400),
        _offer("Azúcar B 1kg", 1600),
        _offer("Azúcar C 1kg", 1800),
    ]

    result = compare_rule(INDEC_PRICE, KG, offers)

    assert result.n_offers == 3
    assert result.ours_median == Decimal("1600")  # por kg
    assert result.ours_min == Decimal("1400")
    assert result.ours_max == Decimal("1800")
    assert result.ours_p25 == Decimal("1500")   # mitad central de las ofertas: 1.500 a 1.700
    assert result.ours_p75 == Decimal("1700")
    assert result.diff_pct == Decimal("0")


def test_normalizes_different_pack_sizes_to_unit_price():
    # 500 g a $900 -> $1.800/kg ; 2 kg a $2.800 -> $1.400/kg ; 1 kg a $1.600
    offers = [
        _offer("Azúcar A 500g", 900),
        _offer("Azúcar B 2kg", 2800),
        _offer("Azúcar C 1kg", 1600),
    ]

    result = compare_rule(INDEC_PRICE, KG, offers)

    assert result.ours_median == Decimal("1600")
    assert result.ours_min == Decimal("1400")
    assert result.ours_max == Decimal("1800")


def test_expresses_our_price_in_the_indec_reference_size():
    # INDEC publica "por 500 g": $1.000 -> $2.000/kg ; nuestra mediana $2.200/kg
    half_kg = Size("mass", Decimal("0.5"))
    offers = [_offer(f"Sal {i} 1kg", 2200) for i in range(3)]

    result = compare_rule(Decimal("1000"), half_kg, offers)

    assert result.indec_unit_price == Decimal("2000")
    assert result.ours_for_reference == Decimal("1100")  # 2.200/kg * 0,5 kg
    assert result.diff_pct == Decimal("0.1")


def test_ignores_offers_of_a_different_kind_or_without_size():
    offers = [
        _offer("Azúcar A 1kg", 1500),
        _offer("Azúcar B 1kg", 1600),
        _offer("Azúcar C 1kg", 1700),
        _offer("Azúcar líquida 1 L", 900),    # volumen: no comparable con masa
        _offer("Azúcar sin tamaño", 1500),     # sin tamaño en el nombre
    ]

    result = compare_rule(INDEC_PRICE, KG, offers)

    assert result.n_offers == 3
    assert result.n_unparsed == 2


def test_drops_junk_prices_outside_a_plausible_band():
    # Precios 0,00 y valores absurdos (ej. 11,69 por 1 kg) no deben mover la mediana
    offers = [
        _offer("Azúcar A 1kg", 1500),
        _offer("Azúcar B 1kg", 1600),
        _offer("Azúcar C 1kg", 1700),
        _offer("Azúcar roto 1kg", 0),
        _offer("Azúcar raro 1kg", "11.69"),
        _offer("Azúcar carísimo 1kg", 90000),
    ]

    result = compare_rule(INDEC_PRICE, KG, offers)

    assert result.n_offers == 3
    assert result.n_discarded == 3
    assert result.ours_median == Decimal("1600")


def test_returns_none_with_too_few_valid_offers():
    offers = [_offer(f"Azúcar {i} 1kg", 1600) for i in range(MIN_OFFERS - 1)]

    assert compare_rule(INDEC_PRICE, KG, offers) is None


def test_counts_distinct_products_and_supermarkets():
    offers = [
        _offer("Azúcar A 1kg", 1500, sm="COTO", pid="a"),
        _offer("Azúcar A 1kg", 1550, sm="DIA", pid="a"),
        _offer("Azúcar B 1kg", 1600, sm="JUMBO", pid="b"),
    ]

    result = compare_rule(INDEC_PRICE, KG, offers)

    assert result.n_offers == 3
    assert result.n_products == 2          # el producto A está en 2 supermercados
    assert result.n_supermarkets == 3


def test_count_kind_uses_units():
    # Huevos: INDEC por docena (12 u) a $4.800 -> $400/u
    dozen = Size("count", Decimal("12"))
    offers = [_offer(f"Huevos Marca{b} x12 unidades", 4800) for b in "ABC"]

    result = compare_rule(Decimal("4800"), dozen, offers)

    assert result.ours_median == Decimal("400")
    assert result.diff_pct == Decimal("0")


def test_drops_offers_far_from_the_indec_reference_size():
    # Referencia INDEC: 1 L. Un sachet de 200 cc o un bidón de 5 L tienen precios
    # por litro que sesgan la comparación: solo cuentan envases de 0,5x a 2x.
    liter = Size("volume", Decimal("1"))
    offers = [
        _offer("Leche A 1 L", 2000),
        _offer("Leche B 1 L", 2100),
        _offer("Leche C 500 ml", 1100),          # 0,5x: entra
        _offer("Leche D 2 L", 3900),             # 2x: entra
        _offer("Leche E 200cc", 1500),           # 0,2x: fuera
        _offer("Leche F 5 L", 9000),             # 5x: fuera
    ]

    result = compare_rule(Decimal("2000"), liter, offers)

    assert result.n_offers == 4
    assert result.n_discarded == 2


# ---------------------------------------------------------------------------
# assemble_price_reference: junta reglas + precios INDEC + ofertas
# ---------------------------------------------------------------------------
import re
from datetime import date

from app.services.indec.price_reference import IndecPoint, assemble_price_reference
from app.services.indec.reference_rules import ReferenceRule

SAL_RULE = ReferenceRule(indec_code="X1", label="Sal", include=re.compile(r"^sal\b"))


def _named(name, price, sm=None, pid=None):
    return Offer(product_id=pid or name, name=name, supermarket=sm or next(_SUPERMARKETS),
                 price=Decimal(str(price)), normalized_name=name.lower())


def test_assemble_expresses_everything_in_the_reference_size():
    # INDEC: "Valor por 500 g" a $1.000 ; nuestras ofertas: 1 kg a $2.200 ($1.100 cada 500 g)
    points = {"X1": IndecPoint("X1", Decimal("1000"), "Valor por 500 g", date(2026, 10, 1))}
    offers = [_named(f"Sal {i} 1kg", 2200) for i in range(3)]

    [item] = assemble_price_reference((SAL_RULE,), points, offers)

    assert item.label == "Sal"
    assert item.reference_unit == "500 g"
    assert item.indec_price == Decimal("1000")
    assert item.indec_period == date(2026, 10, 1)
    assert item.ours_median == Decimal("1100")
    assert item.ours_p25 == Decimal("1100")
    assert item.ours_p75 == Decimal("1100")
    assert item.diff_pct == Decimal("0.1")
    assert item.n_offers == 3


def test_assemble_only_uses_offers_that_match_the_rule():
    points = {"X1": IndecPoint("X1", Decimal("1000"), "Valor por kg", date(2026, 10, 1))}
    offers = [_named(f"Sal {i} 1kg", 1000) for i in range(3)] + [
        _named("Azúcar 1kg", 99999), _named("Pimienta con sal 1kg", 99999),
    ]

    [item] = assemble_price_reference((SAL_RULE,), points, offers)

    assert item.n_offers == 3
    assert item.ours_median == Decimal("1000")


def test_assemble_skips_rules_without_indec_data_or_with_unsupported_unit():
    porciones = {"X1": IndecPoint("X1", Decimal("1000"), "Valor por 8 porciones", date(2026, 10, 1))}
    offers = [_named(f"Sal {i} 1kg", 1000) for i in range(3)]

    assert assemble_price_reference((SAL_RULE,), {}, offers) == []
    assert assemble_price_reference((SAL_RULE,), porciones, offers) == []


def test_assemble_skips_rules_with_too_few_offers():
    points = {"X1": IndecPoint("X1", Decimal("1000"), "Valor por kg", date(2026, 10, 1))}

    assert assemble_price_reference((SAL_RULE,), points, [_named("Sal 1kg", 1000)]) == []


def test_uses_the_indec_kind_to_resolve_names_with_two_sizes():
    # INDEC: hamburguesas "por Env. 4 u". El nombre trae 4 U y 400 g: se toma 4 U.
    four = Size("count", Decimal("4"))
    offers = [_offer(f"Hamburguesas {b} 4 U 400 g", 8000) for b in "ABC"]

    result = compare_rule(Decimal("8000"), four, offers)

    assert result.n_offers == 3
    assert result.ours_median == Decimal("2000")  # $/unidad


def test_multipacks_are_not_compared_as_single_items():
    offers = [
        _offer("Azúcar A 1kg", 1500), _offer("Azúcar B 1kg", 1600), _offer("Azúcar C 1kg", 1700),
        _offer("Azúcar pack 3 x 1kg", 4500),   # precio de 3 kg: no es comparable
    ]

    result = compare_rule(INDEC_PRICE, KG, offers)

    assert result.n_offers == 3
    assert result.n_unparsed == 1


def test_returns_none_when_valid_offers_come_from_too_few_supermarkets():
    # Muchas ofertas, pero de solo 2 supermercados: "los supermercados" no estaría representado
    offers = [_offer(f"Azúcar {i} 1kg", 1600, sm=("COTO" if i % 2 else "DIA")) for i in range(8)]
    assert len({o.supermarket for o in offers}) == MIN_SUPERMARKETS - 1

    assert compare_rule(INDEC_PRICE, KG, offers) is None


def test_accepts_the_minimum_number_of_supermarkets():
    offers = [_offer(f"Azúcar {i} 1kg", 1600, sm=sm) for i, sm in enumerate(["COTO", "DIA", "JUMBO"])]

    assert compare_rule(INDEC_PRICE, KG, offers).n_supermarkets == MIN_SUPERMARKETS
