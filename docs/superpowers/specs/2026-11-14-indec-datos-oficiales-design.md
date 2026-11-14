# Datos oficiales del INDEC — Diseño

Fecha: 2026-11-14 · Estado: pendiente de aprobación

## Intención y por qué

"A Cuanto Está?" compara precios de supermercados con contexto económico. Hoy ese
contexto (inflación, dólar, UVA, riesgo país) viene de ArgentinaDatos y DolarAPI.
El INDEC publica ahora una API oficial (BETA, `https://api.indec.gob.ar`) con
datos más ricos: IPC por rubro y por región, **precios promedio en pesos por
producto**, canastas básicas e índice de salarios.

Se quiere sumar esos datos de forma **robusta, prolija, mantenible y escalable**
(palabras del usuario): que agregar un dataset nuevo sea barato y que una caída o
cambio del INDEC no rompa la app.

Qué gana el usuario final: poder contrastar lo que suben los supermercados contra
lo que dice el dato oficial (IPC Alimentos), ver cuánto cuesta la canasta básica y
cómo evolucionan precios vs. salarios.

## Objetivos

1. Capa genérica de ingesta INDEC: un cliente, un registro declarativo de qué
   cortes se guardan, un cargador genérico. Sumar un dataset = agregar una entrada
   al registro, sin código nuevo de ingesta.
2. Persistir los datos en una tabla propia, en formato largo, con carga idempotente
   (upsert), porque el INDEC revisa valores publicados.
3. Job programado en GitHub Actions que mantenga los datos al día.
4. Endpoints de lectura en el backend y una sección INDEC en `/economia`.
5. Datasets de la primera versión: `ipc_nacional`, `valorizacion_canastas_cba_cbt`,
   `indice_salarios`.

## No-objetivos

- No se reemplaza ArgentinaDatos ni se toca `economic_indicators` (dólar, UVA,
  riesgo país siguen igual). La inflación de ArgentinaDatos queda como está.
- No se ingieren datasets irrelevantes para precios (población, comercio exterior,
  industria, pobreza/EPH, obras públicas).
- No se ingiere el volcado completo (IPC: 235.683 filas; mayoristas: 234.260).
- v1 no incluye la comparación automática "precio de un producto de la app vs.
  precio promedio INDEC del mismo producto" (los datos se ingieren y quedan
  disponibles por API; el cruce y su UI son una fase posterior).
- `sipm_precios_mayoristas` y `canasta-crianza` quedan para después: el diseño debe
  permitir sumarlos solo con el registro.

## Anti-objetivos (fracaso aunque "funcione")

- Que el token quede en el repo, en logs o en el frontend.
- Que el job termine "en verde" con 0 filas cuando el INDEC falló (indistinguible de
  un día sin novedades). Debe fallar con código distinto de 0.
- Que una caída del INDEC afecte las páginas: la API sirve lo ya guardado.
- Volcar series que nadie usa y hacer crecer la base sin control (hay límite de
  almacenamiento en Neon).
- Que sumar un dataset exija tocar cliente, cargador y workflow.

## Restricciones y hechos verificados

- Autenticación: `Authorization: Bearer <token>`. Token rol `basic`, vence el
  **2027-05-13**. Se guarda en `INDEC_API_TOKEN` (`backend/.env`, ignorado por git;
  `.env.example` con valor vacío; secret de GitHub cargado por el usuario).
- Catálogo público: `GET /api/datasets` (+ `?page=2`, 19 datasets). Datos:
  `GET /v1/<slug>` (estilo PostgREST: filtros, `order`, `select`, `limit`).
- El servidor devuelve **máximo 1.000 filas por request** → hay que paginar.
- Todas las filas comparten columnas: `clasificador, nivel, codigo, descripcion,
  periodo (YYYYMM), anio, mes, indicador, tipo_de_indicador, region,
  unidad_de_medida, valor, observaciones`. `indice_salarios` no tiene `region`.
- Dimensiones reales:
  - IPC: regiones `Nacional, GBA, Pampeana, Noreste, Noroeste, Cuyo, Patagonia`;
    niveles `Nivel General, División, Grupo, Clase, Categoría, Producto`;
    tipos `Indice, v_m, v_ia, v_acum, Incidencia_*, Precio promedio`. Último
    período al 2026-11-14: 202610. Códigos clave: `0` Nivel general,
    `01` Alimentos y bebidas no alcohólicas, `01.1` Alimentos.
  - Canastas: región GBA; códigos `CBA, CBT, ICE` (adulto equivalente) y
    `CBA/CBT H1–H3` (hogares); tipos `CBA, CBT, ICE, Hogar n, v_m, v_ia`.
  - Salarios: códigos `0, 100, 110, 120, 121, 122, 200`; tipos
    `Indice, v_m, v_ia, v_acum`.
- Infra existente a respetar: timestamps `timestamptz` con `utcnow_aware`; Alembic
  migra con la URL no pooled de Neon; Render ejecuta `alembic upgrade head` al
  arrancar; el patrón de workflows es `.github/workflows/*.yml` con la acción local
  `setup-backend`, `concurrency` y `timeout-minutes`.
- Lección previa: los scripts que escriben en producción deben persistir por
  unidad de trabajo (acá: un commit por dataset), no solo al final.

## Enfoques considerados

1. **Capa genérica con registro de datasets (elegido).** Tabla de observaciones en
   formato largo + cliente único con paginación + registro declarativo + cargador
   genérico. Más trabajo inicial, mínimo costo por dataset nuevo, cambios del INDEC
   aislados en un lugar.
2. Una tabla y un cliente por dataset. Explícito pero duplica código y migraciones
   en cada dataset: no escala.
3. Forzar todo en `economic_indicators` (usando `IPC_CATEGORY`/`DataSource.INDEC`).
   Rápido, pero el modelo `(tipo, fecha, valor, categoría)` no tiene lugar para
   región, nivel ni tipo de indicador; habría que codificarlos como texto en
   `category`. Frágil: descartado.

Elegido por el usuario: **opción 1**.

## Diseño

### Módulos (`backend/app/services/indec/`)

- `client.py` — `IndecClient`: arma URL y headers (Bearer), pagina (páginas de
  1.000), timeout y reintentos con backoff ante red/5xx, **lanza excepción** si
  agota reintentos o recibe 401/403 (no devuelve lista vacía). Nunca loguea el
  token. Al iniciar avisa (warning) si el token vence en menos de 30 días
  (decodificando el payload del JWT, sin verificar firma).
- `registry.py` — registro declarativo. Cada `DatasetSpec` define: `slug`, filtros
  del lado servidor (para no bajar lo que no se usa) y las series a conservar.
  Es la única parte que se edita para sumar datasets.
- `loader.py` — normaliza filas del INDEC a observaciones y hace upsert por lotes;
  un commit por dataset; devuelve conteos (insertadas / actualizadas).
- `sync.py` — orquesta: por dataset, modo incremental (desde el último período
  guardado menos 3 meses, para capturar revisiones) o `--full` (backfill).

### Tabla `indec_observations` (nueva migración Alembic)

Formato largo. Campos: `dataset`, `classifier`, `level`, `series_code`,
`series_name`, `region` (**NOT NULL**: cuando el dataset no trae región, como
`indice_salarios`, se guarda `Nacional`; un `NULL` rompería la restricción única,
porque en PostgreSQL dos `NULL` no cuentan como iguales y el upsert duplicaría
filas), `indicator_type`, `unit`,
`period` (fecha, primer día del mes), `value` (Numeric), `notes`, `ingested_at`
(timestamptz). Restricción única sobre
`(dataset, classifier, level, series_code, region, indicator_type, period)` y
un índice para las consultas de lectura por serie y rango de fechas. Carga con
`INSERT … ON CONFLICT DO UPDATE`.

### Cortes de la v1 (en el registro)

| Dataset | Qué se conserva | Motivo |
|---|---|---|
| `ipc_nacional` | Códigos `0`, `01`, `01.1`; tipos `Indice, v_m, v_ia, v_acum`; regiones `Nacional` y `GBA` | Comparación central con precios de alimentos |
| `ipc_nacional` | Nivel `Producto`, tipo `Precio promedio`, región `GBA` | Precios de referencia oficiales por producto |
| `valorizacion_canastas_cba_cbt` | Todo (1.651 filas, región GBA) | Chico y todo útil |
| `indice_salarios` | Códigos `0, 100, 110, 120, 200`; tipos `Indice, v_m, v_ia` | Poder adquisitivo vs IPC alimentos |

### Job (`.github/workflows/indec-sync.yml`)

Diario, en modo incremental (barato: pocos requests) para no depender de la fecha
exacta de publicación del IPC (mitad de mes). `workflow_dispatch` con opción
`full` para backfill. Mismo patrón de `concurrency` y `timeout-minutes` que los
otros workflows; secrets `INDEC_API_TOKEN`, `DATABASE_URL`, `SECRET_KEY`.
El script (`scripts/fetch_indec_data.py`) sale con código distinto de 0 si falta el
token, si el INDEC falla, o si un dataset que debería traer filas trae 0.

### API del backend (`/api/v1/indec/`)

- `GET /series` — lectura genérica con filtros: `dataset`, `code`, `region`,
  `indicator`, `from`, `to`.
- `GET /overview` — último valor de las series que usa la UI: IPC general y
  Alimentos (mensual e interanual), CBA, CBT, ICE y la serie IPC Alimentos vs
  salarios (base 100 desde un período común).
- Solo lee de la base propia: si el INDEC cae, la API sigue respondiendo.

### Frontend (`/economia`)

Nueva sección "INDEC" con tarjetas (IPC Alimentos, canasta CBA/CBT) y un gráfico de
dos líneas (IPC Alimentos acumulado vs índice de salarios). Reutiliza los
componentes de gráficos existentes. Los datos se piden con el mismo cliente de API
del frontend.

### Pruebas

Unitarias, sin red ni base real (mismo estilo que `test_economic_data_client.py` y
`test_economic_processor.py`): cliente (paginación, header Bearer, reintentos,
falla ruidosa ante 401/agotamiento, aviso de vencimiento), registro (conversión a
filtros), cargador (upsert idempotente, una sola consulta por lote), script (exit
codes) y API (filtros y forma de respuesta). Opcional y fuera de CI: un script de
humo contra el INDEC real.

## Decisiones que quedan al implementador

Tipos y nombres exactos de columnas e índices; sintaxis exacta de los filtros
PostgREST (`in.(…)`, `gte`) y estrategia de paginación (Range vs offset);
tamaño de lote del upsert; forma exacta del JSON de `/overview`; qué componentes
de gráfico reutilizar; textos de la UI.

## Llamadas hechas por mí (no pedidas por el usuario)

- Job **diario incremental** en vez de mensual.
- Región `GBA` (más `Nacional` en el IPC general) en vez de las 7 regiones.
- Lista concreta de códigos de IPC y salarios de la tabla de cortes.
- Ventana de revisión de 3 meses en el modo incremental.
- Aviso de vencimiento del token a 30 días.
- Comparación producto-de-la-app vs precio promedio INDEC fuera de la v1.
- `region` obligatoria en la tabla; los datasets sin región se guardan como
  `Nacional`.
