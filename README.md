# A Cuanto Esta? - Comparador de Precios Argentina

Plataforma de comparación de precios en supermercados argentinos con historial de precios y contexto económico en tiempo real (inflación, dólar, UVA).

## Estado actual

- **9 supermercados** scrapeando via APIs JSON (sin headless browser)
- **3,295 productos** unicos en base de datos
- **5,078 registros** de precio con historial
- **15,725 indicadores** economicos (inflacion, dolar, UVA, riesgo pais)
- **13 endpoints** REST funcionando
- **24.5%** de productos comparables entre 2+ supermercados (matching por EAN/barcode)

## Supermercados soportados

| Supermercado | Plataforma | Productos | EAN real | Tipo |
|---|---|---|---|---|
| Carrefour | VTEX | 568 | Si | Nacional |
| Coto | Constructor.io | 692 | Si | Nacional |
| Disco | VTEX (Cencosud) | 549 | Si | Nacional |
| Vea | VTEX (Cencosud) | 549 | Si | Nacional |
| Jumbo | VTEX (Cencosud) | 572 | Si | Nacional |
| Dia | VTEX | 560 | Si | Nacional |
| Chango Mas | VTEX (GDN/ex-Walmart) | 547 | Si | Nacional |
| La Anonima | API propia | 266 | No (ID interno) | Nacional |
| Atomo | PrestaShop AJAX | 557 | Si | Regional (Mendoza) |

## Stack tecnologico

**Backend:** Python 3.14, FastAPI, SQLAlchemy, Alembic, PostgreSQL, requests

**Scraping:** APIs JSON publicas (VTEX, Constructor.io, PrestaShop, custom). No usa Selenium ni headless browser.

**Datos economicos:** ArgentinaDatos API, DolarAPI, Datos.gob.ar

## Instalacion

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con DATABASE_URL y SECRET_KEY

# Crear tablas
alembic upgrade head
```

## Cómo correr el proyecto localmente

Para desarrollar y ver la aplicación funcionando, necesitas correr ambos servidores (backend y frontend) en dos terminales separadas.

### 1. Iniciar el Backend (FastAPI)
Abre una terminal y ejecuta:
```bash
cd backend
source venv/bin/activate  # Activa el entorno virtual
uvicorn app.main:app --reload
```
El backend estará disponible en `http://localhost:8000`. Puedes ver la documentación de la API en `http://localhost:8000/docs`.

### 2. Iniciar el Frontend (Next.js/React)
Abre una **nueva** terminal y ejecuta:
```bash
cd frontend
npm install  # (Solo la primera vez si no instalaste las dependencias)
npm run dev
```
El frontend estará disponible en `http://localhost:3000`.

### Tareas adicionales (Scraping)
Si necesitas actualizar los datos de la base de datos (inflación, precios, etc.) de forma manual, puedes correr los scripts desde la carpeta `backend` con el entorno virtual activado:
```bash
python scripts/fetch_economic_data.py
```

## Estructura del proyecto

```
backend/
├── app/
│   ├── api/v1/endpoints/    # 5 routers: products, prices, economic, analysis, locations
│   ├── config/              # settings.py (Pydantic), database.py (SQLAlchemy)
│   ├── models/              # product, price_history, economic_indicator, location
│   ├── schemas/             # Pydantic schemas para request/response
│   ├── scrapers/            # 9 scrapers (base.py → carrefour → vea/disco/jumbo/dia/chango_mas, coto, atomo, la_anonima)
│   ├── services/            # Logica de negocio y clientes API economicos
│   └── utils/               # Normalizacion, location_utils
├── alembic/versions/        # 9 migraciones
├── scripts/                 # Scripts de test y populate por supermercado
└── tests/
```

## API REST

Base URL: `http://localhost:8000/api/v1`

| Metodo | Endpoint | Descripcion |
|---|---|---|
| GET | `/products` | Listar productos con paginacion y filtros |
| GET | `/products/search` | Busqueda avanzada con filtros de precio |
| GET | `/products/{id}` | Detalle con precios actuales por supermercado |
| GET | `/products/{id}/prices/history` | Historial de precios |
| GET | `/prices/compare` | Comparar precio entre supermercados |
| GET | `/prices/current` | Snapshot de precios actuales |
| GET | `/economic/context` | Contexto macroeconomico actual |
| GET | `/economic/inflation/history` | Historial de inflacion |
| GET | `/analysis/price-vs-inflation` | Comparar evolucion de precio vs inflacion |
| GET | `/locations/regions` | Listar regiones de Argentina |
| GET | `/locations/provinces` | Listar provincias |
| GET | `/locations/coverage` | Cobertura de datos por ubicacion |
| GET | `/locations/prices/by-location` | Precios filtrados por ubicacion |

Documentacion interactiva en `/docs` (Swagger UI) cuando el servidor esta corriendo.

Ver [docs/API_DOCS.md](docs/API_DOCS.md) para referencia completa.

## Arquitectura de scrapers

```
BaseScraper (base.py)
├── CarrefourScraper (VTEX)
│   ├── VeaScraper
│   ├── DiscoScraper
│   ├── JumboScraper
│   ├── DiaScraper
│   └── ChangoMasScraper
├── CotoScraper (Constructor.io)
├── AtomoScraper (PrestaShop)
└── LaAnonimaScraper (API propia)
```

Los scrapers VTEX heredan toda la logica de `CarrefourScraper` — cada subclase son ~24 lineas cambiando solo URLs y enum. `BaseScraper._get()` incluye retry con backoff exponencial para HTTP 429.

## Modelo de datos

3 tablas principales:
- **products** — Catalogo normalizado (un producto = un barcode, multiples supermercados)
- **price_history** — Historial de precios con ubicacion geografica (province, region, city)
- **economic_indicators** — Inflacion, dolar, UVA, riesgo pais, plazo fijo

Ver [docs/DATABASE.md](docs/DATABASE.md) para esquema completo.

## Roadmap

- [x] Fase 1: Modelos + primer scraper (Coto)
- [x] Fase 2: 9 supermercados + normalizacion + matching por barcode
- [x] Fase 3: API REST (13 endpoints) + sistema de regiones
- [ ] Fase 4: Frontend React
- [ ] Fase 5: Automatizacion con Celery
- [ ] Fase 6: Docker + Deploy

## Licencia

MIT
