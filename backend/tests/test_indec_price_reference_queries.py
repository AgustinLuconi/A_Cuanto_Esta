"""
Pruebas del acceso a datos del cruce de precios, contra SQLite en memoria
(las tablas se crean desde los modelos).
"""
import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.indec_observation import IndecObservation
from app.models.price_history import PriceHistory, Supermarket
from app.models.product import Product, ProductCategory, ProductUnit
from app.services.indec import price_reference_queries as q
from app.services.indec.reference_rules import RULES

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)
AZUCAR = next(r for r in RULES if r.label == "Azúcar")


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    for model in (IndecObservation, Product, PriceHistory):
        model.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    q._cache.clear()
    yield session
    session.close()
    q._cache.clear()


def _product(db, name, normalized):
    p = Product(name=name, normalized_name=normalized, category=ProductCategory.ALIMENTOS,
                unit=ProductUnit.UNIDAD)
    db.add(p)
    db.commit()
    return p


def _price(db, product, price, sm=Supermarket.COTO, age_hours=1, in_stock=True):
    db.add(PriceHistory(product_id=product.id, supermarket=sm, price=Decimal(str(price)),
                        scraped_at=NOW - timedelta(hours=age_hours), in_stock=in_stock))
    db.commit()


def _indec(db, code, value, description, period, indicator="Precio promedio", region="GBA"):
    db.add(IndecObservation(
        dataset="ipc_nacional", classifier="COICOP Argentina 2019", level="Producto",
        series_code=code, series_name="x", region=region, indicator_type=indicator,
        unit="Pesos argentinos", indicator_description=description, period=period,
        value=Decimal(str(value))))
    db.commit()


def test_fetch_fresh_offers_keeps_only_fresh_in_stock_priced_offers(db):
    a = _product(db, "Azúcar A 1kg", "azucar a 1kg")
    b = _product(db, "Azúcar B 1kg", "azucar b 1kg")
    _price(db, a, 1500)                                   # válida
    _price(db, b, 1600, age_hours=100)                    # vieja (> 72 h)
    _price(db, b, 1700, sm=Supermarket.DIA, in_stock=False)  # sin stock
    _price(db, b, 0, sm=Supermarket.JUMBO)                # precio 0

    offers = q.fetch_fresh_offers(db, now=NOW)

    assert [(o.name, o.price) for o in offers] == [("Azúcar A 1kg", Decimal("1500.00"))]
    assert offers[0].normalized_name == "azucar a 1kg"
    assert offers[0].supermarket == "COTO"


def test_fetch_fresh_offers_uses_latest_price_per_product_and_supermarket(db):
    a = _product(db, "Azúcar A 1kg", "azucar a 1kg")
    _price(db, a, 1400, age_hours=40)
    _price(db, a, 1500, age_hours=2)   # la más nueva gana
    _price(db, a, 1450, sm=Supermarket.DIA, age_hours=5)

    offers = q.fetch_fresh_offers(db, now=NOW)

    assert sorted((o.supermarket, o.price) for o in offers) == [
        ("COTO", Decimal("1500.00")), ("DIA", Decimal("1450.00"))]


def test_fetch_indec_points_picks_latest_period_with_description(db):
    code = AZUCAR.indec_code
    _indec(db, code, 1500, "Valor por kg", date(2026, 9, 1))
    _indec(db, code, 1608, "Valor por kg", date(2026, 10, 1))
    _indec(db, code, 7, "Valor por kg", date(2026, 10, 1), region="Nacional")  # otra región

    points = q.fetch_indec_points(db, (AZUCAR,))

    assert set(points) == {code}
    assert points[code].price == Decimal("1608")
    assert points[code].period == date(2026, 10, 1)
    assert points[code].description == "Valor por kg"


def test_fetch_indec_points_skips_rows_without_description(db):
    # Antes del backfill las filas viejas no tienen la unidad: no se puede comparar
    _indec(db, AZUCAR.indec_code, 1608, None, date(2026, 10, 1))

    assert q.fetch_indec_points(db, (AZUCAR,)) == {}


def test_get_price_reference_end_to_end_and_cached(db):
    _indec(db, AZUCAR.indec_code, 1600, "Valor por kg", date(2026, 10, 1))
    for i, price in enumerate((1500, 1600, 1700)):
        _price(db, _product(db, f"Azúcar {i} 1kg", f"azucar {i} 1kg"), price)

    first = q.get_price_reference(db, now=NOW)

    assert [i.label for i in first] == ["Azúcar"]
    assert first[0].ours_median == Decimal("1600")
    assert first[0].diff_pct == Decimal("0")

    # Segunda llamada dentro del TTL: no vuelve a consultar la base
    db.close()
    assert q.get_price_reference(db, now=NOW + timedelta(minutes=5)) is first


def test_get_price_reference_recomputes_after_the_cache_expires(db):
    _indec(db, AZUCAR.indec_code, 1600, "Valor por kg", date(2026, 10, 1))
    first = q.get_price_reference(db, now=NOW)
    assert first == []   # todavía sin ofertas

    for i in range(3):
        _price(db, _product(db, f"Azúcar {i} 1kg", f"azucar {i} 1kg"), 1600)
    later = q.get_price_reference(db, now=NOW + q.CACHE_TTL + timedelta(seconds=1))

    assert len(later) == 1
