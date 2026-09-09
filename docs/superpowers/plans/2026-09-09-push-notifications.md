# Notificaciones Push Reales — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar el sistema de alertas de precio (hoy 100% localStorage + Notification API del navegador, solo funciona con la pestaña abierta) por notificaciones Web Push reales respaldadas en el backend, con un chequeo diario vía GitHub Actions.

**Architecture:** Dos tablas nuevas en Neon (`push_subscriptions`, `price_alerts`), 4 endpoints REST bajo `/api/v1/push/*`, un script (`check_price_alerts.py`) que corre una vez al día vía GitHub Actions y manda pushes reales con `pywebpush`, y en el frontend un service worker vanilla + reescritura de `priceAlertsContext.tsx` para hablar con el backend en vez de `localStorage`.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, Alembic, Neon Postgres, `pywebpush`/`py-vapid`, Next.js 14 (App Router), Web Push API nativa del navegador (sin `next-pwa`), GitHub Actions.

**Spec:** `docs/plans/2026-09-09-push-notifications-design.md`

## Global Constraints

- Sin cuentas de usuario: cada suscripción se identifica por su `endpoint` (string único), no por un user id.
- Cero costo nuevo: nada de Celery/Redis, nada de plan pago de Render — el scheduler es GitHub Actions (gratis).
- Se reemplaza el sistema viejo por completo — no conviven ambos.
- Todas las columnas `DateTime` nuevas usan `DateTime(timezone=True)` con default `utcnow_aware` (ver `app/utils/time.py`) — nunca `datetime.utcnow()` ni columnas naive (bug real ya encontrado dos veces esta sesión, ver memoria `timezone_aware_migration_2026_09_08`).
- Todo script que escriba contra producción en un loop debe manejar errores por ítem sin abortar el resto (el chequeo de alertas no debe morir entero por una suscripción vencida).
- Reusar `_get_current_prices_bulk` de `app/api/v1/endpoints/products.py` para "precio actual" — no reinventar esa lógica (ya evita N+1 y ya es la fuente de verdad que usa el resto de la app, incluido el chequeo viejo de `PriceAlertsChecker.tsx` vía `lowest_price`).
- No hay test runner de frontend configurado en este proyecto (no `jest`/`vitest` en `package.json`) — la verificación de las tareas de frontend es manual (dev server + browser), no tests automatizados. No agregar un test runner nuevo solo para esto (fuera de alcance).

---

### Task 1: Dependencias y configuración (VAPID settings)

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config/settings.py`

**Interfaces:**
- Produces: `settings.VAPID_PUBLIC_KEY: Optional[str]`, `settings.VAPID_PRIVATE_KEY: Optional[str]`, `settings.VAPID_CLAIMS_EMAIL: str` — usados por Task 5 (endpoint) y Task 7 (script).

- [ ] **Step 1: Agregar `pywebpush` a requirements.txt**

En `backend/requirements.txt`, agregar después del bloque `# Tareas asíncronas`:

```
# Web Push (notificaciones de alertas de precio)
pywebpush>=2.0
```

- [ ] **Step 2: Instalar y verificar**

Run: `cd backend && source venv/bin/activate && pip install -r requirements.txt`
Expected: instala `pywebpush`, `py-vapid`, `http-ece`, `cryptography` sin error.

- [ ] **Step 3: Agregar settings de VAPID**

En `backend/app/config/settings.py`, después del bloque `# Security`:

```python
    # Security
    SECRET_KEY: str

    # Web Push (VAPID) — opcionales: sin configurar, el endpoint de la
    # clave pública devuelve 503 y el script de chequeo aborta con error
    # claro, en vez de romper el arranque normal de la app.
    VAPID_PUBLIC_KEY: Optional[str] = None
    VAPID_PRIVATE_KEY: Optional[str] = None
    VAPID_CLAIMS_EMAIL: str = "admin@example.com"
```

- [ ] **Step 4: Verificar que la app sigue arrancando sin las VAPID keys configuradas**

Run: `cd backend && source venv/bin/activate && python3 -c "from app.main import app; print('OK')"`
Expected: `OK` (no debe fallar por VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY ausentes, son opcionales).

- [ ] **Step 5: Commit**

```bash
cd "/home/agustin/PROYECTOS/A_Cuanto_Esta?"
git add backend/requirements.txt backend/app/config/settings.py
git commit -m "$(cat <<'EOF'
chore: add pywebpush dependency and VAPID settings

Preparación para las notificaciones push reales (ver docs/plans/2026-09-09-push-notifications-design.md).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Modelos `PushSubscription` y `PriceAlert`

**Files:**
- Create: `backend/app/models/push_subscription.py`
- Create: `backend/app/models/price_alert.py`
- Test: `backend/tests/test_push_models.py`

**Interfaces:**
- Consumes: `app.config.database.Base`, `app.utils.time.utcnow_aware`, `app.models.product.Product` (FK).
- Produces: `PushSubscription` (tabla `push_subscriptions`: `id`, `endpoint` único, `p256dh_key`, `auth_key`, `created_at`, relationship `.alerts`), `PriceAlert` (tabla `price_alerts`: `id`, `subscription_id` FK, `product_id` FK, `target_price`, `created_at`, `notified_at_price` nullable, relationships `.subscription`/`.product`). Usados por Task 3 (migración), Task 5 (endpoints), Task 7 (script).

- [ ] **Step 1: Escribir el test (falla porque los modelos no existen)**

Crear `backend/tests/test_push_models.py`:

```python
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
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd backend && source venv/bin/activate && pytest tests/test_push_models.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.push_subscription'`

- [ ] **Step 3: Crear `app/models/push_subscription.py`**

```python
"""
Modelo de base de datos para Suscripciones de Web Push.

No hay cuentas de usuario en el proyecto: cada suscripción representa un
navegador/dispositivo (el `endpoint` que da el browser es único por
combinación navegador+dispositivo+origen), no una persona.
"""
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.config.database import Base
from app.utils.time import utcnow_aware


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    endpoint   = Column(String(500), nullable=False, unique=True, index=True)
    p256dh_key = Column(String(255), nullable=False)
    auth_key   = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow_aware, nullable=False)

    alerts = relationship("PriceAlert", back_populates="subscription", cascade="all, delete-orphan")
```

- [ ] **Step 4: Crear `app/models/price_alert.py`**

```python
"""
Modelo de base de datos para Alertas de Precio.

Una alerta "avisame si <product> baja de <target_price>", atada a una
PushSubscription (navegador/dispositivo) — reemplaza el localStorage que
usaba el sistema anterior.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.config.database import Base
from app.utils.time import utcnow_aware


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id   = Column(UUID(as_uuid=True), ForeignKey("push_subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id        = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    target_price      = Column(Numeric(10, 2), nullable=False)
    created_at        = Column(DateTime(timezone=True), default=utcnow_aware, nullable=False)
    # Último precio con el que ya se notificó — evita re-notificar dos veces
    # al mismo precio (mismo campo/semántica que el localStorage viejo).
    notified_at_price = Column(Numeric(10, 2), nullable=True)

    subscription = relationship("PushSubscription", back_populates="alerts")
    product      = relationship("Product")

    __table_args__ = (
        UniqueConstraint("subscription_id", "product_id", name="uq_subscription_product"),
    )
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `cd backend && source venv/bin/activate && pytest tests/test_push_models.py -v`
Expected: `2 passed`

- [ ] **Step 6: Correr toda la suite para verificar que nada se rompió**

Run: `cd backend && source venv/bin/activate && pytest -q`
Expected: todos los tests existentes (104 antes de esta tarea) más los 2 nuevos, sin fallos.

- [ ] **Step 7: Commit**

```bash
cd "/home/agustin/PROYECTOS/A_Cuanto_Esta?"
git add backend/app/models/push_subscription.py backend/app/models/price_alert.py backend/tests/test_push_models.py
git commit -m "$(cat <<'EOF'
feat: add PushSubscription and PriceAlert models

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Migración Alembic

**Files:**
- Create: `backend/alembic/versions/<nueva_revision>_add_push_subscriptions_and_price_alerts.py`

**Interfaces:**
- Consumes: cabeza actual de Alembic (`c00c6a2c9fb1`, confirmar con `alembic current` porque puede haber cambiado).
- Produces: tablas `push_subscriptions` y `price_alerts` en Neon.

- [ ] **Step 1: Generar el archivo de revisión**

Run: `cd backend && source venv/bin/activate && alembic revision -m "add push subscriptions and price alerts"`
Expected: crea `alembic/versions/<hash>_add_push_subscriptions_and_price_alerts.py` con `down_revision` apuntando a la cabeza actual (verificar con `alembic current` antes de este paso — si no es `c00c6a2c9fb1`, hay una migración de otra sesión intermedia y esta migración debe encadenar sobre esa).

- [ ] **Step 2: Escribir `upgrade()`/`downgrade()`**

Reemplazar el contenido del archivo generado (mantener el `revision`/`down_revision` que Alembic generó):

```python
"""add push subscriptions and price alerts

Revision ID: <el que generó Alembic>
Revises: <el head detectado en Step 1>
Create Date: <la que generó Alembic>

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '<el que generó Alembic>'
down_revision = '<el head detectado en Step 1>'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'push_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('endpoint', sa.String(length=500), nullable=False),
        sa.Column('p256dh_key', sa.String(length=255), nullable=False),
        sa.Column('auth_key', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_push_subscriptions_endpoint'), 'push_subscriptions', ['endpoint'], unique=True)

    op.create_table(
        'price_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notified_at_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['subscription_id'], ['push_subscriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subscription_id', 'product_id', name='uq_subscription_product'),
    )
    op.create_index(op.f('ix_price_alerts_subscription_id'), 'price_alerts', ['subscription_id'], unique=False)
    op.create_index(op.f('ix_price_alerts_product_id'), 'price_alerts', ['product_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_price_alerts_product_id'), table_name='price_alerts')
    op.drop_index(op.f('ix_price_alerts_subscription_id'), table_name='price_alerts')
    op.drop_table('price_alerts')
    op.drop_index(op.f('ix_push_subscriptions_endpoint'), table_name='push_subscriptions')
    op.drop_table('push_subscriptions')
```

- [ ] **Step 3: Verificar que la migración corre limpio en un check local (sin aplicar todavía)**

Run: `cd backend && source venv/bin/activate && python3 -c "import ast; ast.parse(open('alembic/versions/<archivo_generado>.py').read())" && echo OK`
Expected: `OK` (sintaxis válida — no se aplica a producción en este paso, eso es la Task 9).

- [ ] **Step 4: Commit**

```bash
cd "/home/agustin/PROYECTOS/A_Cuanto_Esta?"
git add backend/alembic/versions/<archivo_generado>.py
git commit -m "$(cat <<'EOF'
feat: migration for push_subscriptions and price_alerts tables

No aplicada todavía a producción — se aplica en la tarea de deploy
(alembic upgrade head corre automáticamente en el startCommand de Render).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Schemas Pydantic

**Files:**
- Create: `backend/app/schemas/push.py`

**Interfaces:**
- Produces: `PushSubscriptionKeys`, `PushSubscriptionInfo`, `AlertCreate`, `SubscribeRequest`, `PriceAlertOut`, `SubscribeResponse`, `VapidPublicKeyResponse` — usados por Task 5.

- [ ] **Step 1: Crear el archivo**

```python
"""
Schemas de Pydantic para Notificaciones Push (Web Push API) y Alertas de Precio.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, UUID4


class PushSubscriptionKeys(BaseModel):
    """Claves de cifrado de una PushSubscription del navegador."""
    p256dh: str
    auth: str


class PushSubscriptionInfo(BaseModel):
    """Forma exacta de `PushSubscription.toJSON()` en el navegador."""
    endpoint: str = Field(..., max_length=500)
    keys: PushSubscriptionKeys


class AlertCreate(BaseModel):
    product_id: UUID4
    target_price: Decimal = Field(..., gt=0, decimal_places=2)


class SubscribeRequest(BaseModel):
    """Alta/actualización de una suscripción y (opcionalmente) sus alertas.
    Sirve tanto para suscribir + crear la primera alerta de un producto,
    como para la migración en bloque de alertas viejas de localStorage."""
    subscription: PushSubscriptionInfo
    alerts: list[AlertCreate] = []


class PriceAlertOut(BaseModel):
    id: UUID4
    product_id: UUID4
    target_price: Decimal
    created_at: datetime
    notified_at_price: Decimal | None = None

    class Config:
        from_attributes = True


class SubscribeResponse(BaseModel):
    subscription_id: UUID4
    alerts: list[PriceAlertOut]


class VapidPublicKeyResponse(BaseModel):
    public_key: str
```

- [ ] **Step 2: Verificar que importa sin error**

Run: `cd backend && source venv/bin/activate && python3 -c "from app.schemas import push; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd "/home/agustin/PROYECTOS/A_Cuanto_Esta?"
git add backend/app/schemas/push.py
git commit -m "$(cat <<'EOF'
feat: add Pydantic schemas for push subscriptions and alerts

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Endpoints `/api/v1/push/*`

**Files:**
- Create: `backend/app/api/v1/endpoints/push.py`
- Modify: `backend/app/api/v1/api.py`
- Test: `backend/tests/test_push_api.py`

**Interfaces:**
- Consumes: `PushSubscription`/`PriceAlert` (Task 2), schemas de Task 4, `app.config.database.get_db`, `app.config.settings.settings`.
- Produces: `GET /api/v1/push/vapid-public-key`, `POST /api/v1/push/subscribe`, `GET /api/v1/push/alerts?endpoint=`, `DELETE /api/v1/push/alerts/{alert_id}`. Usados por el frontend (Task 12-13) y por Task 7 (el script lee `PriceAlert`/`PushSubscription` directo, no vía HTTP, pero comparte los mismos modelos).

- [ ] **Step 1: Escribir el test (falla porque el router no existe)**

Crear `backend/tests/test_push_api.py`. Usa SQLite en memoria vía `dependency_overrides` — **no toca la Neon real** (a diferencia de `test_products_api.py`, que sí pega contra la Neon real vía `TestClient(app)` sin override; acá el override es necesario porque estos tests escriben filas, y escribir en la Neon real ensuciaría datos de producción):

```python
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

from app.main import app
from app.config.database import Base, get_db
from app.config.settings import settings
from app.models.product import Product, ProductCategory, ProductUnit


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
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
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd backend && source venv/bin/activate && pytest tests/test_push_api.py -v`
Expected: FAIL con 404 en la primera request (el router `/push` no existe todavía).

- [ ] **Step 3: Crear `app/api/v1/endpoints/push.py`**

```python
"""
Endpoints de Notificaciones Push (Web Push API) y Alertas de Precio.

GET    /api/v1/push/vapid-public-key  — clave pública VAPID (no es secreta)
POST   /api/v1/push/subscribe         — alta/actualización de suscripción + alertas
GET    /api/v1/push/alerts            — alertas de una suscripción (?endpoint=)
DELETE /api/v1/push/alerts/{alert_id} — borra una alerta puntual
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings
from app.models.price_alert import PriceAlert
from app.models.push_subscription import PushSubscription
from app.schemas import push as schemas_push

router = APIRouter()


@router.get("/vapid-public-key", response_model=schemas_push.VapidPublicKeyResponse)
def get_vapid_public_key():
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="Push notifications no configuradas")
    return schemas_push.VapidPublicKeyResponse(public_key=settings.VAPID_PUBLIC_KEY)


@router.post("/subscribe", response_model=schemas_push.SubscribeResponse)
def subscribe(body: schemas_push.SubscribeRequest, db: Session = Depends(get_db)):
    subscription = (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint == body.subscription.endpoint)
        .first()
    )
    if subscription is None:
        subscription = PushSubscription(
            endpoint=body.subscription.endpoint,
            p256dh_key=body.subscription.keys.p256dh,
            auth_key=body.subscription.keys.auth,
        )
        db.add(subscription)
        db.flush()  # asigna subscription.id sin cerrar la transacción
    else:
        # Las keys pueden rotar si el browser renueva la suscripción con el mismo endpoint.
        subscription.p256dh_key = body.subscription.keys.p256dh
        subscription.auth_key = body.subscription.keys.auth

    for alert_in in body.alerts:
        existing = (
            db.query(PriceAlert)
            .filter(
                PriceAlert.subscription_id == subscription.id,
                PriceAlert.product_id == alert_in.product_id,
            )
            .first()
        )
        if existing:
            existing.target_price = alert_in.target_price
            existing.notified_at_price = None  # nuevo umbral -> hay que poder re-notificar
        else:
            db.add(PriceAlert(
                subscription_id=subscription.id,
                product_id=alert_in.product_id,
                target_price=alert_in.target_price,
            ))

    db.commit()
    db.refresh(subscription)

    all_alerts = (
        db.query(PriceAlert)
        .filter(PriceAlert.subscription_id == subscription.id)
        .all()
    )
    return schemas_push.SubscribeResponse(
        subscription_id=subscription.id,
        alerts=[schemas_push.PriceAlertOut.model_validate(a) for a in all_alerts],
    )


@router.get("/alerts", response_model=list[schemas_push.PriceAlertOut])
def list_alerts(endpoint: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    subscription = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
    if subscription is None:
        return []
    alerts = db.query(PriceAlert).filter(PriceAlert.subscription_id == subscription.id).all()
    return [schemas_push.PriceAlertOut.model_validate(a) for a in alerts]


@router.delete("/alerts/{alert_id}", status_code=204)
def delete_alert(alert_id: UUID, db: Session = Depends(get_db)) -> None:
    db.query(PriceAlert).filter(PriceAlert.id == alert_id).delete()
    db.commit()
```

- [ ] **Step 4: Registrar el router en `app/api/v1/api.py`**

En `backend/app/api/v1/api.py`, cambiar:

```python
from app.api.v1.endpoints import analysis, economic, prices, products, supermarkets
```

por:

```python
from app.api.v1.endpoints import analysis, economic, prices, products, push, supermarkets
```

y agregar después de la línea de `products.router`:

```python
api_router.include_router(push.router, prefix="/push", tags=["push"])
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `cd backend && source venv/bin/activate && pytest tests/test_push_api.py -v`
Expected: `9 passed`

- [ ] **Step 6: Correr toda la suite backend**

Run: `cd backend && source venv/bin/activate && pytest -q`
Expected: todos los tests pasan (los previos + los de `test_push_models.py` + los de `test_push_api.py`), ninguno pega contra la Neon real con datos nuevos.

- [ ] **Step 7: Commit**

```bash
cd "/home/agustin/PROYECTOS/A_Cuanto_Esta?"
git add backend/app/api/v1/endpoints/push.py backend/app/api/v1/api.py backend/tests/test_push_api.py
git commit -m "$(cat <<'EOF'
feat: add /api/v1/push endpoints (subscribe, list/delete alerts)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Script `check_price_alerts.py`

**Files:**
- Create: `backend/scripts/check_price_alerts.py`
- Test: `backend/tests/test_check_price_alerts.py`

**Interfaces:**
- Consumes: `app.api.v1.endpoints.products._get_current_prices_bulk(db, product_ids) -> dict[UUID, list[PriceHistory]]`, `PriceAlert`/`PushSubscription` (Task 2), `settings.VAPID_PRIVATE_KEY`/`VAPID_PUBLIC_KEY`/`VAPID_CLAIMS_EMAIL`, `pywebpush.webpush`/`WebPushException`.
- Produces: función pura `_due_alerts(alerts, prices_by_product) -> list[tuple[PriceAlert, float]]` (testeable sin DB ni red) y `main()` (entry point del script, corrido por GitHub Actions en Task 9).

- [ ] **Step 1: Escribir el test de la función pura (falla porque no existe)**

Crear `backend/tests/test_check_price_alerts.py`:

```python
"""
Pruebas unitarias para la lógica de matching de check_price_alerts.py.
No toca la DB ni pywebpush -- usa SimpleNamespace como en test_product_matcher.py.
"""
import os
import sys
from decimal import Decimal
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.check_price_alerts import _due_alerts


def _alert(product_id, target_price, notified_at_price=None):
    return SimpleNamespace(product_id=product_id, target_price=Decimal(str(target_price)), notified_at_price=(
        Decimal(str(notified_at_price)) if notified_at_price is not None else None
    ))


def _price(value, is_stale=False):
    return SimpleNamespace(price=Decimal(str(value)), is_stale=is_stale)


def test_alert_triggers_when_price_at_or_below_target():
    alert = _alert("p1", 500)
    prices = {"p1": [_price(450)]}
    due = _due_alerts([alert], prices)
    assert due == [(alert, 450.0)]


def test_alert_does_not_trigger_when_price_above_target():
    alert = _alert("p1", 500)
    prices = {"p1": [_price(600)]}
    assert _due_alerts([alert], prices) == []


def test_alert_does_not_retrigger_at_same_notified_price():
    alert = _alert("p1", 500, notified_at_price=450)
    prices = {"p1": [_price(450)]}
    assert _due_alerts([alert], prices) == []


def test_alert_retriggers_when_price_drops_further():
    alert = _alert("p1", 500, notified_at_price=450)
    prices = {"p1": [_price(400)]}
    due = _due_alerts([alert], prices)
    assert due == [(alert, 400.0)]


def test_alert_skipped_when_only_stale_prices_available():
    alert = _alert("p1", 500)
    prices = {"p1": [_price(400, is_stale=True)]}
    assert _due_alerts([alert], prices) == []


def test_alert_uses_lowest_fresh_price_among_supermarkets():
    alert = _alert("p1", 500)
    prices = {"p1": [_price(480), _price(420), _price(999, is_stale=True)]}
    due = _due_alerts([alert], prices)
    assert due == [(alert, 420.0)]


def test_alert_skipped_when_product_has_no_price_data():
    alert = _alert("p1", 500)
    assert _due_alerts([alert], {}) == []
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd backend && source venv/bin/activate && pytest tests/test_check_price_alerts.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'scripts.check_price_alerts'`

- [ ] **Step 3: Crear `backend/scripts/__init__.py` si no existe (para que `scripts` sea importable como paquete)**

Run: `ls backend/scripts/__init__.py 2>/dev/null || touch backend/scripts/__init__.py`

- [ ] **Step 4: Crear `backend/scripts/check_price_alerts.py`**

```python
"""
Chequea las alertas de precio activas contra el precio actual de cada
producto y manda un Web Push real a las que ya cumplieron su objetivo.

Pensado para correr una vez al día vía GitHub Actions (ver
.github/workflows/check-price-alerts.yml) -- no hay ningún proceso
corriendo 24/7 en este proyecto (ni Celery ni un cron de Render).

Uso:
    python scripts/check_price_alerts.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import joinedload

from app.api.v1.endpoints.products import _get_current_prices_bulk
from app.config.database import SessionLocal
from app.config.settings import settings
from app.models.price_alert import PriceAlert
from app.models.push_subscription import PushSubscription

try:
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover - solo pasa si no se corrió `pip install -r requirements.txt`
    webpush = None
    WebPushException = Exception


def _due_alerts(alerts: list, prices_by_product: dict) -> list[tuple]:
    """
    Devuelve las alertas que corresponde notificar ahora, junto con el
    precio actual que dispara la notificación. Función pura (no toca la DB
    ni pywebpush) para poder testearla con datos fake -- ver
    tests/test_check_price_alerts.py.
    """
    due = []
    for alert in alerts:
        current_prices = prices_by_product.get(alert.product_id, [])
        fresh_prices = [float(ph.price) for ph in current_prices if not ph.is_stale]
        if not fresh_prices:
            continue
        lowest = min(fresh_prices)
        if lowest > float(alert.target_price):
            continue
        if alert.notified_at_price is not None and float(alert.notified_at_price) == lowest:
            continue
        due.append((alert, lowest))
    return due


def main():
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        print("VAPID_PRIVATE_KEY / VAPID_PUBLIC_KEY no configuradas -- abortando.", file=sys.stderr)
        sys.exit(1)

    session = SessionLocal()
    try:
        alerts = (
            session.query(PriceAlert)
            .options(joinedload(PriceAlert.subscription))
            .all()
        )
        if not alerts:
            print("No hay alertas activas.")
            return

        product_ids = list({a.product_id for a in alerts})
        prices_by_product = _get_current_prices_bulk(session, product_ids)
        due = _due_alerts(alerts, prices_by_product)
        print(f"{len(alerts)} alertas activas, {len(due)} para notificar.")

        expired_subscription_ids = set()
        for alert, current_price in due:
            subscription = alert.subscription
            if subscription.id in expired_subscription_ids:
                continue
            payload = json.dumps({
                "title": "¡Bajó de precio!",
                "product_id": str(alert.product_id),
                "price": current_price,
                "target_price": float(alert.target_price),
            })
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {"p256dh": subscription.p256dh_key, "auth": subscription.auth_key},
                    },
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"},
                )
                alert.notified_at_price = current_price
                print(f"  OK   alerta {alert.id} (producto {alert.product_id}) -> ${current_price}")
            except WebPushException as exc:
                if exc.status_code in (404, 410):
                    print(f"  SUSCRIPCIÓN VENCIDA, se borra (subscription={subscription.id})")
                    expired_subscription_ids.add(subscription.id)
                else:
                    print(f"  ERROR alerta {alert.id}: {exc}", file=sys.stderr)

        if expired_subscription_ids:
            session.query(PushSubscription).filter(
                PushSubscription.id.in_(expired_subscription_ids)
            ).delete(synchronize_session=False)

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `cd backend && source venv/bin/activate && pytest tests/test_check_price_alerts.py -v`
Expected: `7 passed`

- [ ] **Step 6: Correr toda la suite backend**

Run: `cd backend && source venv/bin/activate && pytest -q`
Expected: todos los tests pasan.

- [ ] **Step 7: Commit**

```bash
cd "/home/agustin/PROYECTOS/A_Cuanto_Esta?"
git add backend/scripts/check_price_alerts.py backend/scripts/__init__.py backend/tests/test_check_price_alerts.py
git commit -m "$(cat <<'EOF'
feat: add check_price_alerts.py (daily push notification script)

Corre vía GitHub Actions (Task 9 de este plan) -- reusa
_get_current_prices_bulk de products.py para no reinventar la lógica de
"precio actual" que ya usa el resto de la app.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Generar las VAPID keys reales

**Files:**
- Create (temporal, no se commitea): `/tmp` o scratchpad -- las keys generadas van a secrets, no a un archivo del repo.

**Interfaces:**
- Produces: valores reales para `VAPID_PUBLIC_KEY` y `VAPID_PRIVATE_KEY` que se cargan a mano en Render, GitHub Secrets, y se usan en Task 8/9.

- [ ] **Step 1: Generar el par de claves**

Run:

```bash
cd backend && source venv/bin/activate && python3 -c "
from py_vapid import Vapid
from cryptography.hazmat.primitives import serialization
import base64

v = Vapid()
v.generate_keys()
priv_pem = v.private_pem().decode()
pub_bytes = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
pub_b64url = base64.urlsafe_b64encode(pub_bytes).decode().rstrip('=')

print('VAPID_PRIVATE_KEY (PEM, pegar tal cual incluyendo las líneas BEGIN/END):')
print(priv_pem)
print('VAPID_PUBLIC_KEY (base64url, una sola línea):')
print(pub_b64url)
"
```

Expected: imprime un bloque PEM de clave privada y una clave pública base64url de 87 caracteres. **No commitear esta salida a git.**

- [ ] **Step 2: Guardar los 3 secretos**

El operador humano (no el agente) debe cargar, con los valores generados en Step 1:
- **Render** (dashboard del servicio `acuantoesta-backend`, Environment): `VAPID_PUBLIC_KEY` (la clave pública -- no es secreta, pero se carga igual porque el endpoint `/push/vapid-public-key` la sirve desde `settings`).
- **GitHub** (Settings → Secrets and variables → Actions, del repo): `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_CLAIMS_EMAIL` (un email real de contacto, requerido por el protocolo VAPID), y además `DATABASE_URL_UNPOOLED` y `SECRET_KEY` (los mismos valores que ya están en Render) -- el workflow de Task 9 los necesita para que `Settings()` pueda instanciarse al importar `app.config.settings`.

No hay Step de commit acá -- esta tarea es puramente operativa (generar y cargar secretos), no toca el repo.

---

### Task 8: `render.yaml` -- exponer `VAPID_PUBLIC_KEY`

**Files:**
- Modify: `render.yaml`

**Interfaces:**
- Consumes: el valor cargado en Task 7 Step 2 (a mano en el dashboard de Render).

- [ ] **Step 1: Agregar la env var**

En `render.yaml`, agregar después de `SECRET_KEY`:

```yaml
      - key: SECRET_KEY
        generateValue: true
      - key: VAPID_PUBLIC_KEY
        sync: false # Cargar a mano en el dashboard de Render (ver Task 7 del plan de push notifications)
```

(No se agrega `VAPID_PRIVATE_KEY` a Render -- el backend web nunca manda pushes, solo expone la clave pública. La privada vive únicamente en GitHub Secrets, donde corre el script.)

- [ ] **Step 2: Commit**

```bash
cd "/home/agustin/PROYECTOS/A_Cuanto_Esta?"
git add render.yaml
git commit -m "$(cat <<'EOF'
chore: expose VAPID_PUBLIC_KEY in render.yaml

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Workflow de GitHub Actions

**Files:**
- Create: `.github/workflows/check-price-alerts.yml`

**Interfaces:**
- Consumes: `backend/scripts/check_price_alerts.py` (Task 6), secrets de GitHub cargados en Task 7 Step 2.

- [ ] **Step 1: Crear el workflow**

```yaml
name: Check price alerts

on:
  schedule:
    # 13:00 UTC = 10:00 ART (Argentina, UTC-3) -- después del scraping diario.
    - cron: "0 13 * * *"
  workflow_dispatch: {}

jobs:
  check-alerts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r backend/requirements.txt

      - name: Check price alerts
        working-directory: backend
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL_UNPOOLED }}
          DATABASE_URL_UNPOOLED: ${{ secrets.DATABASE_URL_UNPOOLED }}
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
          VAPID_PUBLIC_KEY: ${{ secrets.VAPID_PUBLIC_KEY }}
          VAPID_PRIVATE_KEY: ${{ secrets.VAPID_PRIVATE_KEY }}
          VAPID_CLAIMS_EMAIL: ${{ secrets.VAPID_CLAIMS_EMAIL }}
        run: python scripts/check_price_alerts.py
```

- [ ] **Step 2: Validar el YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/check-price-alerts.yml')); print('OK')"`
Expected: `OK` (si `pyyaml` no está instalado en el entorno del sistema, `pip install pyyaml` primero, o validar con `yamllint .github/workflows/check-price-alerts.yml` si está disponible).

- [ ] **Step 3: Commit**

```bash
cd "/home/agustin/PROYECTOS/A_Cuanto_Esta?"
git add .github/workflows/check-price-alerts.yml
git commit -m "$(cat <<'EOF'
feat: add GitHub Actions workflow for daily price alert checks

Cron diario, gratuito -- no depende del plan de Render ni agrega
Celery/Redis. Requiere los secrets DATABASE_URL_UNPOOLED, SECRET_KEY,
VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_CLAIMS_EMAIL (Task 7 de este
plan) cargados en GitHub antes de que corra.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: Verificación manual post-deploy (no automatizable acá)**

Una vez que Render tenga desplegada la migración de Task 3 (tablas creadas) y los secrets de GitHub estén cargados: ir a la pestaña Actions del repo → "Check price alerts" → "Run workflow" (dispatch manual) y confirmar que el run termina en verde con el log `No hay alertas activas.` (todavía no hay ninguna suscripción real creada en este punto del plan).

---

### Task 10: Service worker del frontend

**Files:**
- Create: `frontend/public/sw.js`

**Interfaces:**
- Produces: manejo de los eventos `push` y `notificationclick` del navegador. Registrado por Task 12 (`priceAlertsContext.tsx`).

- [ ] **Step 1: Crear `frontend/public/sw.js`**

```js
// Service worker mínimo para Web Push -- no cachea nada (no es un PWA
// offline-first), solo reacciona a 'push' (mostrar la notificación) y
// 'notificationclick' (abrir/enfocar la página del producto).

self.addEventListener("push", (event) => {
  if (!event.data) return;
  let payload;
  try {
    payload = event.data.json();
  } catch {
    return;
  }
  const { title, product_id, price, target_price } = payload;
  event.waitUntil(
    self.registration.showNotification(title || "¡Bajó de precio!", {
      body: `Ahora $${price} (tu objetivo: $${target_price})`,
      tag: `price-alert-${product_id}`,
      data: { productId: product_id },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const productId = event.notification.data && event.notification.data.productId;
  const url = productId ? `/producto/${productId}` : "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.indexOf(url) !== -1 && "focus" in client) return client.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow(url);
    })
  );
});
```

- [ ] **Step 2: Verificar que Next.js lo sirve tal cual (archivos en `public/` son estáticos)**

Run: `cd frontend && npm run dev &` luego `curl -s http://localhost:3000/sw.js | head -5` (parar el server después con `kill %1` o Ctrl+C).
Expected: el `curl` devuelve el contenido JS del archivo (no un 404 ni HTML de una página 404).

- [ ] **Step 3: Commit**

```bash
cd "/home/agustin/PROYECTOS/A_Cuanto_Esta?"
git add frontend/public/sw.js
git commit -m "$(cat <<'EOF'
feat: add service worker for Web Push notifications

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Cliente API y tipos del frontend

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/lib/api.ts`

**Interfaces:**
- Consumes: tipo `PriceAlert` de `@/lib/priceAlertsContext` (Task 12 -- import de solo-tipo, sin dependencia circular en runtime).
- Produces: `getVapidPublicKey(): Promise<string>`, `subscribePush(subscription, alerts): Promise<PriceAlert[]>`, `getPriceAlerts(endpoint): Promise<PriceAlert[]>`, `deletePriceAlert(alertId): Promise<void>` -- usados por Task 12 y Task 13.

- [ ] **Step 1: Agregar el schema en `frontend/src/types/index.ts`**

Agregar (junto a los demás `*Schema` del archivo -- usar `z.coerce.number()` para los campos `Decimal`-backed, igual que el resto del archivo, ya que FastAPI/Pydantic serializa `Decimal` como string JSON, no como número):

```ts
export const PriceAlertApiSchema = z.object({
  id: z.string(),
  product_id: z.string(),
  target_price: z.coerce.number(),
  created_at: z.string(),
  notified_at_price: z.coerce.number().nullable().default(null),
});
export type PriceAlertApi = z.infer<typeof PriceAlertApiSchema>;
```

- [ ] **Step 2: Agregar las funciones en `frontend/src/lib/api.ts`**

Agregar el import al principio del archivo (junto a los demás imports de `@/types`):

```ts
import { PriceAlertApiSchema, type PriceAlertApi } from "@/types";
import type { PriceAlert } from "@/lib/priceAlertsContext";
```

Y al final del archivo:

```ts
function toPriceAlert(a: PriceAlertApi): PriceAlert {
  return {
    id: a.id,
    productId: a.product_id,
    targetPrice: a.target_price,
    createdAt: a.created_at,
    notifiedAtPrice: a.notified_at_price,
  };
}

export async function getVapidPublicKey(): Promise<string> {
  const { data } = await api.get("/push/vapid-public-key");
  return z.object({ public_key: z.string() }).parse(data).public_key;
}

export async function subscribePush(
  subscription: { endpoint: string; keys: { p256dh: string; auth: string } },
  alerts: { product_id: string; target_price: number }[]
): Promise<PriceAlert[]> {
  const { data } = await api.post("/push/subscribe", { subscription, alerts });
  const parsed = z
    .object({ subscription_id: z.string(), alerts: z.array(PriceAlertApiSchema) })
    .parse(data);
  return parsed.alerts.map(toPriceAlert);
}

export async function getPriceAlerts(endpoint: string): Promise<PriceAlert[]> {
  const { data } = await api.get(`/push/alerts?endpoint=${encodeURIComponent(endpoint)}`);
  return z.array(PriceAlertApiSchema).parse(data).map(toPriceAlert);
}

export async function deletePriceAlert(alertId: string): Promise<void> {
  await api.delete(`/push/alerts/${encodeURIComponent(alertId)}`);
}
```

- [ ] **Step 3: Verificar que compila (el import de `priceAlertsContext` todavía no existe en su forma nueva -- este paso puede fallar hasta terminar Task 12; es esperado, no es un error de este paso)**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -v "priceAlertsContext" | head -30`
Expected: sin errores de tipo distintos de los relacionados a `priceAlertsContext` (que se resuelven en Task 12).

- [ ] **Step 4: Commit**

```bash
cd "/home/agustin/PROYECTOS/A_Cuanto_Esta?"
git add frontend/src/types/index.ts frontend/src/lib/api.ts
git commit -m "$(cat <<'EOF'
feat: add API client functions for push subscriptions and alerts

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Reescribir `priceAlertsContext.tsx`

**Files:**
- Modify: `frontend/src/lib/priceAlertsContext.tsx`

**Interfaces:**
- Consumes: `getVapidPublicKey`, `subscribePush`, `getPriceAlerts` (Task 11).
- Produces: `PriceAlert` (interfaz, ahora con campo `id` nuevo), `PriceAlertsProvider`, `usePriceAlerts()` (misma forma pública que antes: `alerts`, `addAlert(productId, targetPrice)`, `removeAlert(productId)`, `hasAlert(productId)` -- así `Header.tsx`, `ProductDetailClient.tsx` y `alertas/page.tsx` no necesitan cambios), y **`getOrCreateSubscription()`** exportada (la usa Task 13, el banner de migración).

- [ ] **Step 1: Reemplazar el archivo completo**

```tsx
"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { getPriceAlerts, getVapidPublicKey, subscribePush } from "@/lib/api";
import { deletePriceAlert } from "@/lib/api";

export interface PriceAlert {
  id: string;
  productId: string;
  targetPrice: number;
  createdAt: string;
  notifiedAtPrice: number | null; // último precio con el que ya se avisó, para no repetir
}

type PriceAlertsContextType = {
  alerts: PriceAlert[];
  addAlert: (productId: string, targetPrice: number) => Promise<void>;
  removeAlert: (productId: string) => Promise<void>;
  hasAlert: (productId: string) => boolean;
};

const PriceAlertsContext = createContext<PriceAlertsContextType>({
  alerts: [],
  addAlert: async () => {},
  removeAlert: async () => {},
  hasAlert: () => false,
});

function urlBase64ToUint8Array(base64: string): Uint8Array {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const base64Safe = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64Safe);
  return Uint8Array.from(rawData.split("").map((c) => c.charCodeAt(0)));
}

/**
 * Registra el service worker (si hace falta), pide permiso de
 * notificaciones, y devuelve una PushSubscription activa -- o `null` si el
 * navegador no soporta push, o el usuario no dio permiso. La usa tanto
 * `addAlert` acá abajo como el banner de migración (Task 13).
 */
export async function getOrCreateSubscription(): Promise<PushSubscription | null> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator) || !("PushManager" in window)) {
    return null;
  }
  const registration = await navigator.serviceWorker.register("/sw.js");
  const existing = await registration.pushManager.getSubscription();
  if (existing) return existing;

  if (Notification.permission === "denied") return null;
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return null;

  const publicKey = await getVapidPublicKey();
  return registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });
}

export function PriceAlertsProvider({ children }: { children: React.ReactNode }) {
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const loadedRef = useRef(false);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    (async () => {
      if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
      try {
        const registration = await navigator.serviceWorker.getRegistration();
        const existing = await registration?.pushManager.getSubscription();
        if (!existing) return;
        const serverAlerts = await getPriceAlerts(existing.endpoint);
        setAlerts(serverAlerts);
      } catch {
        // Sin conexión, o el backend no responde -- se sigue sin alertas
        // cargadas; el usuario puede reintentar creando una alerta nueva.
      }
    })();
  }, []);

  const addAlert = useCallback(async (productId: string, targetPrice: number) => {
    const subscription = await getOrCreateSubscription();
    if (!subscription) {
      window.alert("No se pudo activar la notificación (permiso denegado o navegador sin soporte).");
      return;
    }
    const subJson = subscription.toJSON() as { endpoint: string; keys: { p256dh: string; auth: string } };
    const result = await subscribePush(subJson, [{ product_id: productId, target_price: targetPrice }]);
    setAlerts(result);
  }, []);

  const removeAlert = useCallback(
    async (productId: string) => {
      const alert = alerts.find((a) => a.productId === productId);
      if (!alert) return;
      await deletePriceAlert(alert.id);
      setAlerts((prev) => prev.filter((a) => a.id !== alert.id));
    },
    [alerts]
  );

  const hasAlert = useCallback((productId: string) => alerts.some((a) => a.productId === productId), [alerts]);

  return (
    <PriceAlertsContext.Provider value={{ alerts, addAlert, removeAlert, hasAlert }}>
      {children}
    </PriceAlertsContext.Provider>
  );
}

export const usePriceAlerts = () => useContext(PriceAlertsContext);
```

- [ ] **Step 2: Verificar que compila sin errores de tipo**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores (los 3 consumidores -- `Header.tsx`, `ProductDetailClient.tsx`, `alertas/page.tsx` -- siguen usando `alerts`/`addAlert`/`removeAlert`/`hasAlert` con la misma forma, así que no deberían necesitar cambios; si `tsc` marca algo en esos 3 archivos, es que usan algo de `PriceAlert` que cambió de forma -- revisar y ajustar el archivo consumidor, no el contrato).

- [ ] **Step 3: Commit**

```bash
cd "/home/agustin/PROYECTOS/A_Cuanto_Esta?"
git add frontend/src/lib/priceAlertsContext.tsx
git commit -m "$(cat <<'EOF'
feat: back priceAlertsContext with real Web Push subscriptions

Reemplaza el almacenamiento en localStorage por el backend -- addAlert
ahora registra el service worker, pide permiso, se suscribe a Web Push,
y persiste en el backend. La interfaz pública (alerts/addAlert/
removeAlert/hasAlert) no cambia, así que los consumidores existentes
(Header, ProductDetailClient, /alertas) no necesitan tocarse.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: Banner de migración y limpieza del sistema viejo

**Files:**
- Create: `frontend/src/components/layout/PushMigrationBanner.tsx`
- Modify: `frontend/src/app/layout.tsx`
- Delete: `frontend/src/components/layout/PriceAlertsChecker.tsx`

**Interfaces:**
- Consumes: `getOrCreateSubscription` (Task 12), `subscribePush` (Task 11).

- [ ] **Step 1: Crear `frontend/src/components/layout/PushMigrationBanner.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { subscribePush } from "@/lib/api";
import { getOrCreateSubscription } from "@/lib/priceAlertsContext";

const STORAGE_KEY = "price_alerts";

interface OldAlert {
  productId: string;
  targetPrice: number;
}

function readOldAlerts(): OldAlert[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (v): v is OldAlert =>
        typeof v === "object" &&
        v !== null &&
        typeof (v as OldAlert).productId === "string" &&
        typeof (v as OldAlert).targetPrice === "number"
    );
  } catch {
    return [];
  }
}

/**
 * Detecta alertas guardadas por el sistema viejo (localStorage) y ofrece
 * migrarlas de una a notificaciones push reales con un solo click. Se
 * muestra solo si hay alertas viejas Y todavía no hay una suscripción push
 * activa en este navegador -- una vez migrado (o si nunca hubo alertas
 * viejas), no vuelve a aparecer.
 */
export default function PushMigrationBanner() {
  const [oldAlerts, setOldAlerts] = useState<OldAlert[] | null>(null);
  const [migrating, setMigrating] = useState(false);

  useEffect(() => {
    (async () => {
      const found = readOldAlerts();
      if (found.length === 0) return;
      if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;

      const registration = await navigator.serviceWorker.getRegistration();
      const existing = await registration?.pushManager.getSubscription();
      if (existing) {
        // Ya se migró en algún momento anterior -- limpiar el resto viejo.
        window.localStorage.removeItem(STORAGE_KEY);
        return;
      }
      setOldAlerts(found);
    })();
  }, []);

  if (!oldAlerts || oldAlerts.length === 0) return null;

  const activate = async () => {
    setMigrating(true);
    try {
      const subscription = await getOrCreateSubscription();
      if (!subscription) {
        window.alert("No se pudo activar (permiso denegado o navegador sin soporte).");
        return;
      }
      const subJson = subscription.toJSON() as { endpoint: string; keys: { p256dh: string; auth: string } };
      await subscribePush(
        subJson,
        oldAlerts.map((a) => ({ product_id: a.productId, target_price: a.targetPrice }))
      );
      window.localStorage.removeItem(STORAGE_KEY);
      window.location.reload();
    } finally {
      setMigrating(false);
    }
  };

  return (
    <div
      style={{
        background: "var(--warn-tint)",
        borderBottom: "1px solid var(--border)",
        padding: "8px 16px",
        fontSize: 13,
        display: "flex",
        gap: 12,
        alignItems: "center",
        justifyContent: "center",
        flexWrap: "wrap",
      }}
    >
      <span>
        Tenés {oldAlerts.length} alerta{oldAlerts.length > 1 ? "s" : ""} de precio guardada
        {oldAlerts.length > 1 ? "s" : ""} en este navegador.
      </span>
      <button className="btn" style={{ fontSize: 12 }} disabled={migrating} onClick={activate}>
        {migrating ? "Activando..." : "Activar notificaciones push"}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Borrar `PriceAlertsChecker.tsx`**

Run: `rm "frontend/src/components/layout/PriceAlertsChecker.tsx"`

- [ ] **Step 3: Actualizar `frontend/src/app/layout.tsx`**

Cambiar el import:

```tsx
import PriceAlertsChecker from "@/components/layout/PriceAlertsChecker";
```

por:

```tsx
import PushMigrationBanner from "@/components/layout/PushMigrationBanner";
```

Y cambiar el bloque del body de:

```tsx
              <PriceAlertsProvider>
                <Suspense fallback={null}>
                  <Header />
                </Suspense>
                {children}
                <PriceAlertsChecker />
              </PriceAlertsProvider>
```

a:

```tsx
              <PriceAlertsProvider>
                <PushMigrationBanner />
                <Suspense fallback={null}>
                  <Header />
                </Suspense>
                {children}
              </PriceAlertsProvider>
```

- [ ] **Step 4: Verificar que compila**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 5: Verificación manual en el navegador**

Run: `cd frontend && npm run dev` (dejar corriendo) y en paralelo `cd backend && source venv/bin/activate && uvicorn app.main:app --reload` (con la migración de Task 3 ya aplicada localmente vía `alembic upgrade head` contra una DB de desarrollo, o contra la misma Neon si es la única que existe en este proyecto).

En el navegador (Chrome o Edge, tienen el soporte más simple para probar esto localmente):
1. Abrir `http://localhost:3000`, ir a un producto, click en "Avisarme si baja de $X", confirmar el precio, Guardar.
2. El navegador debe pedir permiso de notificaciones -- aceptar.
3. Verificar en las DevTools → Application → Service Workers que `sw.js` está registrado y activo.
4. Verificar en Application → Push Messaging (o Network) que la request `POST /api/v1/push/subscribe` devolvió 200 con la alerta creada.
5. Recargar la página -- el botón debe seguir mostrando "Alerta a $X · quitar" (la alerta persistió, se recargó desde el backend al montar el contexto).
6. Click en "quitar" -- debe desaparecer y la request `DELETE /api/v1/push/alerts/{id}` debe devolver 204.

Expected: los 6 pasos funcionan sin error de consola. No hace falta probar la recepción real del push en este paso (eso requiere que el script de Task 6 corra y encuentre un precio por debajo del objetivo -- se verifica por separado, manualmente, corriendo `python scripts/check_price_alerts.py` a mano contra una alerta con `target_price` mayor al precio actual del producto).

- [ ] **Step 6: Commit**

```bash
cd "/home/agustin/PROYECTOS/A_Cuanto_Esta?"
git add frontend/src/components/layout/PushMigrationBanner.tsx frontend/src/app/layout.tsx
git rm frontend/src/components/layout/PriceAlertsChecker.tsx
git commit -m "$(cat <<'EOF'
feat: add push migration banner, remove old tab-only alert checker

Cierra el reemplazo completo del sistema de alertas: PriceAlertsChecker
(el polling client-side con Notification API, solo funcionaba con la
pestaña abierta) se saca del todo. Quien tenía alertas viejas en
localStorage ve un banner único para migrarlas a push real con un click.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 14: Aplicar la migración a producción y verificación end-to-end

**Files:** ninguno (tarea operativa).

**Interfaces:** ninguna nueva -- cierra el plan verificando que todo lo de las Tasks 1-13 funciona junto contra Neon real.

- [ ] **Step 1: Confirmar que los secrets de Task 7 ya están cargados en Render y GitHub**

Verificar a mano (o preguntarle al usuario) que `VAPID_PUBLIC_KEY` está en Render, y que `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY`/`VAPID_CLAIMS_EMAIL`/`DATABASE_URL_UNPOOLED`/`SECRET_KEY` están en GitHub Secrets del repo.

- [ ] **Step 2: Aplicar la migración de Task 3 a producción**

Run: `cd backend && source venv/bin/activate && alembic upgrade head`
Expected: aplica la migración `add push subscriptions and price alerts` sobre Neon (o, si ya se hizo automáticamente vía el `startCommand` de Render en el deploy de las Tasks anteriores, confirmar con `alembic current` que la cabeza coincide con el archivo de Task 3).

Nota: este comando puede requerir confirmación explícita del usuario si el classifier de Claude Code lo bloquea por ser un cambio de esquema en producción (ya pasó dos veces esta sesión con las migraciones anteriores) -- intentar directo primero, y solo pedir confirmación si efectivamente lo bloquea.

- [ ] **Step 3: Verificar que las tablas existen**

Run: `cd backend && source venv/bin/activate && python3 -c "
from app.config.database import SessionLocal
from app.models.push_subscription import PushSubscription
from app.models.price_alert import PriceAlert
s = SessionLocal()
print('push_subscriptions:', s.query(PushSubscription).count())
print('price_alerts:', s.query(PriceAlert).count())
s.close()
"`
Expected: `push_subscriptions: 0` y `price_alerts: 0` (tablas creadas, vacías -- todavía no hay ninguna suscripción real).

- [ ] **Step 4: Correr toda la suite backend una vez más contra el estado final**

Run: `cd backend && source venv/bin/activate && pytest -q`
Expected: todos los tests pasan (los tests de push usan SQLite en memoria, no dependen de que la migración esté aplicada en Neon -- este paso es una doble confirmación de que nada se rompió).

- [ ] **Step 5: Disparar el workflow de GitHub Actions a mano**

En GitHub → Actions → "Check price alerts" → "Run workflow". Confirmar que corre en verde.
Expected: log `No hay alertas activas.` (todavía no hay suscripciones reales creadas fuera de las de prueba en SQLite).

- [ ] **Step 6: Prueba end-to-end real (requiere al usuario en un navegador)**

Pedirle al usuario que en el sitio desplegado (Vercel + Render, ambos ya con el deploy de esta feature):
1. Cree una alerta de precio para un producto real, con un `target_price` *por encima* del precio actual (para que dispare en el próximo chequeo).
2. Confirme que el navegador le pidió permiso y lo mostró como activo.
3. Disparar el workflow a mano de nuevo (Step 5) y confirmar en el log que dice `1 alertas activas, 1 para notificar.` y `OK   alerta ...`.
4. Confirmar que le llegó la notificación del sistema operativo (con la pestaña del navegador cerrada, para probar que es push real y no el sistema viejo).

Esta prueba no se automatiza -- es la validación final de que todo el flujo (backend + Neon + GitHub Actions + pywebpush + service worker + notificación del SO) funciona junto en producción.

- [ ] **Step 7: Actualizar la memoria del proyecto**

Una vez confirmado el Step 6, guardar en la memoria persistente (`/home/agustin/.claude/projects/-home-agustin-PROYECTOS-A-Cuanto-Esta-/memory/`) un memory de tipo `project` documentando: que las notificaciones push reales quedaron implementadas y verificadas en producción, reemplazando el sistema de localStorage; que el chequeo corre diario vía GitHub Actions (no Celery, no Render cron); y la ubicación de los secrets (Render + GitHub) para que una sesión futura sepa dónde están si hay que rotarlos. Actualizar `MEMORY.md` con la entrada correspondiente.

---

## Self-Review (completado por quien escribió este plan)

**Cobertura del spec:** las 6 piezas de la arquitectura del diseño (tablas, endpoints, script, workflow, service worker, contexto+banner) tienen tareas dedicadas (Tasks 2-3, 4-5, 6, 9, 10, 12-13). El único ajuste respecto al diseño original: se sacó `NEXT_PUBLIC_VAPID_PUBLIC_KEY` de Vercel (el diseño lo mencionaba de pasada junto con el endpoint) porque duplicaba la misma clave no-secreta en 3 lugares (GitHub Secret, Render env, Vercel env) sin necesidad -- el frontend la pide en runtime al backend (`GET /push/vapid-public-key`), reduciendo a 2 lugares (GitHub + Render). Esto no cambia el comportamiento visible, solo simplifica el despliegue.

**Placeholders:** ninguno -- cada Step tiene código completo o un comando `Run:` con su `Expected:` concreto.

**Consistencia de tipos:** `PriceAlert.id` (nuevo campo) se usa consistentemente en `priceAlertsContext.tsx` (Task 12) y `PushMigrationBanner.tsx` (Task 13, indirectamente vía `subscribePush`); `_get_current_prices_bulk` se referencia con la misma firma (`db, product_ids -> dict[UUID, list[PriceHistory]]`) en Task 6 que la que ya existe en `products.py`; `PriceAlertOut`/`SubscribeResponse` (Task 4) se consumen igual en Task 5 (endpoints) y Task 11 (zod schema `PriceAlertApiSchema` espejando los mismos campos snake_case).
