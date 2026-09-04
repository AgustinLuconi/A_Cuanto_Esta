"""
Pruebas unitarias para la lógica de comparación precio-vs-inflación
(app/api/v1/endpoints/analysis.py). Se mockea la sesión de SQLAlchemy;
no se toca la base de datos real.
"""
import os
import sys
from types import SimpleNamespace
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.analysis import _build_analysis_text, _compute_price_changes, price_vs_inflation
from app.models.economic_indicator import EconomicIndicator
from app.models.price_history import PriceHistory, Supermarket
from app.models.product import Product, ProductCategory


# --- _build_analysis_text: función pura ---------------------------------


def test_build_analysis_text_when_equal():
    text = _build_analysis_text("equal", price_change=10.0, inflation=10.0, difference=0.0)
    assert text == "El precio siguió a la inflación del período."


def test_build_analysis_text_above_with_positive_inflation_shows_multiplier():
    text = _build_analysis_text("above", price_change=20.0, inflation=5.0, difference=15.0)
    assert text == "El producto subió 4.0x más que la inflación del período."


def test_build_analysis_text_above_with_zero_inflation_avoids_division_by_zero():
    # Sin este branch explícito, price_change / inflation lanzaría ZeroDivisionError.
    text = _build_analysis_text("above", price_change=8.0, inflation=0.0, difference=8.0)
    assert text == "El producto subió 8.0% mientras la inflación fue 0%."


def test_build_analysis_text_below_shows_absolute_difference():
    text = _build_analysis_text("below", price_change=3.0, inflation=10.0, difference=-7.0)
    assert text == "El producto subió menos que la inflación (7.0 p.p. por debajo)."


# --- price_vs_inflation: endpoint con DB mockeada ------------------------


def _make_db(product, price_records, inflation_records):
    def query_side_effect(model):
        m = MagicMock()
        if model is Product:
            m.filter.return_value.first.return_value = product
        elif model is PriceHistory:
            m.filter.return_value.order_by.return_value.all.return_value = price_records
        elif model is EconomicIndicator:
            m.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
                inflation_records
            )
        else:
            raise AssertionError(f"Modelo inesperado consultado: {model}")
        return m

    db = MagicMock()
    db.query.side_effect = query_side_effect
    return db


def _price_record(price, when):
    return SimpleNamespace(price=price, scraped_at=when)


def test_price_vs_inflation_computes_change_and_compares_to_compounded_inflation():
    # Arrange: precio sube 20% (100 -> 120), inflación del período (1 mes) es 5%
    product = SimpleNamespace(id=uuid4(), name="Leche Entera 1L")
    prices = [
        _price_record(100, datetime(2026, 1, 1)),
        _price_record(120, datetime(2026, 1, 30)),
    ]
    inflation = [SimpleNamespace(value=5)]
    db = _make_db(product, prices, inflation)

    # Act
    result = price_vs_inflation(
        product_id=product.id, supermarket=Supermarket.COTO, days=30, db=db
    )

    # Assert
    assert result.price_change_percent == 20.0
    assert result.inflation_period_percent == 5.0
    assert result.comparison == "above"
    assert result.difference_points == 15.0
    assert "4.0x" in result.analysis_text


def test_price_vs_inflation_boundary_difference_under_half_point_is_equal():
    # Arrange: diferencia de exactamente 0.4 p.p. -> "equal" (< 0.5)
    product = SimpleNamespace(id=uuid4(), name="Producto X")
    prices = [
        _price_record(1000, datetime(2026, 1, 1)),
        _price_record(1104, datetime(2026, 1, 30)),  # +10.4%
    ]
    inflation = [SimpleNamespace(value=10)]  # 10.0% de inflación
    db = _make_db(product, prices, inflation)

    result = price_vs_inflation(
        product_id=product.id, supermarket=Supermarket.COTO, days=30, db=db
    )

    assert result.price_change_percent == 10.4
    assert result.comparison == "equal"


def test_price_vs_inflation_boundary_at_exactly_half_point_is_not_equal():
    # Arrange: diferencia de exactamente 0.5 p.p. -> ya NO es "equal" (limite estricto <0.5)
    product = SimpleNamespace(id=uuid4(), name="Producto X")
    prices = [
        _price_record(1000, datetime(2026, 1, 1)),
        _price_record(1105, datetime(2026, 1, 30)),  # +10.5%
    ]
    inflation = [SimpleNamespace(value=10)]  # 10.0%
    db = _make_db(product, prices, inflation)

    result = price_vs_inflation(
        product_id=product.id, supermarket=Supermarket.COTO, days=30, db=db
    )

    assert result.difference_points == 0.5
    assert result.comparison == "above"


def test_price_vs_inflation_raises_404_when_product_not_found():
    db = _make_db(None, [], [])
    with pytest.raises(HTTPException) as exc_info:
        price_vs_inflation(product_id=uuid4(), supermarket=Supermarket.COTO, days=30, db=db)
    assert exc_info.value.status_code == 404


def test_price_vs_inflation_raises_400_when_only_one_price_record():
    product = SimpleNamespace(id=uuid4(), name="Producto X")
    prices = [_price_record(100, datetime(2026, 1, 1))]
    db = _make_db(product, prices, [])

    with pytest.raises(HTTPException) as exc_info:
        price_vs_inflation(product_id=product.id, supermarket=Supermarket.COTO, days=30, db=db)

    assert exc_info.value.status_code == 400


def test_price_vs_inflation_raises_404_when_no_price_records_in_period():
    product = SimpleNamespace(id=uuid4(), name="Producto X")
    db = _make_db(product, [], [])

    with pytest.raises(HTTPException) as exc_info:
        price_vs_inflation(product_id=product.id, supermarket=Supermarket.COTO, days=30, db=db)

    assert exc_info.value.status_code == 404


# --- _compute_price_changes: canasta y cálculo de variación -------------


def _row(product_id, supermarket, price, days_ago, category):
    return (product_id, supermarket, price, datetime.utcnow() - timedelta(days=days_ago), category)


def test_compute_price_changes_excludes_pair_below_coverage_threshold():
    # Arrange: ventana de 10 días, umbral de continuidad = ceil(10*0.7) = 7 días.
    # Este (producto, super) solo tiene 2 días distintos de precio -> por debajo del umbral.
    pid = uuid4()
    rows = [
        _row(pid, Supermarket.COTO, 100, days_ago=9, category=ProductCategory.LACTEOS),
        _row(pid, Supermarket.COTO, 110, days_ago=1, category=ProductCategory.LACTEOS),
    ]
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = rows

    result = _compute_price_changes(db, days=10)

    assert result == []


def test_compute_price_changes_includes_pair_meeting_threshold():
    # Arrange: 7 días distintos de precio en una ventana de 10 días (umbral: 7) -> entra.
    # Precio sube de 100 a 110 -> +10%.
    pid = uuid4()
    rows = [_row(pid, Supermarket.COTO, 100, days_ago=9, category=ProductCategory.LACTEOS)]
    for d in range(6, 0, -1):
        rows.append(_row(pid, Supermarket.COTO, 100 + (9 - d), days_ago=d, category=ProductCategory.LACTEOS))
    rows.append(_row(pid, Supermarket.COTO, 110, days_ago=1, category=ProductCategory.LACTEOS))
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = rows

    result = _compute_price_changes(db, days=10)

    assert len(result) == 1
    change_pct, category_value = result[0]
    assert change_pct == pytest.approx(0.10)
    assert category_value == "lacteos"


def test_compute_price_changes_returns_empty_list_when_no_rows():
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = []

    result = _compute_price_changes(db, days=7)

    assert result == []


def test_compute_price_changes_skips_pair_with_zero_first_price():
    # (producto, super) con suficiente continuidad pero precio inicial 0 -> evita división por cero.
    pid = uuid4()
    rows = [
        _row(pid, Supermarket.COTO, 0, days_ago=d, category=ProductCategory.LACTEOS)
        for d in range(6, -1, -1)
    ]
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = rows

    result = _compute_price_changes(db, days=7)

    assert result == []


def test_compute_price_changes_treats_different_supermarkets_as_independent_series():
    # Mismo producto en 2 supermercados: Coto sube 100->110 (+10%, 7 días
    # continuos, entra), Carrefour tiene solo 1 día de datos (no entra). Si
    # el agrupamiento fuera por product_id solo (sin supermarket), esto se
    # mezclaría en una sola serie con el orden equivocado — cada
    # (producto, super) debe evaluarse de forma completamente independiente.
    pid = uuid4()
    rows = [_row(pid, Supermarket.COTO, 100, days_ago=9, category=ProductCategory.LACTEOS)]
    for d in range(6, 0, -1):
        rows.append(_row(pid, Supermarket.COTO, 100 + (9 - d), days_ago=d, category=ProductCategory.LACTEOS))
    rows.append(_row(pid, Supermarket.COTO, 110, days_ago=1, category=ProductCategory.LACTEOS))
    rows.append(_row(pid, Supermarket.CARREFOUR, 9999, days_ago=5, category=ProductCategory.LACTEOS))
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = rows

    result = _compute_price_changes(db, days=10)

    assert len(result) == 1
    change_pct, category_value = result[0]
    assert change_pct == pytest.approx(0.10)  # el 9999 de Carrefour nunca entra al cálculo
