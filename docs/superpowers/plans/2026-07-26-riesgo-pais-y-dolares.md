# Riesgo País y Todos los Dólares — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar el indicador "riesgo país" (nunca conectado pese a estar modelado) y expandir "dólar" de 2 casas (blue/oficial) a las 7 casas activas, en el backend (FastAPI + SQLAlchemy + Alembic) y el frontend (Next.js 14).

**Architecture:** El backend ya tiene modelo/schema/endpoint parcialmente listos para riesgo país; se completa el pipeline cliente→processor→script→endpoint. Para dólares, se reemplaza la combinación de 2 endpoints históricos (blue/oficial) por 1 solo endpoint de ArgentinaDatos que trae las 7 casas con histórico completo, y se agregan 3 valores nuevos al enum `IndicatorType` vía migración manual de Alembic (Postgres no autogenera `ALTER TYPE ADD VALUE`). El frontend consume todo esto vía el endpoint `/context` ya existente (extendido) más un endpoint nuevo para el histórico de riesgo país.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, pytest, Next.js 14 (App Router), TanStack Query, TypeScript.

**Spec:** `docs/superpowers/specs/2026-07-26-riesgo-pais-y-dolares-design.md`

## Global Constraints

- El proyecto no tiene infraestructura de tests contra base de datos real (sin Postgres de test, sin fixtures, `tests/` solo tiene `__init__.py`). Los modelos usan tipos nativos de Postgres (`UUID`, `Enum`) que no funcionan igual contra SQLite, así que no se arma una suite de tests con DB en este plan.
  - Las tareas que solo hacen HTTP + parseo (sin DB) **sí** llevan tests reales con pytest (mockeando `httpx.get`).
  - Las tareas que tocan la base de datos se verifican manualmente contra la base **local** (`acuantoesta`, no Supabase) con scripts ad-hoc, siguiendo el mismo patrón que ya usa el proyecto (`scripts/fetch_economic_data.py`, `scripts/populate_*.py`).
  - El backfill real contra Supabase (producción) es un paso explícito y tardío del plan (Task 4), después de validar todo localmente.
- `DATABASE_URL` local está en `backend/.env` apuntando a la base local `acuantoesta` (usuario `acuanto_user`). La de Supabase (pooler) está guardada aparte — cuando una tarea diga "contra Supabase", hay que usar esa, no la local.
- Todo el código Python corre desde `backend/` con el venv activado: `cd backend && source venv/bin/activate`.
- Correr pytest con: `cd backend && python3 -m pytest -v` (el binario se llama `python3` en este entorno, no `python`).

---

### Task 1: Cliente ArgentinaDatos — `get_risk_country()` y `get_all_dollars()`

**Files:**
- Modify: `backend/app/services/economic_data/client.py:59` (agregar después de `get_inflation_yearly`, antes de `class DolarAPIClient`)
- Create: `backend/tests/test_economic_data_client.py`

**Interfaces:**
- Produces: `ArgentinaDatosClient.get_risk_country() -> list[InflationRecord]`, `ArgentinaDatosClient.get_all_dollars() -> list[DollarRecord]` (ambos reutilizan schemas ya existentes en `app/services/economic_data/schemas.py`, no se crean schemas nuevos)

- [ ] **Step 1: Escribir los tests (van a fallar — los métodos no existen todavía)**

Crear `backend/tests/test_economic_data_client.py`:

```python
"""Tests para los métodos nuevos de ArgentinaDatosClient: riesgo país y todos los dólares."""
import httpx
from unittest.mock import MagicMock, patch

from app.services.economic_data.client import ArgentinaDatosClient


def _fake_response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_get_risk_country_parses_response():
    payload = [
        {"fecha": "2026-07-24", "valor": 437},
        {"fecha": "2026-07-23", "valor": 437},
    ]
    with patch(
        "app.services.economic_data.client.httpx.get",
        return_value=_fake_response(payload),
    ) as mock_get:
        client = ArgentinaDatosClient()
        records = client.get_risk_country()

    called_url = mock_get.call_args[0][0]
    assert called_url.endswith("/v1/finanzas/indices/riesgo-pais")
    assert len(records) == 2
    assert records[0].valor == 437
    assert records[0].fecha.isoformat() == "2026-07-24"


def test_get_risk_country_returns_empty_list_on_error():
    with patch(
        "app.services.economic_data.client.httpx.get",
        side_effect=httpx.ConnectError("boom"),
    ):
        client = ArgentinaDatosClient()
        records = client.get_risk_country()

    assert records == []


def test_get_all_dollars_parses_multiple_casas():
    payload = [
        {"casa": "blue", "compra": 1300.0, "venta": 1320.0, "fecha": "2026-07-24"},
        {"casa": "mayorista", "compra": 1000.0, "venta": 1005.0, "fecha": "2026-07-24"},
    ]
    with patch(
        "app.services.economic_data.client.httpx.get",
        return_value=_fake_response(payload),
    ) as mock_get:
        client = ArgentinaDatosClient()
        records = client.get_all_dollars()

    called_url = mock_get.call_args[0][0]
    assert called_url.endswith("/v1/cotizaciones/dolares")
    assert len(records) == 2
    assert {r.casa for r in records} == {"blue", "mayorista"}
    assert [r.venta for r in records if r.casa == "blue"][0] == 1320.0
```

- [ ] **Step 2: Correr los tests y confirmar que fallan**

Run: `cd backend && python3 -m pytest tests/test_economic_data_client.py -v`
Expected: FAIL — `AttributeError: 'ArgentinaDatosClient' object has no attribute 'get_risk_country'`

- [ ] **Step 3: Implementar los métodos**

En `backend/app/services/economic_data/client.py`, agregar después del método `get_inflation_yearly` (línea 59) y antes de `class DolarAPIClient:`:

```python

    def get_risk_country(self) -> list[InflationRecord]:
        """Riesgo país (EMBI+). Mismo shape que inflación: {fecha, valor}."""
        data = self._get("/v1/finanzas/indices/riesgo-pais")
        if data is None:
            return []
        return [InflationRecord(**item) for item in data]

    def get_all_dollars(self) -> list[DollarRecord]:
        """Histórico combinado de las 8 casas de cambio en una sola llamada."""
        data = self._get("/v1/cotizaciones/dolares")
        if data is None:
            return []
        return [DollarRecord(**item) for item in data]
```

- [ ] **Step 4: Correr los tests y confirmar que pasan**

Run: `cd backend && python3 -m pytest tests/test_economic_data_client.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/economic_data/client.py backend/tests/test_economic_data_client.py
git commit -m "feat: agregar get_risk_country y get_all_dollars a ArgentinaDatosClient"
```

---

### Task 2: Migración — nuevos valores de `IndicatorType`

**Files:**
- Modify: `backend/app/models/economic_indicator.py:20` (después de `DOLLAR_CCL`)
- Create: `backend/alembic/versions/d2e4f6a8b0c2_add_dollar_mayorista_cripto_tarjeta.py`

**Interfaces:**
- Produces: `IndicatorType.DOLLAR_MAYORISTA`, `IndicatorType.DOLLAR_CRIPTO`, `IndicatorType.DOLLAR_TARJETA` (usados por Task 3 y Task 5)

**Nota técnica:** el tipo nativo de Postgres se llama `indicatortype` y guarda el **nombre** del miembro del enum en mayúsculas (ej. `'DOLLAR_MEP'`), no el `.value` en minúsculas — confirmado con `\dT+ indicatortype` contra la base real. Ya hay un precedente idéntico en el repo: `alembic/versions/9b1c3d5e7f8a_add_chango_mas_to_supermarket_enum.py`, que se sigue al pie de la letra acá.

- [ ] **Step 1: Agregar los valores al enum del modelo**

En `backend/app/models/economic_indicator.py`, reemplazar:

```python
    DOLLAR_MEP = "dollar_mep"                # Dólar MEP
    DOLLAR_CCL = "dollar_ccl"                # Dólar CCL
```

por:

```python
    DOLLAR_MEP = "dollar_mep"                # Dólar MEP
    DOLLAR_CCL = "dollar_ccl"                # Dólar CCL
    DOLLAR_MAYORISTA = "dollar_mayorista"    # Dólar mayorista
    DOLLAR_CRIPTO = "dollar_cripto"          # Dólar cripto
    DOLLAR_TARJETA = "dollar_tarjeta"        # Dólar tarjeta
```

- [ ] **Step 2: Crear la migración**

Crear `backend/alembic/versions/d2e4f6a8b0c2_add_dollar_mayorista_cripto_tarjeta.py`:

```python
"""add_dollar_mayorista_cripto_tarjeta

Revision ID: d2e4f6a8b0c2
Revises: 7aadc53c1d48
Create Date: 2026-07-26
"""
from alembic import op

revision = 'd2e4f6a8b0c2'
down_revision = '7aadc53c1d48'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE indicatortype ADD VALUE IF NOT EXISTS 'DOLLAR_MAYORISTA'")
    op.execute("ALTER TYPE indicatortype ADD VALUE IF NOT EXISTS 'DOLLAR_CRIPTO'")
    op.execute("ALTER TYPE indicatortype ADD VALUE IF NOT EXISTS 'DOLLAR_TARJETA'")


def downgrade():
    pass  # PostgreSQL no soporta DROP VALUE de un enum
```

- [ ] **Step 3: Aplicar la migración contra la base local**

Run: `cd backend && source venv/bin/activate && alembic upgrade head`
Expected: sin errores, termina en `d2e4f6a8b0c2`

- [ ] **Step 4: Verificar los valores nuevos en Postgres (local)**

Run:
```bash
PGPASSWORD='AcuantoPass2024!' psql -h localhost -U acuanto_user -d acuantoesta \
  -tAc "SELECT enum_range(NULL::indicatortype);"
```
Expected: la lista incluye `DOLLAR_MAYORISTA`, `DOLLAR_CRIPTO`, `DOLLAR_TARJETA`

- [ ] **Step 5: Aplicar la misma migración contra Supabase**

Esto hace falta ahora (no alcanza con esperar al próximo deploy de Render) porque las tareas siguientes de este plan se verifican contra Supabase.

```bash
cd backend
SUPABASE_URL=$(grep '^DATABASE_URL=' .env | cut -d '=' -f2-)
DATABASE_URL="$SUPABASE_URL" alembic upgrade head
```
Expected: mismo resultado, termina en `d2e4f6a8b0c2`. Verificar con el mismo `enum_range` pero usando `psql "$SUPABASE_URL"` en vez de la conexión local.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/economic_indicator.py backend/alembic/versions/d2e4f6a8b0c2_add_dollar_mayorista_cripto_tarjeta.py
git commit -m "feat: agregar DOLLAR_MAYORISTA, DOLLAR_CRIPTO y DOLLAR_TARJETA a IndicatorType"
```

---

### Task 3: Processor — `_existing_dates()` y `save_all_dollars()`

**Files:**
- Modify: `backend/app/services/economic_data/processor.py:64` (después de `save_dollar_data`, antes de `_CASA_TO_INDICATOR`)

**Interfaces:**
- Consumes: `IndicatorType.DOLLAR_MAYORISTA/CRIPTO/TARJETA` (Task 2), `DollarRecord` (ya existe)
- Produces: `EconomicDataProcessor.save_all_dollars(records: list[DollarRecord]) -> dict[str, int]` (usado por Task 4)

- [ ] **Step 1: Implementar `_existing_dates` y `save_all_dollars`**

En `backend/app/services/economic_data/processor.py`, agregar después del método `save_dollar_data` (termina en la línea 64) y antes de `_CASA_TO_INDICATOR = {`:

```python
    def _existing_dates(self, indicator_type: IndicatorType) -> set:
        """
        Todas las fechas ya guardadas para un tipo de indicador, en una sola
        consulta. Reemplaza el patrón _exists()-por-fila para cargas masivas
        (el endpoint combinado de dólares trae ~30.000 registros de una vez).
        """
        rows = (
            self.session.query(EconomicIndicator.date)
            .filter(EconomicIndicator.indicator_type == indicator_type)
            .all()
        )
        return {row[0] for row in rows}

    _CASA_TO_DOLLAR_TYPE = {
        "blue": IndicatorType.DOLLAR_BLUE,
        "oficial": IndicatorType.DOLLAR_OFICIAL,
        "mayorista": IndicatorType.DOLLAR_MAYORISTA,
        "bolsa": IndicatorType.DOLLAR_MEP,
        "contadoconliqui": IndicatorType.DOLLAR_CCL,
        "cripto": IndicatorType.DOLLAR_CRIPTO,
        "tarjeta": IndicatorType.DOLLAR_TARJETA,
    }

    def save_all_dollars(self, records: list[DollarRecord]) -> dict:
        """
        Guarda el histórico combinado de /v1/cotizaciones/dolares (todas las
        casas). Agrupa por casa y hace un solo SELECT de fechas existentes
        por tipo de indicador (no por fila) antes de insertar.
        Devuelve {casa: cantidad_guardada} para logging. Casas sin
        IndicatorType mapeado (ej. "solidario") se ignoran.
        """
        by_casa: dict[str, list[DollarRecord]] = {}
        for record in records:
            by_casa.setdefault(record.casa, []).append(record)

        saved_per_casa: dict[str, int] = {}
        for casa, casa_records in by_casa.items():
            indicator_type = self._CASA_TO_DOLLAR_TYPE.get(casa)
            if indicator_type is None:
                continue
            existing = self._existing_dates(indicator_type)
            saved = 0
            for record in casa_records:
                if record.fecha in existing:
                    continue
                self.session.add(
                    EconomicIndicator(
                        indicator_type=indicator_type,
                        value=record.venta,
                        date=record.fecha,
                        source=DataSource.ARGENTINADATOS,
                        metadata_json=json.dumps({"compra": record.compra}),
                    )
                )
                existing.add(record.fecha)
                saved += 1
            saved_per_casa[casa] = saved

        self.session.commit()
        return saved_per_casa
```

`DollarRecord` ya está importado en este archivo (línea 8), no hace falta agregar el import.

- [ ] **Step 2: Verificar manualmente contra la base LOCAL (no Supabase todavía)**

Usar fechas en 1901 para no pisar datos reales, y poder limpiarlas después.

Run (desde `backend/`, con el venv activado):
```bash
python3 -c "
from app.config.database import SessionLocal
from app.services.economic_data.processor import EconomicDataProcessor
from app.services.economic_data.schemas import DollarRecord
from datetime import date

session = SessionLocal()
processor = EconomicDataProcessor(session)
fake_records = [
    DollarRecord(casa='blue', compra=1.0, venta=2.0, fecha=date(1901, 1, 1)),
    DollarRecord(casa='mayorista', compra=1.0, venta=2.0, fecha=date(1901, 1, 1)),
    DollarRecord(casa='solidario', compra=1.0, venta=2.0, fecha=date(1901, 1, 1)),
]
print('Primera corrida:', processor.save_all_dollars(fake_records))
print('Segunda corrida (debe ser todo 0):', processor.save_all_dollars(fake_records))
session.close()
"
```
Expected:
```
Primera corrida: {'blue': 1, 'mayorista': 1}
Segunda corrida (debe ser todo 0): {'blue': 0, 'mayorista': 0}
```
Notar que `solidario` no aparece en el dict (sin `IndicatorType` mapeado, se ignora).

- [ ] **Step 3: Limpiar los datos de prueba**

Run:
```bash
PGPASSWORD='AcuantoPass2024!' psql -h localhost -U acuanto_user -d acuantoesta \
  -c "DELETE FROM economic_indicators WHERE date = '1901-01-01';"
```
Expected: `DELETE 2`

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/economic_data/processor.py
git commit -m "feat: agregar save_all_dollars con dedup optimizado por set"
```

---

### Task 4: `fetch_economic_data.py` — wiring, limpieza y backfill real

**Files:**
- Modify: `backend/scripts/fetch_economic_data.py`
- Modify: `backend/app/services/economic_data/client.py` (eliminar `get_dollar_blue`/`get_dollar_oficial`, quedan superados por `get_all_dollars`)

**Interfaces:**
- Consumes: `ArgentinaDatosClient.get_all_dollars()`, `.get_risk_country()` (Task 1), `EconomicDataProcessor.save_all_dollars()` (Task 3)

**Decisión de limpieza:** `get_dollar_blue()` y `get_dollar_oficial()` (que pegan a `/v1/cotizaciones/dolares/blue` y `/oficial`) quedan completamente reemplazados por `get_all_dollars()` (que ya trae blue y oficial, más 5 casas extra, en una sola llamada). Se confirmó que esos dos métodos solo se llamaban desde este script — se eliminan del cliente para no dejar código muerto.

- [ ] **Step 1: Eliminar los métodos superados del cliente**

En `backend/app/services/economic_data/client.py`, eliminar por completo estos dos métodos (están antes de `get_uva`):

```python
    def get_dollar_blue(self) -> list[DollarRecord]:
        data = self._get("/v1/cotizaciones/dolares/blue")
        if data is None:
            return []
        return [DollarRecord(**item) for item in data]

    def get_dollar_oficial(self) -> list[DollarRecord]:
        data = self._get("/v1/cotizaciones/dolares/oficial")
        if data is None:
            return []
        return [DollarRecord(**item) for item in data]

```

- [ ] **Step 2: Reescribir `fetch_economic_data.py`**

Reemplazar el contenido completo de `backend/scripts/fetch_economic_data.py`:

```python
"""
Script standalone para poblar economic_indicators desde la API ArgentinaDatos.

Uso:
    cd backend
    source venv/bin/activate
    python scripts/fetch_economic_data.py
"""
import sys
import os

# Agregar backend/ al path para poder importar app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import SessionLocal
from app.models.economic_indicator import IndicatorType
from app.services.economic_data.client import ArgentinaDatosClient, DolarAPIClient
from app.services.economic_data.processor import EconomicDataProcessor


import argparse

def main():
    parser = argparse.ArgumentParser(description="Fetch economic data")
    parser.add_argument("--inflation", action="store_true", help="Fetch inflation data")
    parser.add_argument("--dollars", action="store_true", help="Fetch dollar data")
    parser.add_argument("--risk-country", action="store_true", help="Fetch country risk data")
    parser.add_argument("--all", action="store_true", help="Fetch all data")
    args = parser.parse_args()

    # Si no se especifica nada, por defecto obtener todo (comportamiento original)
    fetch_all = args.all or (not args.inflation and not args.dollars and not args.risk_country)

    client = ArgentinaDatosClient()
    session = SessionLocal()

    try:
        processor = EconomicDataProcessor(session)

        if fetch_all or args.inflation:
            # Inflación mensual
            records = client.get_inflation()
            saved = processor.save_inflation_data(records, IndicatorType.INFLATION_MONTHLY)
            print(f"[inflacion] Guardados: {saved} nuevos registros")

            # UVA
            records = client.get_uva()
            saved = processor.save_uva_data(records)
            print(f"[uva] Guardados: {saved} nuevos registros")

            # Inflación interanual
            records = client.get_inflation_yearly()
            if records:
                saved = processor.save_inflation_data(records, IndicatorType.INFLATION_YEARLY)
                print(f"[inflacion_interanual] Guardados: {saved} nuevos registros")
            else:
                print("[inflacion_interanual] Endpoint no disponible, saltando.")

        if fetch_all or args.risk_country:
            records = client.get_risk_country()
            saved = processor.save_inflation_data(records, IndicatorType.RISK_COUNTRY)
            print(f"[riesgo_pais] Guardados: {saved} nuevos registros")

        if fetch_all or args.dollars:
            # Todas las casas de cambio — histórico combinado, ArgentinaDatos
            all_dollars = client.get_all_dollars()
            saved_per_casa = processor.save_all_dollars(all_dollars)
            for casa, count in saved_per_casa.items():
                print(f"[dolar_{casa}] Guardados: {count} nuevos registros")

            # DolarAPI — fallback de cotización del día para blue/oficial/MEP/CCL
            dolar_client = DolarAPIClient()
            quotes = dolar_client.get_all_quotes()
            saved = processor.save_dolar_api_quotes(quotes)
            print(f"[dolarapi] Guardados: {saved} nuevos registros")
            for q in quotes:
                print(f"  {q.nombre}: compra={q.compra} venta={q.venta}")

    finally:
        session.close()

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Probar contra la base LOCAL primero**

Run: `cd backend && source venv/bin/activate && python scripts/fetch_economic_data.py --risk-country`
Expected: `[riesgo_pais] Guardados: N nuevos registros` con N > 0 (primera corrida trae todo el histórico desde 1999)

Run: `python scripts/fetch_economic_data.py --dollars`
Expected: una línea `[dolar_<casa>] Guardados: N` por cada una de las 7 casas activas, más la línea de `[dolarapi]`

- [ ] **Step 4: Backfill real contra Supabase**

Este paso escribe en la base de producción — confirmar con el usuario antes de correrlo si no se corrió ya como parte de este plan.

```bash
cd backend
SUPABASE_URL=$(grep '^DATABASE_URL=' .env | cut -d '=' -f2-)
DATABASE_URL="$SUPABASE_URL" python scripts/fetch_economic_data.py --dollars --risk-country
```
Expected: mismo tipo de salida que el Step 3, ahora escribiendo en Supabase.

- [ ] **Step 5: Verificar en Supabase**

```bash
psql "$SUPABASE_URL" -c "
SELECT indicator_type, count(*) FROM economic_indicators
WHERE indicator_type IN ('DOLLAR_MAYORISTA','DOLLAR_CRIPTO','DOLLAR_TARJETA','RISK_COUNTRY')
GROUP BY indicator_type;"
```
Expected: las 4 filas con counts > 0

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/fetch_economic_data.py backend/app/services/economic_data/client.py
git commit -m "feat: wirear riesgo país y todos los dólares en fetch_economic_data.py"
```

---

### Task 5: Extender `/context` — todos los dólares + variación de riesgo país

**Files:**
- Modify: `backend/app/schemas/economic.py:67-85` (clase `EconomicContext`)
- Modify: `backend/app/api/v1/endpoints/economic.py` (función `get_economic_context` completa, líneas 21-152)

**Interfaces:**
- Consumes: `IndicatorType.DOLLAR_MAYORISTA/MEP/CCL/CRIPTO/TARJETA`, `RISK_COUNTRY` (con datos ya cargados por Task 4)
- Produces: `EconomicContext` con los campos nuevos (consumidos por Task 7 en el frontend)

- [ ] **Step 1: Extender el schema `EconomicContext`**

En `backend/app/schemas/economic.py`, reemplazar la clase completa (líneas 67-85):

```python
class EconomicContext(BaseModel):
    """Schema para contexto económico general"""
    inflation_monthly: Optional[Decimal] = None
    inflation_yearly: Optional[Decimal] = None
    dollar_blue: Optional[Decimal] = None
    dollar_oficial: Optional[Decimal] = None
    dollar_mayorista: Optional[Decimal] = None
    dollar_mep: Optional[Decimal] = None
    dollar_ccl: Optional[Decimal] = None
    dollar_cripto: Optional[Decimal] = None
    dollar_tarjeta: Optional[Decimal] = None
    uva_index: Optional[Decimal] = None
    plazo_fijo_rate: Optional[Decimal] = None
    risk_country: Optional[Decimal] = None
    last_updated: datetime
    # Campos de variación para badges
    inflation_monthly_change: Optional[Decimal] = None   # pp vs. mes anterior
    inflation_monthly_date: Optional[date] = None        # fecha del último dato INDEC
    dollar_blue_change: Optional[Decimal] = None         # % vs. registro anterior
    dollar_oficial_change: Optional[Decimal] = None      # % vs. registro anterior
    dollar_mayorista_change: Optional[Decimal] = None    # % vs. registro anterior
    dollar_mep_change: Optional[Decimal] = None          # % vs. registro anterior
    dollar_ccl_change: Optional[Decimal] = None          # % vs. registro anterior
    dollar_cripto_change: Optional[Decimal] = None       # % vs. registro anterior
    dollar_tarjeta_change: Optional[Decimal] = None      # % vs. registro anterior
    risk_country_change: Optional[Decimal] = None        # % vs. registro anterior
    inflation_ytd: Optional[Decimal] = None              # acumulado año corriente (compuesto)

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Reescribir `get_economic_context` con un helper reutilizable**

En `backend/app/api/v1/endpoints/economic.py`, reemplazar `_CONTEXT_TYPES` (líneas 21-29):

```python
_CONTEXT_TYPES = [
    IndicatorType.INFLATION_MONTHLY,
    IndicatorType.INFLATION_YEARLY,
    IndicatorType.DOLLAR_BLUE,
    IndicatorType.DOLLAR_OFICIAL,
    IndicatorType.DOLLAR_MAYORISTA,
    IndicatorType.DOLLAR_MEP,
    IndicatorType.DOLLAR_CCL,
    IndicatorType.DOLLAR_CRIPTO,
    IndicatorType.DOLLAR_TARJETA,
    IndicatorType.UVA_INDEX,
    IndicatorType.PLAZO_FIJO_RATE,
    IndicatorType.RISK_COUNTRY,
]
```

Agregar un helper nuevo después de `_prev_value` (después de la línea 45, antes de `@router.get("/context"...)`):

```python
def _value_and_change(
    db: Session,
    latest: dict[IndicatorType, EconomicIndicator | None],
    indicator_type: IndicatorType,
) -> tuple[Decimal | None, Decimal | None]:
    """Valor actual y variación % vs. registro anterior para un indicador."""
    rec = latest[indicator_type]
    if rec is None:
        return None, None
    prev = _prev_value(db, indicator_type, rec)
    if prev is None or float(prev) == 0:
        return rec.value, None
    change = Decimal(str((float(rec.value) - float(prev)) / float(prev) * 100))
    return rec.value, change
```

Reemplazar todo el cuerpo de `get_economic_context` (desde `latest = {...}` hasta el `return schemas_eco.EconomicContext(...)` inclusive — las líneas que hoy calculan `blue_rec`/`blue_prev`/`dollar_blue_change`, `oficial_rec`/`oficial_prev`/`dollar_oficial_change`, y el `return` final) por:

```python
    latest = {t: EconomicIndicator.get_latest_value(db, t) for t in _CONTEXT_TYPES}

    def val(t: IndicatorType):
        rec = latest[t]
        return rec.value if rec else None

    # Variación inflación mensual (diferencia en pp vs. mes anterior)
    infl_rec = latest[IndicatorType.INFLATION_MONTHLY]
    infl_prev = _prev_value(db, IndicatorType.INFLATION_MONTHLY, infl_rec)
    if infl_rec and infl_prev is not None:
        inflation_monthly_change = Decimal(str(float(infl_rec.value) - float(infl_prev)))
    else:
        inflation_monthly_change = None

    dollar_blue, dollar_blue_change = _value_and_change(db, latest, IndicatorType.DOLLAR_BLUE)
    dollar_oficial, dollar_oficial_change = _value_and_change(db, latest, IndicatorType.DOLLAR_OFICIAL)
    dollar_mayorista, dollar_mayorista_change = _value_and_change(db, latest, IndicatorType.DOLLAR_MAYORISTA)
    dollar_mep, dollar_mep_change = _value_and_change(db, latest, IndicatorType.DOLLAR_MEP)
    dollar_ccl, dollar_ccl_change = _value_and_change(db, latest, IndicatorType.DOLLAR_CCL)
    dollar_cripto, dollar_cripto_change = _value_and_change(db, latest, IndicatorType.DOLLAR_CRIPTO)
    dollar_tarjeta, dollar_tarjeta_change = _value_and_change(db, latest, IndicatorType.DOLLAR_TARJETA)
    risk_country, risk_country_change = _value_and_change(db, latest, IndicatorType.RISK_COUNTRY)

    # Inflación acumulada año corriente (compuesta)
    current_year = date.today().year
    ytd_records = (
        db.query(EconomicIndicator)
        .filter(
            EconomicIndicator.indicator_type == IndicatorType.INFLATION_MONTHLY,
            EconomicIndicator.date >= date(current_year, 1, 1),
        )
        .order_by(EconomicIndicator.date.asc())
        .all()
    )
    if ytd_records:
        compound = Decimal("1")
        for rec in ytd_records:
            compound *= 1 + rec.value / 100
        inflation_ytd = (compound - 1) * 100
    else:
        inflation_ytd = None

    # Fecha más reciente entre todos los registros disponibles
    dates = [rec.date for rec in latest.values() if rec is not None]
    last_updated = (
        datetime.combine(max(dates), time.min) if dates else datetime.utcnow()
    )

    # Inflación interanual (últimos 12 meses)
    last_12m_cutoff = date.today() - relativedelta(months=12)
    last_12m_records = (
        db.query(EconomicIndicator)
        .filter(
            EconomicIndicator.indicator_type == IndicatorType.INFLATION_MONTHLY,
            EconomicIndicator.date >= last_12m_cutoff,
        )
        .order_by(EconomicIndicator.date.asc())
        .all()
    )
    inflation_yearly_val = val(IndicatorType.INFLATION_YEARLY)
    if not inflation_yearly_val and len(last_12m_records) >= 1:
        compound = Decimal("1")
        for rec in last_12m_records[-12:]:
            compound *= 1 + rec.value / 100
        inflation_yearly_val = (compound - 1) * 100

    return schemas_eco.EconomicContext(
        inflation_monthly=val(IndicatorType.INFLATION_MONTHLY),
        inflation_yearly=inflation_yearly_val,
        dollar_blue=dollar_blue,
        dollar_oficial=dollar_oficial,
        dollar_mayorista=dollar_mayorista,
        dollar_mep=dollar_mep,
        dollar_ccl=dollar_ccl,
        dollar_cripto=dollar_cripto,
        dollar_tarjeta=dollar_tarjeta,
        uva_index=val(IndicatorType.UVA_INDEX),
        plazo_fijo_rate=val(IndicatorType.PLAZO_FIJO_RATE),
        risk_country=risk_country,
        last_updated=last_updated,
        inflation_monthly_change=inflation_monthly_change,
        inflation_monthly_date=infl_rec.date if infl_rec else None,
        dollar_blue_change=dollar_blue_change,
        dollar_oficial_change=dollar_oficial_change,
        dollar_mayorista_change=dollar_mayorista_change,
        dollar_mep_change=dollar_mep_change,
        dollar_ccl_change=dollar_ccl_change,
        dollar_cripto_change=dollar_cripto_change,
        dollar_tarjeta_change=dollar_tarjeta_change,
        risk_country_change=risk_country_change,
        inflation_ytd=inflation_ytd,
    )
```

La firma de la función (`@router.get("/context"...)` / `def get_economic_context(db: Session = Depends(get_db)):`) y su docstring no cambian.

- [ ] **Step 3: Verificar contra Supabase con el servidor local**

Run: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload`

En otra terminal:
```bash
curl -s http://localhost:8000/api/v1/economic/context | python3 -m json.tool
```
Expected: JSON con `dollar_mayorista`, `dollar_mep`, `dollar_ccl`, `dollar_cripto`, `dollar_tarjeta` y `risk_country` con valores numéricos (no `null`, porque Task 4 ya cargó los datos en Supabase), y sus `_change` correspondientes.

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/economic.py backend/app/api/v1/endpoints/economic.py
git commit -m "feat: extender /economic/context con todos los dólares y riesgo país"
```

---

### Task 6: Endpoint `GET /economic/risk-country/history`

**Files:**
- Modify: `backend/app/api/v1/endpoints/economic.py` (agregar al final del archivo, después de `get_inflation_history`)

**Interfaces:**
- Produces: `GET /api/v1/economic/risk-country/history?months=N -> list[EconomicIndicator]` (consumido por Task 7)

- [ ] **Step 1: Agregar el endpoint**

Al final de `backend/app/api/v1/endpoints/economic.py`, agregar:

```python


@router.get("/risk-country/history", response_model=list[schemas_eco.EconomicIndicator])
def get_risk_country_history(
    months: int = Query(12, ge=1, le=360, description="Últimos N meses de historial"),
    db: Session = Depends(get_db),
):
    """
    Historial de riesgo país (EMBI+).

    Devuelve los registros ordenados por fecha descendente.
    - `months`: ventana de tiempo (máximo 360 meses = 30 años; hay datos desde 1999)
    """
    cutoff = date.today() - relativedelta(months=months)

    return (
        db.query(EconomicIndicator)
        .filter(
            EconomicIndicator.indicator_type == IndicatorType.RISK_COUNTRY,
            EconomicIndicator.date >= cutoff,
        )
        .order_by(EconomicIndicator.date.desc())
        .all()
    )
```

- [ ] **Step 2: Verificar**

Con el servidor corriendo (`uvicorn app.main:app --reload`):
```bash
curl -s "http://localhost:8000/api/v1/economic/risk-country/history?months=12" | python3 -m json.tool | head -20
```
Expected: lista de objetos con `indicator_type: "RISK_COUNTRY"`, `value`, `date`, ordenados por fecha descendente

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/v1/endpoints/economic.py
git commit -m "feat: agregar endpoint /economic/risk-country/history"
```

---

### Task 7: Frontend — tipos y cliente API

**Files:**
- Modify: `frontend/src/types/index.ts` (interfaz `EconomicContext`)
- Modify: `frontend/src/lib/api.ts`

**Interfaces:**
- Produces: `getRiskCountryHistory(months?: number) -> Promise<Array<{date: string, value: number}>>` (consumido por Task 9)

- [ ] **Step 1: Extender la interfaz `EconomicContext`**

En `frontend/src/types/index.ts`, reemplazar la interfaz completa:

```typescript
export interface EconomicContext {
  inflation_monthly: number | null;
  inflation_yearly: number | null;
  dollar_blue: number | null;
  dollar_oficial: number | null;
  dollar_mayorista: number | null;
  dollar_mep: number | null;
  dollar_ccl: number | null;
  dollar_cripto: number | null;
  dollar_tarjeta: number | null;
  uva_index: number | null;
  plazo_fijo_rate: number | null;
  risk_country: number | null;
  last_updated: string;
  inflation_monthly_change: number | null;
  inflation_monthly_date: string | null;
  dollar_blue_change: number | null;
  dollar_oficial_change: number | null;
  dollar_mayorista_change: number | null;
  dollar_mep_change: number | null;
  dollar_ccl_change: number | null;
  dollar_cripto_change: number | null;
  dollar_tarjeta_change: number | null;
  risk_country_change: number | null;
  inflation_ytd: number | null;
}
```

- [ ] **Step 2: Agregar `getRiskCountryHistory` en `api.ts`**

En `frontend/src/lib/api.ts`, agregar después de `getDollarHistory`:

```typescript
export async function getRiskCountryHistory(
  months = 12
): Promise<Array<{ date: string; value: number }>> {
  const { data } = await api.get<EconomicIndicator[]>(
    `/economic/risk-country/history?months=${months}`
  );
  return data.map((r) => ({
    date: r.date,
    value: parseFloat(String(r.value)),
  }));
}
```

- [ ] **Step 3: Verificar tipos**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores (nota: `npm run build` falla en este entorno local por el `?` en la ruta del proyecto — no relacionado con este cambio, ver nota en `CLAUDE.md`/memoria del proyecto; `tsc --noEmit` es la verificación válida acá)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/lib/api.ts
git commit -m "feat: agregar tipos y cliente para riesgo país y todos los dólares"
```

---

### Task 8: `EconomicSidebar.tsx` — fila de riesgo país

**Files:**
- Modify: `frontend/src/components/layout/EconomicSidebar.tsx`

**Interfaces:**
- Produces: `export function ChangeBadge` (se exporta para reutilizarlo en Task 9 — hoy es una función local sin `export`)

**Nota importante:** el badge de variación de esta pantalla (`ChangeBadge`, formato porcentaje directo tipo `2.3`) es distinto del `VarBadge` que usa `IndicatorCard` en `economia/page.tsx` (espera una *fracción* tipo `0.023` y la multiplica por 100 internamente). Son incompatibles entre sí — no hay que mezclarlos. Por eso Task 9 importa `ChangeBadge` de acá en vez de reusar `VarBadge`.

- [ ] **Step 1: Exportar `ChangeBadge`**

En `frontend/src/components/layout/EconomicSidebar.tsx`, cambiar:

```typescript
function ChangeBadge({ value }: { value: number | null | undefined }) {
```

por:

```typescript
export function ChangeBadge({ value }: { value: number | null | undefined }) {
```

- [ ] **Step 2: Agregar la fila de "Riesgo país"**

En el mismo archivo, dentro del `<div className="divide-y divide-border">`, agregar después de la fila "Dólar oficial" (después del `<IndicatorRow label="Dólar oficial" .../>`):

```tsx
          <IndicatorRow
            label="Riesgo país"
            source="JP Morgan EMBI+"
            value={data?.risk_country != null ? `${fmt(data.risk_country, 0)} pb` : "—"}
            badge={<ChangeBadge value={data?.risk_country_change} />}
            subtitle="últimas 24 hs"
          />
```

- [ ] **Step 3: Verificar visualmente**

Run: `cd frontend && npm run dev` (usa `--turbo`, así que corre bien pese al `?` en la ruta)

Abrir `http://localhost:3000` en el navegador y confirmar que el panel derecho ("Hoy en Argentina") muestra la fila "Riesgo país" con un valor numérico (ej. "437 pb") y un badge de variación.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/layout/EconomicSidebar.tsx
git commit -m "feat: agregar fila de riesgo país al EconomicSidebar"
```

---

### Task 9: `economia/page.tsx` — 5ta card, grid de dólares y gráfico de riesgo país

**Files:**
- Modify: `frontend/src/app/economia/page.tsx`

**Interfaces:**
- Consumes: `getRiskCountryHistory` (Task 7), `ChangeBadge` (Task 8), `BarChart` (ya existe en `@/components/design/components`)

- [ ] **Step 1: Actualizar imports y agregar el query de riesgo país histórico**

En `frontend/src/app/economia/page.tsx`, reemplazar la línea de import de `api`:

```typescript
import { getEconomicContext, getInflationHistory, getDollarHistory } from "@/lib/api";
```

por:

```typescript
import { getEconomicContext, getInflationHistory, getDollarHistory, getRiskCountryHistory } from "@/lib/api";
import { ChangeBadge } from "@/components/layout/EconomicSidebar";
```

Después del query `dollarHist` existente (después del bloque `const { data: dollarHist } = useQuery({...});`), agregar:

```typescript
  const { data: riskCountryRaw = [] } = useQuery({
    queryKey: ["riskCountryHistory"],
    queryFn: () => getRiskCountryHistory(12),
    staleTime: 30 * 60 * 1000,
  });
```

- [ ] **Step 2: Parsear los valores nuevos**

Después de la línea `const dollarOficial = eco?.dollar_oficial != null ? parseFloat(String(eco.dollar_oficial)) : null;`, agregar:

```typescript
  const dollarMayorista = eco?.dollar_mayorista != null ? parseFloat(String(eco.dollar_mayorista)) : null;
  const dollarMep = eco?.dollar_mep != null ? parseFloat(String(eco.dollar_mep)) : null;
  const dollarCcl = eco?.dollar_ccl != null ? parseFloat(String(eco.dollar_ccl)) : null;
  const dollarCripto = eco?.dollar_cripto != null ? parseFloat(String(eco.dollar_cripto)) : null;
  const dollarTarjeta = eco?.dollar_tarjeta != null ? parseFloat(String(eco.dollar_tarjeta)) : null;
  const riskCountry = eco?.risk_country != null ? parseFloat(String(eco.risk_country)) : null;
```

Después del bloque `const dollarLabels = ...` / `const dollarOficialArr = ...`, agregar:

```typescript
  const riskCountryBarData = [...riskCountryRaw]
    .reverse()
    .map((r) => ({
      m: new Date(r.date + "T00:00:00").toLocaleDateString("es-AR", { month: "short" }),
      v: r.value,
    }));

  const riskCountrySpark = riskCountryBarData.slice(-6).map((d) => d.v);
```

- [ ] **Step 3: Agregar la 5ta card en el grid superior**

Cambiar:

```jsx
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 22 }}>
```

por:

```jsx
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 16, marginBottom: 22 }}>
```

Y agregar, después de la card "Inflación interanual" (antes del `</div>` que cierra ese grid):

```jsx
        <RiskCountryCard value={riskCountry} change={eco?.risk_country_change} spark={riskCountrySpark} />
```

**Por qué una card aparte y no `<IndicatorCard delta={...}>`:** `IndicatorCard` (en `@/components/design/components`) renderiza su badge de variación con `VarBadge`, que espera una *fracción* (`0.023` → `+2,3%`) y la multiplica x100 internamente — ya se usa así en otras pantallas (precios de productos) y no hay que tocarlo. Pero `risk_country_change` que devuelve el backend ya es un porcentaje directo (`2.3`), igual que `dollar_blue_change`, etc. Pasarlo tal cual a `IndicatorCard` mostraría un badge con el número equivocado (dividido implícitamente x100 de más). Por eso esta card se arma aparte, con el mismo look visual pero usando `ChangeBadge` (porcentaje directo, ya importado de `EconomicSidebar` en el Step 1).

- [ ] **Step 4: Agregar la sección "Todos los dólares"**

Después del `</div>` que cierra el grid "MAIN CHARTS" (el `<div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", ...}}>` con los charts de inflación y dólar), agregar:

```jsx
      {/* TODOS LOS DÓLARES */}
      <div className="card" style={{ padding: 22, marginBottom: 22 }}>
        <div className="section-head">
          <div>
            <h2>Todos los dólares</h2>
            <div className="subtle" style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2 }}>
              Cotización de venta · variación vs. registro anterior
            </div>
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginTop: 16 }}>
          <DollarCard label="Oficial" value={dollarOficial} change={eco?.dollar_oficial_change} />
          <DollarCard label="Blue" value={dollarBlue} change={eco?.dollar_blue_change} />
          <DollarCard label="Mayorista" value={dollarMayorista} change={eco?.dollar_mayorista_change} />
          <DollarCard label="MEP" value={dollarMep} change={eco?.dollar_mep_change} />
          <DollarCard label="CCL" value={dollarCcl} change={eco?.dollar_ccl_change} />
          <DollarCard label="Cripto" value={dollarCripto} change={eco?.dollar_cripto_change} />
          <DollarCard label="Tarjeta" value={dollarTarjeta} change={eco?.dollar_tarjeta_change} />
        </div>
      </div>

      {/* RIESGO PAÍS HISTÓRICO */}
      <div className="card" style={{ padding: 22, marginBottom: 22 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
          <div>
            <h2>Riesgo país</h2>
            <div className="subtle" style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2 }}>
              Últimos 12 meses · EMBI+ · JP Morgan
            </div>
          </div>
          {riskCountry != null && (
            <div style={{ textAlign: "right" }}>
              <div className="mono" style={{ fontSize: 22, fontWeight: 700, color: "var(--fg)" }}>
                {fmtPrice(riskCountry)} pb
              </div>
              <div className="subtle">último dato</div>
            </div>
          )}
        </div>
        <BarChart data={riskCountryBarData} color="var(--fg-3)" height={220} valueFmt={(v) => fmtPrice(v) + " pb"} />
      </div>
```

- [ ] **Step 5: Agregar los componentes `RiskCountryCard` y `DollarCard`**

Al final del archivo, después de la función `LegendDot`, agregar:

```tsx
function RiskCountryCard({ value, change, spark }: {
  value: number | null;
  change?: number | null;
  spark: number[];
}) {
  return (
    <div className="card" style={{ padding: 18, display: "flex", flexDirection: "column", gap: 12 }}>
      <div>
        <div style={{ fontSize: 11.5, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Riesgo país
        </div>
        <div style={{ fontSize: 11, color: "var(--fg-4)", marginTop: 2 }}>EMBI+ · JP Morgan</div>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
        <div className="mono" style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em" }}>
          {value != null ? fmtPrice(value) + " pb" : "–"}
        </div>
        <ChangeBadge value={change} />
      </div>
      {spark.length > 1 && <Sparkline data={spark} color="var(--fg-3)" height={36} />}
    </div>
  );
}

function DollarCard({ label, value, change }: {
  label: string;
  value: number | null;
  change?: number | null;
}) {
  return (
    <div style={{ padding: 14, background: "var(--bg-2)", borderRadius: 10, border: "1px solid var(--border)" }}>
      <div style={{ fontSize: 11, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span className="mono" style={{ fontSize: 18, fontWeight: 700 }}>
          {value != null ? "$" + fmtPrice(value) : "–"}
        </span>
        <ChangeBadge value={change} />
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Verificar tipos**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores

- [ ] **Step 7: Verificar visualmente**

Con `npm run dev` corriendo, abrir `http://localhost:3000/economia` y confirmar:
- 5 cards en la fila superior, la última "Riesgo país" con sparkline
- Sección "Todos los dólares" con 7 cards (Oficial, Blue, Mayorista, MEP, CCL, Cripto, Tarjeta), cada una con valor y badge de variación
- Gráfico de barras "Riesgo país" debajo, con datos de los últimos 12 meses
- El gráfico de línea doble blue/oficial sigue igual que antes

- [ ] **Step 8: Commit**

```bash
git add frontend/src/app/economia/page.tsx
git commit -m "feat: agregar riesgo país y todos los dólares a la pantalla de economía"
```
