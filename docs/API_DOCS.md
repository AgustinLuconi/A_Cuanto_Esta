# API Reference

Base URL: `http://localhost:8000/api/v1`

Documentacion interactiva: `http://localhost:8000/docs` (Swagger UI)

---

## Products

### GET /products

Listar productos con paginacion y filtros.

| Parametro | Tipo | Default | Descripcion |
|---|---|---|---|
| skip | int | 0 | Offset para paginacion |
| limit | int | 50 | Max resultados (1-200) |
| category | string | null | Filtrar por categoria (lacteos, bebidas, etc.) |
| search | string | null | Buscar por nombre |

### GET /products/search

Busqueda avanzada con filtros de precio.

| Parametro | Tipo | Default | Descripcion |
|---|---|---|---|
| q | string | **requerido** | Texto a buscar |
| category | string | null | Filtrar por categoria |
| brand | string | null | Filtrar por marca |
| min_price | float | null | Precio minimo |
| max_price | float | null | Precio maximo |
| skip | int | 0 | Offset |
| limit | int | 50 | Max resultados (1-200) |

### GET /products/{product_id}

Detalle de un producto con precios actuales en todos los supermercados.

Incluye `current_prices` (precio mas reciente por supermercado), `lowest_price`, `highest_price` y `price_difference`.

---

## Prices

### GET /products/{product_id}/prices/history

Historial de precios de un producto.

| Parametro | Tipo | Default | Descripcion |
|---|---|---|---|
| supermarket | string | null | Filtrar por supermercado |
| days | int | 30 | Ultimos N dias (0 = sin limite) |

### GET /prices/compare

Comparar precio actual entre supermercados.

| Parametro | Tipo | Default | Descripcion |
|---|---|---|---|
| product_id | UUID | **requerido** | ID del producto |

Respuesta incluye: `prices` por supermercado, `lowest_price`, `highest_price`, `price_difference_percentage`, `best_deal`.

### GET /prices/current

Snapshot de precios actuales (registro mas reciente por producto y supermercado).

| Parametro | Tipo | Default | Descripcion |
|---|---|---|---|
| supermarket | string | null | Filtrar por supermercado |
| category | string | null | Filtrar por categoria |
| skip | int | 0 | Offset |
| limit | int | 100 | Max resultados (1-500) |

---

## Economic

### GET /economic/context

Contexto macroeconomico actual. Devuelve el valor mas reciente de:
- Inflacion mensual y anual
- Dolar blue y oficial
- Indice UVA
- Tasa plazo fijo
- Riesgo pais

### GET /economic/inflation/history

Historial de inflacion.

| Parametro | Tipo | Default | Descripcion |
|---|---|---|---|
| months | int | 12 | Ultimos N meses (1-120) |
| type | string | "monthly" | "monthly" o "yearly" |

---

## Analysis

### GET /analysis/price-vs-inflation

Compara la variacion de precio de un producto contra la inflacion acumulada en el mismo periodo.

| Parametro | Tipo | Default | Descripcion |
|---|---|---|---|
| product_id | UUID | **requerido** | ID del producto |
| supermarket | string | **requerido** | Supermercado |
| days | int | 30 | Periodo en dias (1-365) |

Respuesta incluye: `price_change_percent`, `inflation_period_percent`, `comparison` (above/below/equal), `analysis_text`.

---

## Locations

### GET /locations/regions

Lista las 7 regiones de Argentina con sus provincias.

```json
{
  "regions": [
    {
      "code": "cuyo",
      "name": "Cuyo",
      "provinces": [
        {"code": "mendoza", "name": "Mendoza"},
        {"code": "san_juan", "name": "San Juan"},
        {"code": "san_luis", "name": "San Luis"}
      ]
    }
  ]
}
```

### GET /locations/provinces

Lista las 24 provincias con su region primaria.

### GET /locations/coverage

Muestra que regiones y provincias tienen datos de precios en la BD.

```json
{
  "regions_with_data": [{"code": "cuyo", "name": "Cuyo"}],
  "provinces_with_data": [{"code": "mendoza", "name": "Mendoza"}],
  "supermarkets_by_region": {"cuyo": ["atomo"]},
  "stats": {
    "total_records": 5078,
    "records_with_location": 573,
    "coverage_percentage": 11.28
  }
}
```

### GET /locations/prices/by-location

Precios de un producto filtrados por ubicacion.

| Parametro | Tipo | Default | Descripcion |
|---|---|---|---|
| product_id | UUID | **requerido** | ID del producto |
| region | string | null | Filtrar por region (ej: cuyo) |
| province | string | null | Filtrar por provincia (ej: mendoza) |
| supermarket | string | null | Filtrar por supermercado |
| limit | int | 50 | Max resultados (1-100) |

---

## Valores de enums

**Supermarket:** `carrefour`, `coto`, `disco`, `atomo`, `vea`, `jumbo`, `dia`, `la_anonima`, `chango_mas`

**ProductCategory:** `lacteos`, `bebidas`, `alimentos`, `limpieza`, `higiene`, `carnes`, `frutas_verduras`, `panaderia`, `congelados`, `mascotas`, `bebes`, `otros`

**Region:** `amba`, `pampeana`, `cuyo`, `noa`, `nea`, `patagonia`, `centro`
