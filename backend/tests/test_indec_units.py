"""
Pruebas de los convertidores de unidades: descripción de referencia del INDEC
("Valor por 390 g") y tamaño de un producto a partir de su nombre ("Azúcar 1kg").
Ambos se llevan a unidades base: kg, litro o unidad.
"""
from decimal import Decimal

import pytest

from app.services.indec.units import Size, parse_reference_description, parse_size_from_name


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Valor por kg", Size("mass", Decimal("1"))),
        ("Valor por Litro", Size("volume", Decimal("1"))),
        ("Valor por 390 g", Size("mass", Decimal("0.39"))),
        ("Valor por 1,5 litros", Size("volume", Decimal("1.5"))),
        ("Valor por 1.000 cc", Size("volume", Decimal("1"))),   # el punto es separador de miles
        ("Valor por 195 cc", Size("volume", Decimal("0.195"))),
        ("Valor por Docena", Size("count", Decimal("12"))),
        ("Valor por Env. 4 u", Size("count", Decimal("4"))),
        ("Valor por Lata 220 g", Size("mass", Decimal("0.22"))),
        ("Valor por 10 u", Size("count", Decimal("10"))),
    ],
)
def test_parse_reference_description(text, expected):
    assert parse_reference_description(text) == expected


@pytest.mark.parametrize("text", ["Valor por 8 porciones", "", None, "algo sin unidad"])
def test_parse_reference_description_returns_none_when_unsupported(text):
    assert parse_reference_description(text) is None


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Azúcar La Campechana 1kg", Size("mass", Decimal("1"))),
        ("Aceite de girasol Pureza 1500 cc.", Size("volume", Decimal("1.5"))),
        ("Leche Entera 1 Lts Manfrey", Size("volume", Decimal("1"))),
        ("Aceite de Girasol Dia 900 Ml.", Size("volume", Decimal("0.9"))),
        ("Harina de Trigo 0000 Pureza x 1000 g.", Size("mass", Decimal("1"))),
        ("Aceite  De Girasol 120 Grs Cuisine & Co", Size("mass", Decimal("0.12"))),
        ("Lavandina Querubín clásica 2 lt.", Size("volume", Decimal("2"))),
        ("Arroz para sushi x kg", Size("mass", Decimal("1"))),
        ("Arroz Yamaní Gallo X500 Gr", Size("mass", Decimal("0.5"))),
        ("Gaseosa Cola 1.5 L", Size("volume", Decimal("1.5"))),
        ("Alimento Adultos RAZA 3 Kg Pollo, Carne, Cereales Y Arroz", Size("mass", Decimal("3"))),
    ],
)
def test_parse_size_from_name(name, expected):
    assert parse_size_from_name(name) == expected


def test_parse_size_from_name_returns_none_without_size():
    assert parse_size_from_name("Harina Sagemuller Leudante") is None


def test_parse_size_from_name_returns_none_when_ambiguous():
    # Dos tamaños distintos en el mismo nombre: mejor no adivinar
    assert parse_size_from_name("Aceite 900 ml pack 2 x 1 L") is None


def test_parse_size_from_name_ignores_repeated_same_size():
    # "1kg" en el nombre y en el campo quantity no es ambigüedad
    assert parse_size_from_name("Azúcar La Campechana 1kg 1kg") == Size("mass", Decimal("1"))


# ---------------------------------------------------------------------------
# preferencia de tipo: "Hamburguesas 4 U 400 g" trae dos tamaños de tipos distintos
# ---------------------------------------------------------------------------
from app.services.indec.units import is_multipack


def test_parse_size_picks_the_requested_kind_when_the_name_has_several():
    name = "Hamburguesas Paty Clásicas 4 U 400 g"

    assert parse_size_from_name(name) is None                                   # ambiguo sin preferencia
    assert parse_size_from_name(name, kind="count") == Size("count", Decimal("4"))
    assert parse_size_from_name(name, kind="mass") == Size("mass", Decimal("0.4"))


def test_parse_size_with_kind_still_rejects_two_sizes_of_that_kind():
    assert parse_size_from_name("Aceite 900 ml pack 2 x 1 L", kind="volume") is None


def test_parse_size_with_kind_returns_none_when_that_kind_is_absent():
    assert parse_size_from_name("Azúcar 1kg", kind="volume") is None


def test_parse_size_resolves_a_mixed_unit_name_by_kind():
    assert parse_size_from_name("Lavandina Limpialin Clasica 25g 4lt", kind="volume") == Size("volume", Decimal("4"))


@pytest.mark.parametrize(
    "name",
    [
        "Jabón de tocador Rexona 3 x 125 g",
        "Shampoo Pantene pack x 2",
        "Gaseosa Coca Cola 1.5 L pack x6",
        "Galletitas Oreo promo 2x1",
        "Cerveza Quilmes combo 6 latas",
        "Yogur Ilolay x 4 unidades",
    ],
)
def test_is_multipack_detects_bundles(name):
    assert is_multipack(name)


@pytest.mark.parametrize(
    "name",
    [
        "Harina de Trigo 0000 Pureza x 1000 g.",
        "Arroz Yamaní Gallo X500 Gr",
        "Aceite de girasol Pureza 1500 cc.",
        "Hamburguesas Paty Clásicas 4 U 400 g",     # 4 U es el envase estándar, no un multipack
        "Leche Entera 1 Lts Manfrey",
    ],
)
def test_is_multipack_leaves_regular_products_alone(name):
    assert not is_multipack(name)


@pytest.mark.parametrize(
    "name, kind, expected",
    [
        ("Hamburguesas PATY 4 Uni X 80 Gr Clásicas", "count", Size("count", Decimal("4"))),
        ("Hamburguesas PATY 4 Uni X 80 Gr Clásicas", "mass", Size("mass", Decimal("0.08"))),
        ("Hamburguesa . Swift Fwp 2 Uni", "count", Size("count", Decimal("2"))),
        ("Pañales Huggies Classic talle P 48 uni", "count", Size("count", Decimal("48"))),
        ("Hamburguesas Medianas X4 U. UNION Ganadera 276 g", "count", Size("count", Decimal("4"))),
    ],
)
def test_parse_size_recognizes_uni_as_a_count_unit(name, kind, expected):
    assert parse_size_from_name(name, kind=kind) == expected
