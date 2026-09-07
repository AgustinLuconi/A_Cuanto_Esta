"""
Pruebas unitarias para Product.full_name (backend/app/models/product.py).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.product import Product, ProductCategory, ProductUnit


def _product(name, brand, unit, quantity):
    return Product(
        name=name,
        normalized_name=name.lower(),
        brand=brand,
        category=ProductCategory.OTROS,
        unit=unit,
        quantity=quantity,
    )


def test_full_name_does_not_duplicate_unit_when_quantity_already_includes_it():
    # Bug real: quantity="100g" + unit=G producía "(100g g)".
    p = _product("Jugo en polvo", "BC", ProductUnit.G, "100g")
    assert p.full_name == "BC Jugo en polvo (100g)"


def test_full_name_appends_unit_when_quantity_is_a_bare_number():
    p = _product("Aceite de oliva", "Cañuelas", ProductUnit.ML, "500")
    assert p.full_name == "Cañuelas Aceite de oliva (500 ml)"


def test_full_name_omits_quantity_parens_when_quantity_is_none():
    p = _product("Detergente", "Ala", ProductUnit.UNIDAD, None)
    assert p.full_name == "Ala Detergente"


def test_full_name_omits_brand_when_missing():
    p = _product("Leche entera", None, ProductUnit.L, "1L")
    assert p.full_name == "Leche entera (1L)"
