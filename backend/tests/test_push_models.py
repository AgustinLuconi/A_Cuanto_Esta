"""
Pruebas unitarias para los modelos PushSubscription y PriceAlert — solo
verifican que las tablas se puedan crear e insertar/consultar en SQLite en
memoria (no toca la Neon real).
"""
import os
import sys
import uuid
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.database import Base
from app.models.product import Product, ProductCategory, ProductUnit
from app.models.push_subscription import PushSubscription
from app.models.price_alert import PriceAlert


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make_product(session):
    product = Product(
        name="Leche Entera 1L", normalized_name="leche entera 1l",
        brand="La Serenísima", category=ProductCategory.LACTEOS, unit=ProductUnit.L,
    )
    session.add(product)
    session.commit()
    return product


def test_create_subscription_and_alert(session):
    product = _make_product(session)
    sub = PushSubscription(endpoint="https://push.example.com/abc", p256dh_key="pkey", auth_key="akey")
    session.add(sub)
    session.commit()

    alert = PriceAlert(subscription_id=sub.id, product_id=product.id, target_price=Decimal("500.00"))
    session.add(alert)
    session.commit()

    assert alert.notified_at_price is None
    assert alert.subscription.endpoint == "https://push.example.com/abc"
    assert sub.alerts == [alert]


def test_endpoint_is_unique(session):
    session.add(PushSubscription(endpoint="https://push.example.com/dup", p256dh_key="a", auth_key="b"))
    session.commit()
    session.add(PushSubscription(endpoint="https://push.example.com/dup", p256dh_key="c", auth_key="d"))
    with pytest.raises(Exception):
        session.commit()


def test_deleting_subscription_cascades_to_its_alerts(session):
    # SQLite en memoria no aplica el ondelete="CASCADE" de la FK (requiere
    # PRAGMA foreign_keys=ON), así que esto prueba específicamente el
    # cascade="all, delete-orphan" del lado relationship() en el ORM.
    product = _make_product(session)
    sub = PushSubscription(endpoint="https://push.example.com/cascade", p256dh_key="pkey", auth_key="akey")
    session.add(sub)
    session.commit()

    alert = PriceAlert(subscription_id=sub.id, product_id=product.id, target_price=Decimal("500.00"))
    session.add(alert)
    session.commit()

    session.delete(sub)
    session.commit()

    assert session.query(PriceAlert).count() == 0


def test_alert_unique_constraint_on_subscription_and_product(session):
    product = _make_product(session)
    sub = PushSubscription(endpoint="https://push.example.com/unique-alert", p256dh_key="pkey", auth_key="akey")
    session.add(sub)
    session.commit()

    session.add(PriceAlert(subscription_id=sub.id, product_id=product.id, target_price=Decimal("500.00")))
    session.commit()

    session.add(PriceAlert(subscription_id=sub.id, product_id=product.id, target_price=Decimal("600.00")))
    with pytest.raises(Exception):
        session.commit()
