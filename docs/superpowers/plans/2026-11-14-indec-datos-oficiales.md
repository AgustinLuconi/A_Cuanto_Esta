# Datos oficiales del INDEC — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ingerir datos oficiales del INDEC (IPC, canastas, salarios) en una tabla propia mediante una capa genérica basada en un registro de datasets, exponerlos por API y mostrarlos en `/economia`.

**Architecture:** Un `IndecClient` pagina la API del INDEC; un registro declarativo (`registry.py`) define qué cortes se piden; un cargador normaliza y hace upsert idempotente en `indec_observations` (formato largo); un orquestador (`sync.py`) y un script CLI lo ejecutan desde un workflow diario. La API y el frontend leen solo de la base propia.

**Tech Stack:** Python 3.11 (Render; local 3.14), FastAPI, SQLAlchemy + Alembic (PostgreSQL/Neon), httpx, pytest; Next.js 14 + TypeScript + zod + TanStack Query; GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-14-indec-datos-oficiales-design.md`

## Global Constraints

- Variable de entorno del token: `INDEC_API_TOKEN` (en `backend/.env`, ignorado por git; secret de GitHub ya cargado por el usuario). URL base: `https://api.indec.gob.ar`. Header: `Authorization: Bearer <token>`. **Nunca** loguear ni incluir el token en mensajes de error.
- La API devuelve máximo **1.000 filas** por request: paginar con `limit`/`offset` y orden total determinista.
- Ventana de revisión del modo incremental: **3 meses** hacia atrás desde el último período guardado. Aviso de vencimiento del token: **menos de 30 días**.
- `region` es **NOT NULL**; si el dataset no trae región (`indice_salarios`) se guarda `Nacional`.
- Timestamps `timestamptz` con `app.utils.time.utcnow_aware` (no `datetime.utcnow`).
- Migración Alembic nueva con `down_revision = '089f6eb41b51'` (head actual).
- **Un commit de base de datos por dataset**; la carga es upsert (`ON CONFLICT DO UPDATE`).
- El job debe terminar con código distinto de 0 si falta el token, si el INDEC falla o si un dataset trae 0 filas.
- No se toca `economic_indicators` ni los clientes de ArgentinaDatos/DolarAPI. Código compatible con Python 3.11.
- Comentarios, docstrings y mensajes de log en español (convención del repo); identificadores en inglés.

## Review Focus

Entradas/condiciones que el spec implica y que ningún caso feliz ejercita, de más a menos probable:

1. Filas duplicadas dentro de un mismo lote (misma clave única): PostgreSQL falla con "cannot affect row a second time". Se deduplica al normalizar (Task 4).
2. El INDEC responde 200 con lista vacía, o devuelve filas pero todas con `valor` nulo: el sync debe fallar con `EmptyDatasetError`, no terminar "en verde" (Task 5).
3. Filas con `valor: null` o `periodo` mal formado: se descartan sin romper el lote (Task 4).
4. Token vencido/inválido (401/403): error inmediato sin reintentos y sin filtrar el token (Task 2). Token ausente: error claro antes de pedir nada.
5. Una página de exactamente 1.000 filas: hay que pedir la siguiente (que puede venir vacía) para no truncar datos (Task 2). Con la tabla vacía, `/overview` responde con campos `null`, no 500, y el frontend oculta la sección (Tasks 6 y 8).

---

### Task 1: Configuración, modelo y migración

**Files:**
- Modify: `backend/app/config/settings.py` (agregar `INDEC_API_URL`, `INDEC_API_TOKEN` en el bloque "APIs externas")
- Create: `backend/app/models/indec_observation.py`
- Modify: `backend/app/models/__init__.py`, `backend/alembic/env.py` (importar el modelo nuevo)
- Create: `backend/alembic/versions/<nuevo_id>_create_indec_observations.py`
- Test: `backend/tests/test_indec_model.py`

**Interfaces:**
- Produces: `settings.INDEC_API_URL: str = "https://api.indec.gob.ar"`, `settings.INDEC_API_TOKEN: Optional[str] = None`. Modelo `IndecObservation` (tabla `indec_observations`) con columnas: `id` UUID pk (default `uuid4`), `dataset` String(80), `classifier` String(120), `level` String(60), `series_code` String(40), `series_name` String(255), `region` String(40) NOT NULL, `indicator_type` String(60), `unit` String(40) nullable, `period` Date, `value` Numeric(18,4), `notes` Text nullable, `ingested_at` DateTime(timezone=True) default `utcnow_aware`. Todas NOT NULL salvo `unit` y `notes`. `UniqueConstraint(dataset, classifier, level, series_code, region, indicator_type, period, name="uq_indec_observation_key")` e `Index("ix_indec_observation_lookup", dataset, series_code, region, indicator_type, period)`.

- [ ] **Step 1: Crear la rama y commitear lo previo**

`git checkout -b feat/indec-datos-oficiales`. Commits separados, en orden: (a) fix del processor + su test (`backend/app/services/economic_data/processor.py`, `backend/tests/test_economic_processor.py`) con mensaje `fix: usar una sola consulta de fechas existentes al guardar indicadores`; (b) spec y plan (`docs/superpowers/`) con `docs: diseño y plan de datos del INDEC`. El `.env.example` se commitea con este task. Verificar con `git status` que `backend/.env` NO aparece.

- [ ] **Step 2: Escribir el test que falla** (`test_indec_model.py`)

Tests que inspeccionan `IndecObservation.__table__` sin base de datos: `test_region_is_not_nullable` (`not __table__.c.region.nullable`), `test_unit_and_notes_are_nullable`, `test_unique_constraint_covers_full_key` (existe una `UniqueConstraint` llamada `uq_indec_observation_key` cuyas columnas, como conjunto, son exactamente `{dataset, classifier, level, series_code, region, indicator_type, period}`), `test_ingested_at_is_timezone_aware` (`__table__.c.ingested_at.type.timezone is True`).

- [ ] **Step 3: Verificar que falla**

Run: `cd backend && source venv/bin/activate && pytest tests/test_indec_model.py -v` — Expected: FAIL (`ModuleNotFoundError: app.models.indec_observation`).

- [ ] **Step 4: Implementar** settings, modelo (mismo estilo que `economic_indicator.py`), exportarlo en `models/__init__.py` y `alembic/env.py`, y escribir la migración a mano (`op.create_table` + constraint + índice; `downgrade` hace `drop_table`). Verificar el SQL con `alembic upgrade head --sql | grep -i indec_observations` (modo offline, no toca la base).

- [ ] **Step 5: Verificar que pasa**

Run: `pytest tests/test_indec_model.py -v` — Expected: 4 passed. Luego `pytest -q` completo — Expected: sin fallos nuevos.

- [ ] **Step 6: Commit**

```bash
git add backend/app/config/settings.py backend/app/models backend/alembic backend/tests/test_indec_model.py backend/.env.example
git commit -m "feat: modelo y migración de observaciones del INDEC"
```

---

### Task 2: Cliente del INDEC

**Files:**
- Create: `backend/app/services/indec/__init__.py`, `backend/app/services/indec/client.py`
- Test: `backend/tests/test_indec_client.py`

**Interfaces:**
- Consumes: `settings.INDEC_API_URL`, `settings.INDEC_API_TOKEN`, `settings.SCRAPING_TIMEOUT` (Task 1 / existentes).
- Produces (en `client.py`):
  - `class IndecError(Exception)`; `class IndecAuthError(IndecError)`.
  - `class IndecClient` con `__init__(self, token: str | None = None, base_url: str | None = None, timeout: int | None = None, max_retries: int = 3, retry_backoff: float = 1.0, page_size: int = 1000)` — usa los `settings` cuando el argumento es `None`; lanza `IndecAuthError` si no hay token.
  - `IndecClient.fetch(self, slug: str, params: dict[str, str], order: str) -> list[dict]` — devuelve todas las filas del dataset `slug` aplicando `params` (filtros estilo PostgREST, ej. `{"codigo": "in.(0,01)"}`), paginando con `limit=page_size` y `offset`, siempre con `order=<order>`.
  - `token_days_remaining(token: str, now: datetime | None = None) -> int | None` — días hasta `exp` del JWT (sin verificar firma); `None` si no se puede decodificar.

- [ ] **Step 1: Escribir los tests que fallan** (patchear `app.services.indec.client.httpx.get` y `app.services.indec.client.time.sleep`, como en `test_economic_data_client.py`)

- `test_fetch_sends_bearer_header_and_url`: el `httpx.get` recibe URL `…/v1/ipc_nacional`, `headers["Authorization"] == "Bearer tok"` y `params` con `limit=1000`, `offset=0`, `order`, más los filtros pasados.
- `test_fetch_paginates_until_short_page`: respuestas de 1000 filas y luego 3 → devuelve 1003 filas y se hicieron 2 requests con `offset` 0 y 1000.
- `test_fetch_requests_next_page_after_exactly_full_page`: respuestas de 1000 filas y luego `[]` → devuelve 1000 filas y se hicieron 2 requests (Review Focus 5).
- `test_fetch_retries_on_5xx_then_succeeds`: 503, 503, 200 → devuelve datos; `time.sleep` llamado 2 veces.
- `test_fetch_raises_indec_error_after_exhausting_retries`: `httpx.ConnectError` siempre → `IndecError` (no `IndecAuthError`), 3 intentos.
- `test_fetch_raises_auth_error_on_401_without_retry`: 401 → `IndecAuthError`, un solo request, y `"tok"` no aparece en `str(exc)` (Review Focus 4).
- `test_fetch_raises_on_non_list_payload`: respuesta JSON objeto → `IndecError`.
- `test_init_without_token_raises_auth_error`: `IndecClient(token=None)` con `settings.INDEC_API_TOKEN` en `None` (monkeypatch) → `IndecAuthError`.
- `test_token_days_remaining`: JWT construido en el test con `exp` = ahora + 10 días → `10` (usar `now` fijo); token basura → `None`.
- `test_init_warns_when_token_expires_soon`: con `exp` a 5 días, `capsys` captura una línea que contiene `vence` y `5`, y no contiene el token.

- [ ] **Step 2: Verificar que fallan**

Run: `pytest tests/test_indec_client.py -v` — Expected: FAIL (módulo inexistente).

- [ ] **Step 3: Implementar `IndecClient` y `token_days_remaining` en `client.py`**

Reintentar solo ante `httpx.HTTPError` de red y respuestas 5xx, con espera `retry_backoff * intento` (mismo patrón que `ArgentinaDatosClient._get`). 401/403 → `IndecAuthError`; otros 4xx → `IndecError` sin reintento. Mensajes de error incluyen slug y status, nunca headers. Para decodificar el JWT usar `base64.urlsafe_b64decode` con padding manual y `json.loads`. Seguir el estilo `print("[indec] …")` del repo.

- [ ] **Step 4: Verificar que pasan**

Run: `pytest tests/test_indec_client.py -v` — Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/indec backend/tests/test_indec_client.py
git commit -m "feat: cliente del INDEC con paginación, reintentos y aviso de vencimiento del token"
```

---

### Task 3: Registro de datasets

**Files:**
- Create: `backend/app/services/indec/registry.py`
- Test: `backend/tests/test_indec_registry.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class DatasetSpec: slug: str; slices: tuple[dict[str, str], ...]; has_region: bool; order: str` — cada slice es un dict de filtros PostgREST que se pide por separado y se une.
  - `REGISTRY: dict[str, DatasetSpec]` con exactamente las claves `ipc_nacional`, `valorizacion_canastas_cba_cbt`, `indice_salarios`.
  - `get_specs(slug: str | None) -> list[DatasetSpec]` — `None` devuelve todos; slug desconocido lanza `ValueError` con los slugs válidos en el mensaje.

Valores exactos (del spec y verificados contra el INDEC real el 2026-11-14):
- `ipc_nacional`: `has_region=True`; slice A = `{"clasificador": "in.(IPC,COICOP Argentina 2019)", "codigo": "in.(0,01,01.1)", "tipo_de_indicador": "in.(Indice,v_m,v_ia,v_acum)", "region": "in.(Nacional,GBA)"}`; slice B = `{"nivel": "eq.Producto", "tipo_de_indicador": "eq.Precio promedio", "region": "eq.GBA"}`.
- `valorizacion_canastas_cba_cbt`: `has_region=True`; un slice vacío `{}`.
- `indice_salarios`: `has_region=False`; slice `{"codigo": "in.(0,100,110,120,200)", "tipo_de_indicador": "in.(Indice,v_m,v_ia)"}`.
- `order` (orden total sobre la clave única): `"periodo.asc,clasificador.asc,nivel.asc,codigo.asc,tipo_de_indicador.asc,region.asc"` cuando `has_region`, sin `region.asc` cuando no.

- [ ] **Step 1: Escribir los tests que fallan**

`test_registry_has_the_three_v1_datasets` (conjunto de claves), `test_get_specs_none_returns_all`, `test_get_specs_unknown_slug_raises_value_error_listing_valid_slugs`, `test_order_includes_region_only_when_dataset_has_region`, `test_ipc_slices_match_spec` (compara los dos dicts exactos de arriba), `test_every_slice_value_is_a_postgrest_filter` (todo valor de todo slice empieza con `eq.` o `in.(`).

- [ ] **Step 2: Verificar que fallan** — `pytest tests/test_indec_registry.py -v` → FAIL.

- [ ] **Step 3: Implementar** `registry.py` con los valores exactos de arriba.

- [ ] **Step 4: Verificar que pasan** — `pytest tests/test_indec_registry.py -v` → 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/indec/registry.py backend/tests/test_indec_registry.py
git commit -m "feat: registro declarativo de datasets del INDEC"
```

---

### Task 4: Cargador (normalización y upsert)

**Files:**
- Create: `backend/app/services/indec/loader.py`
- Test: `backend/tests/test_indec_loader.py`

**Interfaces:**
- Consumes: `DatasetSpec` (Task 3), `IndecObservation` (Task 1), `utcnow_aware`.
- Produces:
  - `normalize_rows(spec: DatasetSpec, rows: list[dict]) -> list[dict]` — convierte filas crudas del INDEC en dicts con las claves `dataset, classifier, level, series_code, series_name, region, indicator_type, unit, period, value, notes`. Mapeo: `clasificador→classifier`, `nivel→level`, `codigo→series_code`, `descripcion→series_name`, `tipo_de_indicador→indicator_type`, `unidad_de_medida→unit`, `observaciones→notes`, `valor→value`, `periodo` ("YYYYMM")→`period` = `date(año, mes, 1)`. `region`: si `spec.has_region` el valor de la fila, si no `"Nacional"`. Descarta filas con `valor` nulo o `periodo` inválido; deduplica por la clave única `(dataset, classifier, level, series_code, region, indicator_type, period)` conservando la última aparición.
  - `@dataclass class UpsertResult: inserted: int; updated: int`.
  - `upsert_observations(session: Session, rows: list[dict], batch_size: int = 1000) -> UpsertResult` — `INSERT … ON CONFLICT ON CONSTRAINT uq_indec_observation_key DO UPDATE` (dialecto `sqlalchemy.dialects.postgresql`) actualizando `value`, `series_name`, `unit`, `notes` e `ingested_at=utcnow_aware()`; distingue insertadas de actualizadas con `RETURNING (xmax = 0)`. No hace commit.

- [ ] **Step 1: Escribir los tests que fallan**

- `test_normalize_maps_fields_and_parses_period`: una fila IPC con `periodo="202610"` produce `period == date(2026, 10, 1)`, `series_code`, `indicator_type`, `region` correctos.
- `test_normalize_forces_region_nacional_when_dataset_has_no_region`: fila de salarios sin clave `region` → `region == "Nacional"`.
- `test_normalize_drops_null_value_rows` y `test_normalize_drops_invalid_period_rows` (`"2026"`, `"abcdef"`, `None`) — sin excepción (Review Focus 3).
- `test_normalize_dedups_same_key_keeping_last`: dos filas con la misma clave y distinto `valor` → una sola fila con el segundo valor (Review Focus 1).
- `test_upsert_executes_one_statement_per_batch`: `session` `MagicMock`; 2.500 filas con `batch_size=1000` → `session.execute` llamado 3 veces; no se llama `session.commit`.
- `test_upsert_counts_inserted_and_updated`: `session.execute().all()` devuelve filas `[(True,), (False,), (True,)]` → `UpsertResult(inserted=2, updated=1)`.
- `test_upsert_with_empty_rows_does_nothing`: `[]` → `UpsertResult(0, 0)` y `execute` no se llama.

- [ ] **Step 2: Verificar que fallan** — `pytest tests/test_indec_loader.py -v` → FAIL.

- [ ] **Step 3: Implementar** `normalize_rows`, `UpsertResult` y `upsert_observations` en `loader.py`. Convertir `valor` a `Decimal(str(valor))` para no arrastrar error de float.

- [ ] **Step 4: Verificar que pasan** — `pytest tests/test_indec_loader.py -v` → 8 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/indec/loader.py backend/tests/test_indec_loader.py
git commit -m "feat: normalización y upsert idempotente de observaciones del INDEC"
```

---

### Task 5: Orquestador y script CLI

**Files:**
- Create: `backend/app/services/indec/sync.py`, `backend/scripts/fetch_indec_data.py`
- Test: `backend/tests/test_indec_sync.py`

**Interfaces:**
- Consumes: `IndecClient`, `IndecError` (Task 2), `DatasetSpec`/`get_specs` (Task 3), `normalize_rows`/`upsert_observations`/`UpsertResult` (Task 4), `IndecObservation`.
- Produces (en `sync.py`):
  - `class EmptyDatasetError(IndecError)`.
  - `@dataclass class SyncResult: dataset: str; fetched: int; inserted: int; updated: int`.
  - `@dataclass class SyncReport: results: list[SyncResult]; errors: dict[str, str]`.
  - `latest_period(session: Session, dataset: str) -> date | None` — máximo `period` guardado del dataset.
  - `sync_dataset(session: Session, client: IndecClient, spec: DatasetSpec, *, full: bool = False) -> SyncResult` — modo incremental: pide `periodo=gte.YYYYMM` con `YYYYMM` = (último período − 3 meses) añadido a **cada** slice; si no hay datos guardados o `full=True`, pide todo. Une las filas de todos los slices, normaliza, y si quedan 0 filas lanza `EmptyDatasetError` **antes de escribir**. Hace `session.commit()` una vez al final del dataset.
  - `sync_all(session: Session, client: IndecClient, specs: list[DatasetSpec], *, full: bool = False) -> SyncReport` — ejecuta cada dataset; ante `IndecError` hace `session.rollback()`, registra `errors[slug] = str(exc)` y sigue con el siguiente.
- Produces (en `scripts/fetch_indec_data.py`): `main(argv: list[str] | None = None) -> int` con `--dataset <slug>` (opcional; por defecto todos) y `--full`; imprime una línea por dataset; **retorna 1** si el token falta/es inválido, si hay cualquier error en el reporte, y 0 si todo salió bien. `if __name__ == "__main__": sys.exit(main())`. Mismo prólogo de `sys.path` que `scripts/fetch_economic_data.py`.

- [ ] **Step 1: Escribir los tests que fallan** (cliente y sesión `MagicMock`; patchear `latest_period` y `normalize_rows`/`upsert_observations` cuando haga falta aislar)

- `test_incremental_adds_periodo_gte_with_three_month_window`: `latest_period` → `date(2026, 10, 1)` → cada llamada a `client.fetch` lleva `params["periodo"] == "gte.202607"`.
- `test_full_flag_skips_periodo_filter`: con `full=True` ningún `fetch` lleva `periodo`.
- `test_no_stored_data_fetches_everything`: `latest_period` → `None` → sin filtro `periodo`.
- `test_fetches_each_slice_and_merges_rows`: spec con 2 slices → 2 llamadas a `fetch`, `SyncResult.fetched` es la suma.
- `test_empty_fetch_raises_empty_dataset_error_before_writing`: `fetch` devuelve `[]` → `EmptyDatasetError`, `upsert_observations` no llamado, `commit` no llamado (Review Focus 2).
- `test_all_rows_null_value_raises_empty_dataset_error`: `fetch` devuelve filas con `valor: None` → `EmptyDatasetError`.
- `test_commits_once_per_dataset`: éxito → `session.commit` llamado exactamente una vez.
- `test_sync_all_continues_after_error_and_reports_it`: el primer dataset lanza `IndecError("boom")`, el segundo tiene éxito → `report.errors == {slug1: "boom"}`, `len(report.results) == 1`, `session.rollback` llamado.
- `test_main_returns_1_when_token_missing`: `settings.INDEC_API_TOKEN=None` → `main([]) == 1`.
- `test_main_returns_1_when_report_has_errors` y `test_main_returns_0_on_success` (patchear `IndecClient`, `SessionLocal` y `sync_all`).
- `test_main_unknown_dataset_returns_1`: `main(["--dataset", "nope"]) == 1`.

- [ ] **Step 2: Verificar que fallan** — `pytest tests/test_indec_sync.py -v` → FAIL.

- [ ] **Step 3: Implementar** `sync.py` y el script. La resta de 3 meses con `dateutil.relativedelta` (ya usado en `economic.py`). Cerrar la sesión en `finally` en el script.

- [ ] **Step 4: Verificar que pasan** — `pytest tests/test_indec_sync.py -v` → 11 passed; `pytest -q` completo sin fallos nuevos.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/indec/sync.py backend/scripts/fetch_indec_data.py backend/tests/test_indec_sync.py
git commit -m "feat: orquestador de sincronización y script CLI del INDEC"
```

---

### Task 6: Consultas, schemas y endpoints

**Files:**
- Create: `backend/app/schemas/indec.py`, `backend/app/services/indec/queries.py`, `backend/app/api/v1/endpoints/indec.py`
- Modify: `backend/app/api/v1/api.py` (registrar `indec.router` con `prefix="/indec"`, `tags=["indec"]`)
- Test: `backend/tests/test_indec_api.py`

**Interfaces:**
- Consumes: `IndecObservation` (Task 1), `get_db` (`app.config.database`).
- Produces:
  - `schemas/indec.py` (Pydantic v2, `ConfigDict(from_attributes=True)`): `ObservationOut(dataset: str, series_code: str, series_name: str, region: str, indicator_type: str, unit: str | None, period: date, value: float)`; `LatestPoint(period: date, value: float)`; `FoodVsWages(labels: list[str], ipc_alimentos: list[float], salarios: list[float])`; `IndecOverview` con campos opcionales (`None` por defecto) `ipc_general_mensual`, `ipc_general_interanual`, `ipc_alimentos_mensual`, `ipc_alimentos_interanual`, `cba`, `cbt`, `ice` (todos `LatestPoint | None`) y `food_vs_wages: FoodVsWages | None`.
  - `queries.py`: `get_series(db: Session, *, dataset: str, code: str | None = None, region: str | None = None, indicator: str | None = None, date_from: date | None = None, date_to: date | None = None, limit: int = 1000) -> list[IndecObservation]` (orden `period` ascendente); `build_food_vs_wages(ipc: dict[date, float], wages: dict[date, float], months: int = 24) -> FoodVsWages | None` (función pura: toma los últimos `months` períodos presentes en **ambas** series, reescala cada una a base 100 en el primer período común, `labels` en formato `YYYY-MM`; `None` si hay menos de 2 períodos comunes); `get_overview(db: Session) -> IndecOverview`.
  - Definición de las series del overview (todas leen el último período disponible): `ipc_general_*` = dataset `ipc_nacional`, código `0`, región `Nacional`, indicador `v_m` / `v_ia`; `ipc_alimentos_*` = igual con código `01`; `cba` = `valorizacion_canastas_cba_cbt`, código `CBA`, indicador `CBA`, región `GBA`; `cbt` ídem con `CBT`; `ice` ídem con `ICE`. `food_vs_wages`: IPC código `01` indicador `Indice` región `Nacional` vs `indice_salarios` código `0` indicador `Indice`, región `Nacional`.
  - Endpoints: `GET /api/v1/indec/series` (query: `dataset` obligatorio, `code`, `region`, `indicator`, `from`, `to` — alias de `date_from`/`date_to`, `limit` 1–5000 por defecto 1000) → `list[ObservationOut]`; `GET /api/v1/indec/overview` → `IndecOverview`. Los endpoints solo llaman a `queries.get_series` / `queries.get_overview`.

- [ ] **Step 1: Escribir los tests que fallan** (`TestClient(app)`; sustituir la base con `app.dependency_overrides[get_db] = lambda: MagicMock()` y patchear `app.services.indec.queries.get_series` / `get_overview`; limpiar `dependency_overrides` al terminar)

- `test_series_requires_dataset`: sin `dataset` → 422.
- `test_series_passes_filters_to_query`: `GET /api/v1/indec/series?dataset=ipc_nacional&code=01&region=Nacional&indicator=Indice&from=2026-01-01&to=2026-10-01&limit=50` → `get_series` llamado con esos valores (fechas como `date`) y `limit=50`.
- `test_series_rejects_limit_above_5000`: `limit=5001` → 422.
- `test_series_serializes_observations`: `get_series` devuelve un objeto con atributos → respuesta con `period` ISO y `value` numérico.
- `test_overview_with_empty_table_returns_nulls_not_error`: `get_overview` devuelve `IndecOverview()` → 200 y todos los campos `null` (Review Focus 5).
- `test_build_food_vs_wages_rebases_to_100_on_first_common_period`: IPC `{2026-01: 200, 2026-02: 220, 2026-03: 242}`, salarios `{2026-02: 50, 2026-03: 55, 2026-04: 60}` → `labels == ["2026-02", "2026-03"]`, `ipc_alimentos == [100.0, 110.0]`, `salarios == [100.0, 110.0]`.
- `test_build_food_vs_wages_limits_to_last_months`: 30 períodos comunes, `months=24` → 24 puntos, el primero vale `100.0`.
- `test_build_food_vs_wages_returns_none_with_fewer_than_two_common_periods`.

- [ ] **Step 2: Verificar que fallan** — `pytest tests/test_indec_api.py -v` → FAIL.

- [ ] **Step 3: Implementar** schemas, queries (consultas con `db.query(IndecObservation)`), endpoints y registrar el router. Mantener `/overview` tolerante a datos faltantes: cada campo se calcula por separado y queda `None` si no hay fila.

- [ ] **Step 4: Verificar que pasan** — `pytest tests/test_indec_api.py -v` → 8 passed; `pytest -q` completo sin fallos nuevos.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/indec.py backend/app/services/indec/queries.py backend/app/api/v1 backend/tests/test_indec_api.py
git commit -m "feat: endpoints /indec/series y /indec/overview"
```

---

### Task 7: Workflow de GitHub Actions y documentación

**Files:**
- Create: `.github/workflows/indec-sync.yml`
- Modify: `docs/API_DOCS.md`, `docs/DATABASE.md`, `CLAUDE.md` (una línea en "Backend": `services/indec/`)
- Test: validación sintáctica del YAML (`python -c "import yaml; yaml.safe_load(open(...))"`)

**Interfaces:**
- Consumes: `scripts/fetch_indec_data.py` (Task 5) y sus flags `--full`.
- Produces: workflow `Datos INDEC (diario)` con `schedule: cron '0 9 * * *'` y `workflow_dispatch` con input booleano `full` (default `false`); mismo patrón que `.github/workflows/dollar-6h.yml` (`permissions: contents: read`, `concurrency` por workflow sin cancelar, `timeout-minutes: 15`, acción local `./.github/actions/setup-backend`); `env` con `INDEC_API_TOKEN`, `DATABASE_URL`, `SECRET_KEY` desde `secrets`; paso `working-directory: backend` que ejecuta `python scripts/fetch_indec_data.py` agregando `--full` solo si el input es `true`.

- [ ] **Step 1: Escribir el workflow** y validar que parsea como YAML y que contiene las tres variables de entorno y el flag condicional (comando de verificación en una línea con `grep`).
- [ ] **Step 2: Documentar** en `API_DOCS.md` los dos endpoints (parámetros y forma de respuesta), en `DATABASE.md` la tabla `indec_observations` (columnas, restricción única, regla de `region`), y la línea en `CLAUDE.md`.
- [ ] **Step 3: Commit**

```bash
git add .github/workflows/indec-sync.yml docs CLAUDE.md
git commit -m "feat: workflow diario de datos del INDEC y documentación"
```

---

### Task 8: Frontend — sección INDEC en `/economia`

**Files:**
- Modify: `frontend/src/types/index.ts` (schemas zod), `frontend/src/lib/api.ts` (`getIndecOverview`), `frontend/src/app/economia/EconomiaContent.tsx` (montar la sección)
- Create: `frontend/src/app/economia/IndecSection.tsx`
- Test: verificación con `npx tsc --noEmit` y `npm run lint` (el frontend no tiene tests automatizados)

**Interfaces:**
- Consumes: respuesta de `GET /indec/overview` (Task 6).
- Produces: en `types/index.ts` — `LatestPointSchema`, `FoodVsWagesSchema`, `IndecOverviewSchema` y el tipo `IndecOverview` (mismos campos y nulabilidad que el schema Pydantic; `period` como string ISO, `value` como number). En `api.ts` — `getIndecOverview(): Promise<IndecOverview>` (`api.get("/indec/overview")` + `IndecOverviewSchema.parse`). `IndecSection` es un componente cliente sin props que pide los datos con `useQuery({ queryKey: ["indecOverview"], queryFn: getIndecOverview, staleTime: 30 * 60 * 1000 })`.

Comportamiento de `IndecSection` (texto en español):
- Si la consulta falla o todos los campos del overview son `null`: **no renderiza nada** (`return null`); la página no debe mostrar error por esto.
- Tarjetas: "IPC Alimentos" (variación interanual y mensual, formateadas con `fmtPct` dividiendo por 100 como hace el resto de la página), "IPC Nivel general" (ídem), "Canasta Básica Alimentaria" y "Canasta Básica Total" en pesos con `fmtPrice`; cada tarjeta muestra el período del dato y una cita "Fuente: INDEC". Una tarjeta cuyo valor es `null` no se muestra.
- Gráfico "IPC Alimentos vs. salarios (base 100)" con `DualLineChart` (`labels`, `a=ipc_alimentos`, `b=salarios`, `aLabel="IPC Alimentos"`, `bLabel="Salarios"`, colores `var(--bad)` y `var(--primary)`, `height=260`), solo si `food_vs_wages` no es `null`.
- Reutilizar el estilo de tarjetas y encabezados ya presentes en `EconomiaContent.tsx` (leerlo antes de escribir el componente).

- [ ] **Step 1: Agregar los schemas y `getIndecOverview`.**
- [ ] **Step 2: Escribir `IndecSection.tsx` y montarlo en `EconomiaContent.tsx`** debajo de las secciones existentes de inflación.
- [ ] **Step 3: Verificar** — `cd frontend && npx tsc --noEmit` (Expected: sin salida, exit 0) y `npm run lint` (Expected: sin errores; los warnings preexistentes de `<img>` y fuentes no cuentan).
- [ ] **Step 4: Commit**

```bash
git add frontend/src
git commit -m "feat: sección de datos del INDEC en la pantalla de economía"
```

---

### Task 9: Despliegue y verificación con datos reales

**Files:** ninguno nuevo (opcionalmente `docs/` si surge algo que documentar).

**Interfaces:** Consumes todo lo anterior. Este task toca producción: **pedir confirmación al usuario antes de cada paso marcado con ⚠**.

- [ ] **Step 1: Revisión previa.** `pytest -q` completo (Expected: todo verde) y `git diff main --stat` sin archivos inesperados (`backend/.env` no debe aparecer).
- [ ] **Step 2 ⚠: Aplicar la migración a Neon.** Con la `.env` local apuntando a Neon, `cd backend && alembic upgrade head`. Es aditiva (tabla nueva). Verificar con `alembic current` que quedó en la revisión nueva.
- [ ] **Step 3 ⚠: Backfill inicial.** `python scripts/fetch_indec_data.py --full`. Expected: una línea por dataset con `fetched > 0`, exit code 0. Ejecutarlo una segunda vez y confirmar que `inserted` es 0 (idempotencia; `updated` puede ser > 0 si el INDEC revisó valores).
- [ ] **Step 4: Verificar los cortes contra la base.** Consultar con SQL (Neon) el conteo por `dataset`, `region` e `indicator_type`, y confirmar: IPC trae `Nacional` y `GBA`, hay `Precio promedio` solo en `GBA`, salarios tiene `region = 'Nacional'`, no hay filas con `value` nulo. Anotar el tamaño total de la tabla; si supera el orden de 100.000 filas, avisar al usuario antes de seguir.
- [ ] **Step 5: Probar la API local.** `uvicorn app.main:app --reload` y `curl localhost:8000/api/v1/indec/overview` (Expected: campos poblados y `food_vs_wages` con 24 puntos) y `curl "localhost:8000/api/v1/indec/series?dataset=indice_salarios&code=0&indicator=Indice&limit=3"`.
- [ ] **Step 6: Verificar la UI.** Levantar el frontend con `npm run dev` (Turbopack es obligatorio por el `?` en el path) y revisar `/economia` en el navegador con Playwright: las tarjetas y el gráfico se ven, sin errores de consola, también en modo oscuro.
- [ ] **Step 7 ⚠: Subir y activar el job.** Con el usuario: merge a `main` (dispara el deploy en Render y Vercel), luego `gh workflow run indec-sync.yml` y `gh run watch` — Expected: éxito en menos de 5 minutos. Confirmar que el usuario cargó `INDEC_API_TOKEN` en los secrets antes (`gh secret list`).
- [ ] **Step 8: Actualizar memoria del proyecto** con una nota breve (qué se hizo, token vence 2027-05-13, dónde está el registro de datasets).
