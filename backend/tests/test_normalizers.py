"""
Pruebas unitarias para las funciones de normalización del scraper.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.models.product import ProductCategory, ProductUnit
from app.scrapers.utils.normalizer import (
    normalize_product_name,
    normalize_name,
    map_category,
    map_unit,
    parse_discount_price,
    build_quantity_str,
)


def test_normalize_product_name_removes_accents_and_lowercases():
    raw = "Leche Entera Larga Vida 1L Sancor Café"
    normalized = normalize_product_name(raw)
    assert normalized == "leche entera larga vida 1l sancor cafe"


def test_normalize_name_replaces_punctuation_with_spaces():
    raw = "Coca-Cola, Zero. 1.5L"
    normalized = normalize_name(raw)
    assert normalized == "coca cola zero 1 5l"


def test_map_category_identifies_lacteos():
    groups = [{"path_list": [{"display_name": "Lácteos"}]}]
    cat = map_category(groups)
    assert cat == ProductCategory.LACTEOS


def test_map_category_identifies_limpieza():
    groups = [{"display_name": "Limpieza"}]
    cat = map_category(groups)
    assert cat == ProductCategory.LIMPIEZA


def test_map_category_returns_otros_when_unmatched():
    groups = [{"display_name": "CategoríaDesconocidaXYZ"}]
    cat = map_category(groups)
    assert cat == ProductCategory.OTROS


def test_map_unit_maps_common_units():
    assert map_unit("Litro") == ProductUnit.L
    assert map_unit("Gramo") == ProductUnit.G
    assert map_unit("Unidad") == ProductUnit.UNIDAD
    assert map_unit("Pack") == ProductUnit.PACK


def test_parse_discount_price_handles_argentine_and_standard_formats():
    assert parse_discount_price("$1.898,97") == 1898.97
    assert parse_discount_price("$1898.97") == 1898.97
    assert parse_discount_price("2500") == 2500.0
    assert parse_discount_price("") is None
    assert parse_discount_price(None) is None


def test_build_quantity_str_formats_abbreviation():
    assert build_quantity_str(1.0, "Litro") == "1L"
    assert build_quantity_str(500.0, "Gramo") == "500g"
    assert build_quantity_str(6.0, "Unidad") == "6un"
