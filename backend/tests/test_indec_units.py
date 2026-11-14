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
