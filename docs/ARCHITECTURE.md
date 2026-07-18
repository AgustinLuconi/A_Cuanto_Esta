# Architecture

## Flujo de datos

```
Supermercados (9)                  APIs economicas
  │                                  │
  ├─ VTEX (6): Carrefour,           ├─ ArgentinaDatos API
  │   Vea, Disco, Jumbo,            ├─ DolarAPI
  │   Dia, Chango Mas               └─ Datos.gob.ar
  ├─ Constructor.io: Coto                │
  ├─ PrestaShop AJAX: Atomo              │
  └─ API propia: La Anonima             │
        │                                │
        ▼                                ▼
   Scrapers (JSON)              economic_data service
        │                                │
        ▼                                ▼
    Normalizacion               ┌────────────────┐
    (nombre, categoria,         │  PostgreSQL     │
     barcode matching)          │  ─────────────  │
        │                       │  products       │
        └────────────────────►  │  price_history  │
                                │  economic_ind.  │
                                └────────┬───────┘
                                         │
                                         ▼
                                   FastAPI REST
                                   (13 endpoints)
                                         │
                                         ▼
                                   React Frontend
                                   (pendiente)
```

## Scrapers

### Jerarquia de clases

```
BaseScraper (ABC)
│   _get()          → HTTP GET con retry/backoff para 429
│   delay           → 2s default entre requests
│   max_retries     → 3 reintentos con backoff exponencial (5s, 10s, 20s)
│   default_province/region/city → ubicacion geografica
│
├── CarrefourScraper (VTEX)
│   │   search()        → /api/catalog_system/pub/products/search
│   │   parse_product() → items[0].sellers[0].commertialOffer
│   │   _save_product() → barcode matching + PriceHistory
│   │
│   ├── VeaScraper          (solo cambia URLs y enum)
│   ├── DiscoScraper        (solo cambia URLs y enum)
│   ├── JumboScraper        (solo cambia URLs y enum)
│   ├── DiaScraper          (solo cambia URLs y enum)
│   └── ChangoMasScraper    (solo cambia URLs y enum, delay=4s)
│
├── CotoScraper (Constructor.io)
│   │   search()        → /search/{query} via cnstrc.com
│   │   parse_product() → data.sku_display_name, product_list_price
│   │   _save_product() → barcode matching + PriceHistory
│
├── AtomoScraper (PrestaShop)
│   │   search()        → /index.php?controller=search&ajax=true
│   │   parse_product() → price_amount, regular_price_amount
│   │   _save_product() → barcode matching + PriceHistory
│   │   default_province = "mendoza", default_region = "cuyo"
│
└── LaAnonimaScraper (API propia)
        search()        → /catalogo/buscador/{termino}?pagina=N
        parse_product() → precioMostrar, codAnonima
        _save_product() → barcode = "la_anonima_{cod}" (sin EAN)
```

### Patron Template Method

`CarrefourScraper` implementa toda la logica de scraping VTEX: busqueda, parsing, paginacion, guardado en BD. Las subclases (Vea, Disco, Jumbo, Dia, Chango Mas) solo sobreescriben `__init__` cambiando 4 atributos: `name`, `search_url`, `store_url`, `supermarket_enum`.

### Rate Limiting

`BaseScraper._get()` implementa retry con backoff exponencial para HTTP 429:
- Intento 1: espera 5s
- Intento 2: espera 10s
- Intento 3: falla y retorna None

Chango Mas (MasOnline) tiene delay de 4s entre requests (vs 2s default) por rate limits mas agresivos.

### Normalizacion

`app/scrapers/utils/normalizer.py` contiene:
- `normalize_product_name()` — lowercase, sin acentos, sin caracteres especiales
- `map_category()` — mapea categorias de cada supermercado al enum `ProductCategory`
- `map_unit()` — infiere unidad de medida desde formato/descripcion

### Deduplicacion

Productos se matchean por `barcode` (EAN/UPC). Si un scraper encuentra un barcode existente, reutiliza el `Product` y agrega un nuevo `PriceHistory`. Esto permite comparar el mismo producto entre supermercados.

La Anonima no expone EAN — usa IDs internos prefijados (`la_anonima_{codAnonima}`) para evitar colisiones. Estos productos no participan en comparacion cross-market.

## API

5 routers en `app/api/v1/endpoints/`:

| Router | Prefix | Endpoints | Descripcion |
|---|---|---|---|
| products | /products | 3 | Catalogo y busqueda |
| prices | /prices | 3 | Historial, comparacion, snapshot |
| economic | /economic | 2 | Contexto macro e inflacion |
| analysis | /analysis | 1 | Precio vs inflacion |
| locations | /locations | 4 | Regiones, provincias, cobertura |

## Sistema de ubicacion

Campos `province`, `region`, `city`, `store_id` en `price_history` (String, nullable).

Validacion via enums Python en `app/models/location.py` (Region, Province). Utils en `app/utils/location_utils.py` para mapeo inverso province→region.

Actualmente solo Atomo tiene ubicacion (Mendoza, Cuyo). Los supermercados nacionales guardan NULL — correcto semanticamente porque los precios online son nacionales.

## Base de datos

PostgreSQL con SQLAlchemy ORM. Migraciones con Alembic.

3 tablas: `products`, `price_history`, `economic_indicators`. Ver [DATABASE.md](DATABASE.md).

Indices compuestos optimizados para los queries mas comunes:
- Historial de precio por producto/supermercado/fecha
- Snapshot de precios actuales por supermercado
- Filtro por ubicacion geografica
