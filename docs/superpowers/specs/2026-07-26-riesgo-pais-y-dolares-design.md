# Riesgo país + todos los tipos de dólar

## Contexto

El usuario pidió incorporar el indicador "riesgo país" en dos pantallas del
frontend (el panel derecho de "buscar" y la pantalla de economía), y en la
pantalla de economía mostrar todos los tipos de dólar disponibles, no solo
blue y oficial.

Al explorar el código se encontró que:

- El modelo (`IndicatorType.RISK_COUNTRY`), el schema (`EconomicContext.risk_country`)
  y el endpoint `/context` **ya están preparados** para riesgo país — nunca
  se conectó ningún fetch, así que el campo siempre devuelve `null`.
- `/v1/finanzas/indices/riesgo-pais/ultimo` y `/v1/finanzas/indices/riesgo-pais`
  devuelven `{fecha, valor}`, el mismo shape que ya usa `InflationRecord`.
- `/v1/cotizaciones/dolares` (sin especificar casa) devuelve el **histórico
  completo combinado de 8 casas** en una sola llamada (~30.000 registros
  desde 2011), con el mismo shape que `DollarRecord` (`casa`, `compra`,
  `venta`, `fecha`). Las 8 casas: `blue`, `oficial`, `mayorista`, `bolsa`
  (MEP), `contadoconliqui` (CCL), `cripto`, `tarjeta`, `solidario`.
  `solidario` dejó de actualizarse en dic-2023 (dólar ahorro + impuesto
  PAIS, derogado) — se excluye de "todos los dólares".
- El modelo ya tenía `DOLLAR_MEP` y `DOLLAR_CCL` en el enum, alimentados hoy
  vía `dolarapi.com` (cotización en tiempo real) porque el cliente de
  ArgentinaDatos solo tenía métodos para blue/oficial. Faltan
  `DOLLAR_MAYORISTA`, `DOLLAR_CRIPTO`, `DOLLAR_TARJETA`.

## Decisiones

- **ArgentinaDatos pasa a ser la fuente principal para todos los tipos de
  dólar** (histórico completo, una sola llamada). **`dolarapi.com` se
  mantiene como fallback** para blue/oficial/MEP/CCL — si algún día
  ArgentinaDatos falla, dolarapi sigue completando el dato del día. El
  "skip if exists" por `(indicator_type, date)` ya evita duplicados si
  ambas fuentes escriben la misma fecha; no hace falta lógica adicional
  de coordinación entre ambas.
- **Optimizar el guardado masivo**: la lógica actual de
  `EconomicDataProcessor` hace un `SELECT` (`_exists()`) por cada registro
  antes de insertarlo. Con 3-4 registros por corrida diaria no se nota,
  pero la carga inicial de dólares trae ~30.000 filas y la de riesgo país
  datos desde 1999 — un `SELECT` por fila sería un cuello de botella real.
  Se reemplaza por una única consulta que trae las fechas ya guardadas por
  tipo de indicador (`SELECT date FROM economic_indicators WHERE
  indicator_type = :type`), y se filtra en memoria con un `set` antes de
  insertar.
- No se crea un gráfico multi-línea para los 7 dólares (ilegible). Se
  muestran como grid de cards con valor + variación, y el gráfico de línea
  doble existente (blue vs. oficial) queda como está.
- El gráfico histórico de riesgo país reutiliza el componente `BarChart`
  ya existente (mismo que usa inflación mensual) — no se crea un
  componente de gráfico nuevo.

## Backend — cliente y persistencia

### `app/services/economic_data/client.py`
- `ArgentinaDatosClient.get_risk_country() -> list[InflationRecord]`
  — GET `/v1/finanzas/indices/riesgo-pais`
- `ArgentinaDatosClient.get_all_dollars() -> list[DollarRecord]`
  — GET `/v1/cotizaciones/dolares`
- `DolarAPIClient` no cambia (se mantiene como está, sigue usándose)

### `app/models/economic_indicator.py`
- Agregar a `IndicatorType`: `DOLLAR_MAYORISTA`, `DOLLAR_CRIPTO`,
  `DOLLAR_TARJETA`
- **Nota de migración**: agregar valores a un enum nativo de Postgres
  requiere `ALTER TYPE indicatortype ADD VALUE '...'` — Alembic
  autogenerate no lo detecta solo, hay que escribir la migración a mano
  con `op.execute(...)` para cada valor nuevo

### `app/services/economic_data/processor.py`
- Nuevo método auxiliar `_existing_dates(indicator_type) -> set[date]`:
  una sola query que trae todas las fechas ya guardadas para ese tipo
- `save_all_dollars(records: list[DollarRecord]) -> dict[str, int]`:
  agrupa por `casa`, mapea a `IndicatorType` vía un dict
  `_CASA_TO_DOLLAR_TYPE` (`blue`, `oficial`, `mayorista`, `bolsa`→MEP,
  `contadoconliqui`→CCL, `cripto`, `tarjeta`; ignora `solidario` y
  cualquier casa desconocida), usa `_existing_dates()` una vez por tipo
  en vez de `_exists()` por fila, y hace un solo `commit()` al final.
  Devuelve un dict `{casa: cantidad_guardada}` para logging
- Riesgo país no necesita método nuevo: `save_inflation_data(records,
  IndicatorType.RISK_COUNTRY)` ya es genérico sobre fecha/valor

### `scripts/fetch_economic_data.py`
- Nuevo flag `--risk-country` (incluido en el comportamiento `--all`)
- `--dollars` ahora también llama a `client.get_all_dollars()` +
  `processor.save_all_dollars()`, ANTES de la llamada existente a
  `dolarapi.com` (que queda igual, como fallback del día actual)

## Backend — API

### `app/schemas/economic.py` — `EconomicContext`
Nuevos campos opcionales (`Decimal`, igual que los existentes):
`dollar_mayorista`, `dollar_mep`, `dollar_ccl`, `dollar_cripto`,
`dollar_tarjeta`, y sus respectivos `_change` (variación % vs. registro
anterior, mismo criterio que `dollar_blue_change`/`dollar_oficial_change`)
más `risk_country_change` (el valor `risk_country` ya existía, faltaba la
variación).

### `app/api/v1/endpoints/economic.py`
- Extender `_CONTEXT_TYPES` con los 3 tipos de dólar nuevos
- Refactor: el cálculo de "valor actual + variación %" está repetido a
  mano para blue y oficial (~8 líneas cada uno). Con 7 tipos de dólar se
  extrae a un helper `_dollar_value_and_change(db, indicator_type) ->
  tuple[Decimal | None, Decimal | None]` reutilizado para los 7
- Nuevo endpoint `GET /api/v1/economic/risk-country/history?months=N`
  (default 12, igual patrón que `/inflation/history`), devuelve
  `list[schemas_eco.EconomicIndicator]` para `RISK_COUNTRY`

## Frontend

### `src/types/index.ts`
Extender `EconomicContext` con los mismos campos nuevos del schema backend.

### `src/lib/api.ts`
Nueva función `getRiskCountryHistory(months: number)`.

### `src/components/layout/EconomicSidebar.tsx`
Una `IndicatorRow` nueva: "Riesgo país" — valor entero + "pb", badge de
variación, subtítulo con fuente (ej. "JP Morgan EMBI+"), mismo patrón que
las filas existentes.

### `src/app/economia/page.tsx`
- 5ta `IndicatorCard` en el grid superior: Riesgo País (valor + variación
  + sparkline con los últimos puntos de `getRiskCountryHistory`)
- Sección nueva "Todos los dólares": grid de 7 cards compactas (oficial,
  blue, mayorista, MEP, CCL, cripto, tarjeta), cada una con valor actual
  (venta) y variación %, alimentadas desde `EconomicContext`
- Nuevo card de gráfico "Riesgo país histórico" reutilizando `BarChart`
  (mismo componente que "Inflación mensual"), alimentado por
  `getRiskCountryHistory`
- El gráfico dual blue/oficial existente no cambia

## Manejo de errores

- Si `/v1/finanzas/indices/riesgo-pais` o `/v1/cotizaciones/dolares` no
  responden, los clientes ya devuelven `[]` (mismo patrón que los métodos
  existentes) — el script loguea "0 nuevos registros" y sigue sin abortar
- Casas desconocidas o `solidario` en la respuesta combinada de dólares se
  ignoran silenciosamente en `save_all_dollars` (no rompen el resto del
  procesamiento)

## Testing / validación

- Correr `fetch_economic_data.py --dollars --risk-country` una vez contra
  Supabase y confirmar que:
  - Se insertan los ~30.000 registros de dólares sin duplicar los que ya
    existían de blue/oficial
  - `economic_indicators` tiene filas para `dollar_mayorista`,
    `dollar_cripto`, `dollar_tarjeta`, `risk_country`
  - Correrlo una segunda vez guarda 0 registros nuevos (dedup funciona)
- Verificar que `/api/v1/economic/context` devuelve los 5 valores de dólar
  nuevos + `risk_country` + `risk_country_change`
- Verificar `/api/v1/economic/risk-country/history` devuelve datos
  ordenados por fecha
- Revisar visualmente ambas pantallas del frontend (sidebar y economía)

## Fuera de alcance

- No se agrega gráfico histórico para los 7 tipos de dólar (solo blue vs.
  oficial, como hoy)
- No se retira `dolarapi.com` del flujo
- No se migra el dato histórico de `solidario`
