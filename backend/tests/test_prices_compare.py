"""
Pruebas unitarias para la lógica de comparación de precios entre supermercados
(app/api/v1/endpoints/prices.py::compare_prices). Se mockea la sesión de
SQLAlchemy y `_get_current_prices` (la construcción del query con joins/subquery
no es el objeto de esta prueba) para aislar el cálculo de negocio: precio más
bajo/alto, diferencia porcentual y "mejor oferta".
"""
import os
import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.prices import compare_prices
from app.models.price_history import Supermarket
from app.models.product import Product


def _make_price(supermarket, price):
    return SimpleNamespace(
        supermarket=supermarket,
        price=price,
        was_on_sale=False,
        original_price=None,
        discount_percentage=None,
        url=None,
        scraped_at=datetime(2026, 1, 1),
        in_stock=True,
        province=None,
        region=None,
    )


def _make_db(product):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = product
    return db


def test_compare_prices_computes_lowest_highest_and_percentage_difference():
    # Arrange
    product = SimpleNamespace(id=uuid4(), name="Coca Cola 1.5L", image_url=None)
    db = _make_db(product)
    prices = [_make_price(Supermarket.COTO, 100), _make_price(Supermarket.CARREFOUR, 150)]

    # Act
    with patch(
        "app.api.v1.endpoints.prices._get_current_prices", return_value=prices
    ):
        result = compare_prices(product_id=product.id, db=db)

    # Assert
    assert result.lowest_price == 100
    assert result.highest_price == 150
    assert result.price_difference == 50
    assert float(result.price_difference_percentage) == pytest.approx(33.33, abs=0.01)
    assert result.best_deal == Supermarket.COTO


def test_compare_prices_best_deal_is_supermarket_with_lowest_price():
    # Arrange: el más barato no es el primero de la lista
    product = SimpleNamespace(id=uuid4(), name="Yerba 1kg", image_url=None)
    db = _make_db(product)
    prices = [
        _make_price(Supermarket.CARREFOUR, 200),
        _make_price(Supermarket.DIA, 80),
        _make_price(Supermarket.COTO, 150),
    ]

    # Act
    with patch(
        "app.api.v1.endpoints.prices._get_current_prices", return_value=prices
    ):
        result = compare_prices(product_id=product.id, db=db)

    # Assert
    assert result.best_deal == Supermarket.DIA
    assert result.lowest_price == 80
    assert result.highest_price == 200


def test_compare_prices_zero_difference_when_all_prices_equal():
    # Arrange: mismo precio en todos los supermercados -> sin división por
    # cero y diferencia porcentual en 0.
    product = SimpleNamespace(id=uuid4(), name="Agua 500ml", image_url=None)
    db = _make_db(product)
    prices = [_make_price(Supermarket.COTO, 500), _make_price(Supermarket.DIA, 500)]

    with patch(
        "app.api.v1.endpoints.prices._get_current_prices", return_value=prices
    ):
        result = compare_prices(product_id=product.id, db=db)

    assert result.price_difference == 0
    assert result.price_difference_percentage == 0.0


def test_compare_prices_raises_404_when_no_current_prices():
    # Arrange: producto existe pero no tiene precios vigentes
    product = SimpleNamespace(id=uuid4(), name="Producto sin stock", image_url=None)
    db = _make_db(product)

    # Act / Assert
    with patch("app.api.v1.endpoints.prices._get_current_prices", return_value=[]):
        with pytest.raises(HTTPException) as exc_info:
            compare_prices(product_id=product.id, db=db)

    assert exc_info.value.status_code == 404


def test_compare_prices_raises_404_when_product_not_found():
    # Arrange
    db = _make_db(None)

    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        compare_prices(product_id=uuid4(), db=db)

    assert exc_info.value.status_code == 404
