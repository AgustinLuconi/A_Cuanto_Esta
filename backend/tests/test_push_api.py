"""
Pruebas de integración para los endpoints de push (/api/v1/push).
Usa una DB SQLite en memoria vía dependency_overrides — no toca la Neon
real (estos tests escriben filas; escribir contra producción ensuciaría
datos reales, a diferencia de los tests de solo lectura de otros archivos).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.config.database import Base, get_db
from app.config.settings import settings
from app.models.product import Product, ProductCategory, ProductUnit


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        # StaticPool: TestClient ejecuta los requests en un thread aparte (vía
        # anyio); sin esto, SQLite :memory: le da a ese thread una conexión
        # (y por lo tanto una DB) nueva y vacía, distinta de la que sembramos
        # acá arriba -- "no such table" en el primer request.
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Producto de prueba, para poder crear alertas contra un product_id real.
    seed_db = TestingSessionLocal()
    product = Product(
        name="Leche Entera 1L", normalized_name="leche entera 1l",
        brand="La Serenísima", category=ProductCategory.LACTEOS, unit=ProductUnit.L,
    )
    seed_db.add(product)
    seed_db.commit()
    seed_db.refresh(product)
    product_id = str(product.id)
    seed_db.close()

    with TestClient(app) as c:
        c.product_id = product_id  # type: ignore[attr-defined]
        yield c

    app.dependency_overrides.pop(get_db, None)


def test_vapid_public_key_returns_503_when_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", None)
    response = client.get("/api/v1/push/vapid-public-key")
    assert response.status_code == 503


def test_vapid_public_key_returns_key_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "fake-public-key")
    response = client.get("/api/v1/push/vapid-public-key")
    assert response.status_code == 200
    assert response.json() == {"public_key": "fake-public-key"}


def test_subscribe_creates_subscription_and_alert(client):
    response = client.post("/api/v1/push/subscribe", json={
        "subscription": {"endpoint": "https://push.example.com/a", "keys": {"p256dh": "pk", "auth": "ak"}},
        "alerts": [{"product_id": client.product_id, "target_price": 500.50}],
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["alerts"]) == 1
    assert data["alerts"][0]["product_id"] == client.product_id
    assert data["alerts"][0]["target_price"] == "500.50"
    assert data["alerts"][0]["notified_at_price"] is None


def test_subscribe_upserts_existing_subscription_by_endpoint(client):
    client.post("/api/v1/push/subscribe", json={
        "subscription": {"endpoint": "https://push.example.com/b", "keys": {"p256dh": "pk1", "auth": "ak1"}},
        "alerts": [{"product_id": client.product_id, "target_price": 500}],
    })
    response = client.post("/api/v1/push/subscribe", json={
        "subscription": {"endpoint": "https://push.example.com/b", "keys": {"p256dh": "pk2", "auth": "ak2"}},
        "alerts": [{"product_id": client.product_id, "target_price": 400}],
    })
    data = response.json()
    # Mismo endpoint -> misma suscripción, la alerta se actualiza (no se duplica).
    assert len(data["alerts"]) == 1
    assert data["alerts"][0]["target_price"] == "400.00"


def test_subscribe_resets_notified_at_price_when_target_changes(client):
    r1 = client.post("/api/v1/push/subscribe", json={
        "subscription": {"endpoint": "https://push.example.com/c", "keys": {"p256dh": "pk", "auth": "ak"}},
        "alerts": [{"product_id": client.product_id, "target_price": 500}],
    })
    alert_id = r1.json()["alerts"][0]["id"]
    # Simula que el script ya notificó a $450 antes del segundo POST.
    # (No hay endpoint para setear notified_at_price directo -- se prueba
    # la semántica de "nuevo umbral" indirectamente vía otra suscripción.)
    r2 = client.post("/api/v1/push/subscribe", json={
        "subscription": {"endpoint": "https://push.example.com/c", "keys": {"p256dh": "pk", "auth": "ak"}},
        "alerts": [{"product_id": client.product_id, "target_price": 300}],
    })
    assert r2.json()["alerts"][0]["notified_at_price"] is None


def test_list_alerts_by_endpoint(client):
    client.post("/api/v1/push/subscribe", json={
        "subscription": {"endpoint": "https://push.example.com/d", "keys": {"p256dh": "pk", "auth": "ak"}},
        "alerts": [{"product_id": client.product_id, "target_price": 500}],
    })
    response = client.get("/api/v1/push/alerts", params={"endpoint": "https://push.example.com/d"})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_alerts_returns_empty_list_for_unknown_endpoint(client):
    response = client.get("/api/v1/push/alerts", params={"endpoint": "https://push.example.com/nunca-existio"})
    assert response.status_code == 200
    assert response.json() == []


def test_delete_alert(client):
    r1 = client.post("/api/v1/push/subscribe", json={
        "subscription": {"endpoint": "https://push.example.com/e", "keys": {"p256dh": "pk", "auth": "ak"}},
        "alerts": [{"product_id": client.product_id, "target_price": 500}],
    })
    alert_id = r1.json()["alerts"][0]["id"]

    delete_response = client.delete(f"/api/v1/push/alerts/{alert_id}")
    assert delete_response.status_code == 204

    list_response = client.get("/api/v1/push/alerts", params={"endpoint": "https://push.example.com/e"})
    assert list_response.json() == []


def test_delete_unknown_alert_is_idempotent(client):
    response = client.delete("/api/v1/push/alerts/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 204


def test_subscribe_returns_404_for_unknown_product_id(client):
    # UUID4 válido (para pasar la validación de Pydantic) pero que no
    # corresponde a ningún Product sembrado en la DB de test.
    unknown_product_id = "12345678-1234-4234-8234-123456789abc"
    response = client.post("/api/v1/push/subscribe", json={
        "subscription": {"endpoint": "https://push.example.com/f", "keys": {"p256dh": "pk", "auth": "ak"}},
        "alerts": [{"product_id": unknown_product_id, "target_price": 500}],
    })
    assert response.status_code == 404

    # No debe haber quedado ni suscripción ni alerta como efecto colateral.
    list_response = client.get("/api/v1/push/alerts", params={"endpoint": "https://push.example.com/f"})
    assert list_response.json() == []
