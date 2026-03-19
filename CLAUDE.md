# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

**A Cuanto Está?** — Plataforma de comparación de precios en supermercados argentinos con contexto económico en tiempo real (inflación, dólar, UVA). Proyecto de aprendizaje orientado a web scraping, APIs y full-stack.

## Comandos de desarrollo

### Backend (FastAPI)
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Migraciones
alembic upgrade head           # Aplicar todas las migraciones
alembic revision --autogenerate -m "descripción"  # Nueva migración

# Servidor de desarrollo
uvicorn app.main:app --reload

# Tests
pytest                         # Todos los tests
pytest tests/test_foo.py       # Un solo archivo
pytest -k "test_nombre"        # Un solo test por nombre
```

### Frontend (React)
```bash
cd frontend
npm install
npm run dev      # Servidor desarrollo
npm run build    # Build producción
npm run lint     # Lint
```

## Arquitectura

### Flujo de datos
```
Supermercados (Carrefour, Coto, Disco)
    └── Scrapers (BeautifulSoup4 + Selenium)
            └── Normalización de datos
                    └── PostgreSQL (price_history, products)
                            └── FastAPI REST API
                                    └── React Frontend

APIs externas (ArgentinaDatos, Datos.gob.ar)
    └── services/economic_indicators.py
            └── economic_indicators table → API → Frontend
```

### Backend (`backend/app/`)
- **`api/`** — Routers FastAPI. Cada recurso tiene su propio router.
- **`models/`** — Modelos SQLAlchemy (ORM). Tablas: `products`, `price_history`, `economic_indicators`.
- **`schemas/`** — Schemas Pydantic para validación de request/response.
- **`scrapers/`** — Un scraper por supermercado. Producen datos normalizados con la misma estructura.
- **`services/`** — Lógica de negocio: comparación de precios, integración con APIs económicas, lógica de análisis.
- **`config/`** — Settings via Pydantic BaseSettings leyendo desde `.env`.
- **`utils/`** — Helpers reutilizables (normalización de nombres de productos, etc).

### Base de datos
Ver `docs/DATABASE.md` cuando exista. Las tablas principales son:
- `products` — Catálogo normalizado (un producto puede tener entradas en varios supermercados)
- `price_history` — Historial de precios con timestamp, supermercado y producto
- `economic_indicators` — Snapshot de indicadores macroeconómicos (inflación, tipos de cambio)

### Automatización (Fase 5)
Celery + Redis para scraping programado. Los workers de Celery ejecutan scrapers periódicamente y guardan en PostgreSQL.

## Variables de entorno

Copiar `backend/.env.example` → `backend/.env`. Incluirá al menos:
- `DATABASE_URL` — conexión PostgreSQL
- `REDIS_URL` — para Celery (cuando se implemente)
- Credenciales de APIs externas si requieren auth

## Notas del entorno

- `firebase-debug.log` en la raíz es generado por el Firebase MCP Server de Antigravity (IDE). No pertenece al proyecto — debe estar en `.gitignore`.

## Estado actual

🚧 Proyecto en scaffolding inicial. Solo existe estructura de directorios. No hay código implementado aún.

**Roadmap activo:**
1. Fase 1 (en progreso): Cliente ArgentinaDatos API + primer scraper funcional
2. Fase 2: Scrapers de los 3 supermercados + normalización
3. Fase 3: API REST completa con endpoints de búsqueda y comparación
4. Fase 4: Frontend React
5. Fase 5: Automatización con Celery
6. Fase 6: Docker + Deploy
