# Automatización de scrapers e indicadores económicos (Fase 5)

## Contexto

El roadmap del proyecto (`CLAUDE.md`) planteaba Celery + Redis para automatizar
el scraping periódico. En la práctica:

- Ninguno de los 9 scrapers (`backend/app/scrapers/*.py`) usa Selenium —
  todos consultan APIs JSON directas (Constructor.io, VTEX, APIs propias de
  cada supermercado) vía `requests`.
- No existe código de Celery en el repo pese a estar en `requirements.txt`.
- Hoy el scraping y la carga de indicadores económicos se corren a mano:
  `python scripts/populate_<super>_products.py` y
  `python scripts/fetch_economic_data.py` contra el `DATABASE_URL` de `.env`.
- El backend corre en Render (plan free) y la base en Supabase.
- El repositorio (`AgustinLuconi/A_Cuanto_Esta`) es **público**, por lo que
  GitHub Actions con runners estándar es gratis sin límite de minutos
  mensuales (único tope real: 6 horas por job individual).

## Decisión: GitHub Actions en vez de Celery + Redis

El rol de Celery acá sería únicamente disparar tareas en un horario fijo —
no hay colas, reintentos distribuidos, ni resultados asíncronos que un
cliente consulte. Es un cron job. Usar Celery + Redis es sobre-ingeniería
para este caso y además requiere infraestructura paga en Render.

**Alternativa elegida**: tres workflows de GitHub Actions con distintos
`schedule`, cada uno reutilizando scripts existentes sin modificarlos,
contra Supabase directo.

## Arquitectura

```
GitHub Actions
├── scrape-daily.yml       (cron diario) ──► 9 steps, uno por supermercado
│                                            └─ populate_<super>_products.py
├── dollar-6h.yml          (cron c/6h)   ──► fetch_economic_data.py --dollars
└── inflation-daily.yml    (cron diario) ──► fetch_economic_data.py --inflation
                                                      │
                                                      ▼
                                          Supabase (Session Pooler)
```

Tres workflows separados en vez de uno solo con múltiples schedules: cada
cron de GitHub Actions dispara el workflow completo, no jobs individuales
dentro de él, así que mezclar cadencias distintas en un único archivo
obligaría a lógica condicional (`if: github.event.schedule == ...`) sin
necesidad. Separado es más simple de leer, debuggear y re-disparar a mano.

## Componentes

### `.github/workflows/scrape-daily.yml`
- Trigger `schedule`: `cron: '0 6 * * *'` (diario, ~03:00 ART) + `workflow_dispatch`
- Job `scrape` con 9 steps (uno por supermercado), cada uno `continue-on-error: true`
- Step final que revisa el `outcome` de los 9 anteriores y falla el job si
  alguno fue `failure`, para que quede visible en rojo aunque el resto haya
  corrido bien

### `.github/workflows/dollar-6h.yml`
- Trigger `schedule`: `cron: '0 */6 * * *'` (cada 6 horas) + `workflow_dispatch`
- Un solo step: `python scripts/fetch_economic_data.py --dollars`

### `.github/workflows/inflation-daily.yml`
- Trigger `schedule`: `cron: '0 7 * * *'` (diario, corrido una hora respecto
  al de scrapers para no competir por el mismo minuto) + `workflow_dispatch`
- Un solo step: `python scripts/fetch_economic_data.py --inflation`
- Es idempotente y de bajo costo: al ser datos de INDEC publicados
  mensualmente, la mayoría de las corridas no van a encontrar registros
  nuevos, pero eso no genera ningún efecto secundario negativo

### GitHub Secrets (compartidos por los tres workflows)
- `DATABASE_URL` — connection string del Session Pooler de Supabase
  (mismo formato que usa Render:
  `postgresql://postgres.<ref>:<pass>@aws-1-us-east-2.pooler.supabase.com:5432/postgres`)
- `SECRET_KEY` — dummy, requerido porque `Settings` lo exige aunque no se
  use en estos scripts

### Scripts reutilizados sin cambios
- Los 9 `backend/scripts/populate_*_products.py`
- `backend/scripts/fetch_economic_data.py` (ya soporta `--dollars` e
  `--inflation` por separado)

## Flujo de datos

**scrape-daily.yml**: cron dispara → checkout + setup Python 3.11 →
`pip install -r backend/requirements.txt` → 9 steps secuenciales, uno por
supermercado → cada script hace upsert de productos e inserta filas nuevas
en `price_history` → step de resumen evalúa fallas parciales.

**dollar-6h.yml / inflation-daily.yml**: mismo checkout/setup/install →
un único step que corre `fetch_economic_data.py` con el flag
correspondiente → inserta filas nuevas en `economic_indicators`.

## Manejo de errores

- Aislamiento por supermercado en `scrape-daily.yml`: `continue-on-error: true`
  evita que la falla de una API (ej. Coto cambia su endpoint) bloquee a
  los otros 8
- `BaseScraper._get()` ya reintenta ante HTTP 429 con backoff exponencial
  y hace `session.rollback()` por término de búsqueda sin abortar el script
- GitHub manda mail automático al dueño del repo cuando un workflow falla
  (activado por default) — no hace falta notificación custom
- Nota operativa: GitHub deshabilita automáticamente los workflows
  programados (`schedule`) si el repositorio no tiene actividad (commits)
  durante 60 días. Con cadencias diarias/cada 6h esto no debería ser un
  problema mientras el proyecto siga activo, pero si el repo queda inactivo
  mucho tiempo hay que reactivarlos a mano desde la pestaña Actions.

## Testing / validación

- Disparar cada uno de los tres workflows manualmente vía `workflow_dispatch`
  antes de confiar en el cron
- Confirmar en Supabase que `price_history` y `economic_indicators` suman
  filas nuevas después de cada corrida, y que no aparecen productos
  duplicados
- Forzar una falla en un step (ej. romper temporalmente una URL) para
  verificar que el step de resumen de `scrape-daily.yml` marca el job en
  rojo correctamente

## Fuera de alcance

- No se instala Celery ni Redis
- No se modifican los scrapers ni los scripts `populate_*` / `fetch_economic_data.py` existentes
- No se cubre la ejecución on-demand desde la API/frontend (si se necesita
  en el futuro, es un proyecto aparte)
