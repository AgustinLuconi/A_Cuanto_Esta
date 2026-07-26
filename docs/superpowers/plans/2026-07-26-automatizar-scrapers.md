# Automatización de scrapers e indicadores económicos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatizar vía GitHub Actions el scraping diario de los 9 supermercados y la carga de indicadores económicos (dólar cada 6h, inflación diaria) contra Supabase, sin Celery/Redis.

**Architecture:** Tres workflows de GitHub Actions (`scrape-daily.yml`, `dollar-6h.yml`, `inflation-daily.yml`), cada uno con su propio `schedule` + `workflow_dispatch`, compartiendo una composite action (`setup-backend`) para instalar Python y dependencias. Reutilizan sin modificar los scripts `backend/scripts/populate_*_products.py` y `backend/scripts/fetch_economic_data.py`, conectando a Supabase vía secrets de repo.

**Tech Stack:** GitHub Actions (`ubuntu-latest`, Python 3.11), `gh` CLI para configurar secrets, scripts Python existentes sin cambios.

## Global Constraints

- Spec de referencia: `docs/superpowers/specs/2026-07-26-automatizar-scrapers-design.md`
- No se instala Celery ni Redis
- No se modifican los scrapers ni los scripts `populate_*` / `fetch_economic_data.py`
- Python 3.11 (misma versión que Render, ver `render.yaml`)
- Secrets requeridos, ambos a nivel repo (Settings → Secrets and variables → Actions): `DATABASE_URL`, `SECRET_KEY`
- Repo público (`AgustinLuconi/A_Cuanto_Esta`) → Actions gratis sin límite de minutos, tope de 6h por job
- Cron times (UTC): scrapers `0 6 * * *`, dólar `0 */6 * * *`, inflación `0 7 * * *`

---

### Task 1: Composite action `setup-backend`

**Files:**
- Create: `.github/actions/setup-backend/action.yml`

**Interfaces:**
- Consumes: nada (asume que el caller ya hizo `actions/checkout@v4` antes de invocar esta action)
- Produces: entorno con Python 3.11 y `backend/requirements.txt` instalado, listo para que el workflow caller corra cualquier script de `backend/scripts/`. Se invoca en los workflows como `uses: ./.github/actions/setup-backend`

- [ ] **Step 1: Crear el archivo de la composite action**

```yaml
# .github/actions/setup-backend/action.yml
name: "Setup backend"
description: "Instala Python 3.11 y las dependencias de backend/requirements.txt"
runs:
  using: "composite"
  steps:
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - name: Instalar dependencias
      shell: bash
      run: pip install -r backend/requirements.txt
```

- [ ] **Step 2: Validar sintaxis YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/actions/setup-backend/action.yml')); print('YAML OK')"`
Expected: `YAML OK`

- [ ] **Step 3: Commit**

```bash
git add .github/actions/setup-backend/action.yml
git commit -m "ci: agregar composite action setup-backend para workflows de automatización"
```

---

### Task 2: Workflow `scrape-daily.yml`

**Files:**
- Create: `.github/workflows/scrape-daily.yml`

**Interfaces:**
- Consumes: composite action `./.github/actions/setup-backend` (Task 1); scripts `backend/scripts/populate_atomo_products.py`, `populate_carrefour_products.py`, `populate_chango_mas_products.py`, `populate_coto_products.py`, `populate_dia_products.py`, `populate_disco_products.py`, `populate_jumbo_products.py`, `populate_la_anonima_products.py`, `populate_vea_products.py` (ya existen, sin cambios); secrets `DATABASE_URL`, `SECRET_KEY`
- Produces: workflow `Scrape supermercados (diario)`, disparable a mano vía `gh workflow run scrape-daily.yml`

- [ ] **Step 1: Crear el workflow**

```yaml
# .github/workflows/scrape-daily.yml
name: Scrape supermercados (diario)

on:
  schedule:
    - cron: '0 6 * * *'
  workflow_dispatch: {}

jobs:
  scrape:
    runs-on: ubuntu-latest
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      SECRET_KEY: ${{ secrets.SECRET_KEY }}
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-backend

      - name: Coto
        id: coto
        continue-on-error: true
        working-directory: backend
        run: python scripts/populate_coto_products.py

      - name: Carrefour
        id: carrefour
        continue-on-error: true
        working-directory: backend
        run: python scripts/populate_carrefour_products.py

      - name: Disco
        id: disco
        continue-on-error: true
        working-directory: backend
        run: python scripts/populate_disco_products.py

      - name: Atomo
        id: atomo
        continue-on-error: true
        working-directory: backend
        run: python scripts/populate_atomo_products.py

      - name: Vea
        id: vea
        continue-on-error: true
        working-directory: backend
        run: python scripts/populate_vea_products.py

      - name: Jumbo
        id: jumbo
        continue-on-error: true
        working-directory: backend
        run: python scripts/populate_jumbo_products.py

      - name: Dia
        id: dia
        continue-on-error: true
        working-directory: backend
        run: python scripts/populate_dia_products.py

      - name: La Anonima
        id: la_anonima
        continue-on-error: true
        working-directory: backend
        run: python scripts/populate_la_anonima_products.py

      - name: Chango Mas
        id: chango_mas
        continue-on-error: true
        working-directory: backend
        run: python scripts/populate_chango_mas_products.py

      - name: Verificar resultados
        if: always()
        run: |
          FAILED=0
          for outcome in \
            "${{ steps.coto.outcome }}" \
            "${{ steps.carrefour.outcome }}" \
            "${{ steps.disco.outcome }}" \
            "${{ steps.atomo.outcome }}" \
            "${{ steps.vea.outcome }}" \
            "${{ steps.jumbo.outcome }}" \
            "${{ steps.dia.outcome }}" \
            "${{ steps.la_anonima.outcome }}" \
            "${{ steps.chango_mas.outcome }}"; do
            echo "outcome: $outcome"
            if [ "$outcome" = "failure" ]; then
              FAILED=1
            fi
          done
          if [ "$FAILED" = "1" ]; then
            echo "::error::Al menos un supermercado falló. Revisá los logs de los steps de arriba."
            exit 1
          fi
```

- [ ] **Step 2: Validar sintaxis YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/scrape-daily.yml')); print('YAML OK')"`
Expected: `YAML OK`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/scrape-daily.yml
git commit -m "ci: agregar workflow diario de scraping de los 9 supermercados"
```

---

### Task 3: Workflow `dollar-6h.yml`

**Files:**
- Create: `.github/workflows/dollar-6h.yml`

**Interfaces:**
- Consumes: composite action `./.github/actions/setup-backend` (Task 1); script `backend/scripts/fetch_economic_data.py --dollars` (ya existe, sin cambios); secrets `DATABASE_URL`, `SECRET_KEY`
- Produces: workflow `Dólar (cada 6 horas)`, disparable a mano vía `gh workflow run dollar-6h.yml`

- [ ] **Step 1: Crear el workflow**

```yaml
# .github/workflows/dollar-6h.yml
name: Dólar (cada 6 horas)

on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch: {}

jobs:
  fetch-dollar:
    runs-on: ubuntu-latest
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      SECRET_KEY: ${{ secrets.SECRET_KEY }}
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-backend
      - name: Fetch dólar
        working-directory: backend
        run: python scripts/fetch_economic_data.py --dollars
```

- [ ] **Step 2: Validar sintaxis YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/dollar-6h.yml')); print('YAML OK')"`
Expected: `YAML OK`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/dollar-6h.yml
git commit -m "ci: agregar workflow de dólar cada 6 horas"
```

---

### Task 4: Workflow `inflation-daily.yml`

**Files:**
- Create: `.github/workflows/inflation-daily.yml`

**Interfaces:**
- Consumes: composite action `./.github/actions/setup-backend` (Task 1); script `backend/scripts/fetch_economic_data.py --inflation` (ya existe, sin cambios); secrets `DATABASE_URL`, `SECRET_KEY`
- Produces: workflow `Inflación (diario)`, disparable a mano vía `gh workflow run inflation-daily.yml`

- [ ] **Step 1: Crear el workflow**

```yaml
# .github/workflows/inflation-daily.yml
name: Inflación (diario)

on:
  schedule:
    - cron: '0 7 * * *'
  workflow_dispatch: {}

jobs:
  fetch-inflation:
    runs-on: ubuntu-latest
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      SECRET_KEY: ${{ secrets.SECRET_KEY }}
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-backend
      - name: Fetch inflación
        working-directory: backend
        run: python scripts/fetch_economic_data.py --inflation
```

- [ ] **Step 2: Validar sintaxis YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/inflation-daily.yml')); print('YAML OK')"`
Expected: `YAML OK`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/inflation-daily.yml
git commit -m "ci: agregar workflow de inflación diario"
```

---

### Task 5: Configurar GitHub Secrets

**Files:** ninguno (configuración de repo en GitHub, no código)

**Interfaces:**
- Consumes: `backend/.env` local, específicamente la línea `DATABASE_URL=...` (el pooler de Supabase que ya está validado funcionando en Render)
- Produces: secrets de repo `DATABASE_URL` y `SECRET_KEY`, consumidos por los tres workflows de las Tasks 2-4 vía `${{ secrets.* }}`

- [ ] **Step 1: Confirmar que `gh` está autenticado contra el repo correcto**

Run: `gh repo view --json nameWithOwner,visibility`
Expected: `{"nameWithOwner":"AgustinLuconi/A_Cuanto_Esta","visibility":"PUBLIC"}`

- [ ] **Step 2: Setear `DATABASE_URL` sin exponerla en la terminal**

Run:
```bash
cd backend
grep '^DATABASE_URL=' .env | cut -d '=' -f2- | gh secret set DATABASE_URL
```
Expected: `✓ Set secret DATABASE_URL for AgustinLuconi/A_Cuanto_Esta`

- [ ] **Step 3: Generar y setear un `SECRET_KEY` dummy**

Los scripts de scraping no usan `SECRET_KEY` funcionalmente — `Settings` sólo lo exige porque es un campo requerido. No hace falta reutilizar el de producción.

Run:
```bash
openssl rand -hex 32 | gh secret set SECRET_KEY
```
Expected: `✓ Set secret SECRET_KEY for AgustinLuconi/A_Cuanto_Esta`

- [ ] **Step 4: Verificar que ambos secrets quedaron listados**

Run: `gh secret list`
Expected: salida con dos filas, `DATABASE_URL` y `SECRET_KEY`, cada una con una fecha de "Updated" reciente (los valores nunca se muestran, eso es esperado)

---

### Task 6: Push y validación end-to-end

**Files:** ninguno (validación, no código nuevo)

**Interfaces:**
- Consumes: los tres workflows (Tasks 2-4), la composite action (Task 1) y los secrets (Task 5), todos ya committeados/configurados
- Produces: confirmación de que los tres workflows corren correctamente contra Supabase en producción

- [ ] **Step 1: Push de los commits de las Tasks 1-4**

```bash
git push origin main
```
Expected: push exitoso, sin conflictos (los commits de Tasks 1-4 quedaron locales hasta este punto)

- [ ] **Step 2: Disparar `scrape-daily.yml` manualmente y esperar el resultado**

```bash
gh workflow run scrape-daily.yml
sleep 10
gh run watch $(gh run list --workflow=scrape-daily.yml --limit 1 --json databaseId --jq '.[0].databaseId')
```
Expected: el comando `gh run watch` sigue el run en vivo y termina imprimiendo `✓ Run ... completed with 'success'` (o, si algún supermercado individual falló pero el resto corrió, revisar el log de ese step puntual — no bloquea el resto según el diseño)

- [ ] **Step 3: Confirmar en Supabase que `price_history` sumó filas nuevas**

Run:
```bash
cd backend
SUPABASE_URL=$(grep '^DATABASE_URL=' .env | cut -d '=' -f2-)
psql "$SUPABASE_URL" -c "SELECT count(*) FROM price_history;"
```
Expected: un número mayor a 5472 (el conteo de referencia post-migración de datos)

- [ ] **Step 4: Disparar `dollar-6h.yml` y `inflation-daily.yml` manualmente**

```bash
gh workflow run dollar-6h.yml
gh workflow run inflation-daily.yml
sleep 10
gh run list --limit 4
```
Expected: ambos runs aparecen en la lista con status `completed` / conclusion `success`

- [ ] **Step 5: Confirmar en Supabase que `economic_indicators` sumó filas (si había datos nuevos disponibles)**

Run:
```bash
psql "$SUPABASE_URL" -c "SELECT count(*) FROM economic_indicators;"
```
Expected: un número mayor o igual a 17109 (puede ser igual si no había cotizaciones/índices nuevos publicados desde la migración inicial — no es una falla)

- [ ] **Step 6: Confirmar que el step de resumen de `scrape-daily.yml` efectivamente falla el job ante un error real**

Esto es una prueba manual puntual, no queda como parte del código: renombrar temporalmente (en un branch descartable, sin pushear) el step `Coto` a un comando roto (ej. `run: python scripts/no_existe.py`), correr `gh workflow run` apuntando a ese branch con `--ref <branch>`, confirmar que el job termina en rojo por el step "Verificar resultados", y después descartar el branch sin mergear.

---

## Notas para quien ejecute el plan

- Los cron de GitHub Actions corren en UTC. `0 6 * * *` es ~03:00 ART, `0 7 * * *` es ~04:00 ART (offset intencional para no competir con el workflow de scrapers por el mismo minuto de arranque de runners).
- Si el repo queda 60 días sin commits, GitHub deshabilita automáticamente los workflows `schedule` — hay que reactivarlos a mano desde la pestaña Actions si eso pasa.
- No se toca `CLAUDE.md` en este plan. Si se quiere, como tarea aparte, actualizar la sección "Automatización (Fase 5)" del roadmap para reflejar que se usó GitHub Actions en vez de Celery + Redis.
