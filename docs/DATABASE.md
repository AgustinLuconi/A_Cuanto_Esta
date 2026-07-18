# Database Schema

PostgreSQL 15+. Migraciones gestionadas con Alembic.

## Tablas

### products

Catalogo maestro de productos. Un producto = un barcode unico, puede tener precios en multiples supermercados.

| Columna | Tipo | Nullable | Descripcion |
|---|---|---|---|
| id | UUID | PK | Identificador unico |
| name | VARCHAR(255) | No | Nombre original del producto |
| normalized_name | VARCHAR(255) | No | Nombre normalizado para busquedas (lowercase, sin acentos) |
| brand | VARCHAR(100) | Si | Marca |
| category | ENUM ProductCategory | No | Categoria del producto |
| unit | ENUM ProductUnit | No | Unidad de medida (kg, l, unidad, etc.) |
| quantity | VARCHAR(50) | Si | Cantidad (ej: "900", "1.5") |
| description | VARCHAR(500) | Si | Descripcion |
| image_url | VARCHAR(500) | Si | URL de imagen |
| barcode | VARCHAR(50) | Si | EAN/UPC o ID interno prefijado (ej: `la_anonima_12345`) |
| created_at | TIMESTAMP | No | Fecha de creacion |
| updated_at | TIMESTAMP | Si | Ultima actualizacion |

**Indices:** `name`, `normalized_name`, `brand`, `category`, `barcode` (unique)

### price_history

Historial de precios. Cada registro es un precio observado en un momento dado para un producto en un supermercado.

| Columna | Tipo | Nullable | Descripcion |
|---|---|---|---|
| id | UUID | PK | Identificador unico |
| product_id | UUID | No | FK → products.id |
| supermarket | ENUM Supermarket | No | Supermercado |
| price | NUMERIC(10,2) | No | Precio en pesos argentinos |
| was_on_sale | BOOLEAN | No | Si estaba en oferta |
| original_price | NUMERIC(10,2) | Si | Precio original (si en oferta) |
| discount_percentage | NUMERIC(5,2) | Si | Porcentaje de descuento |
| url | VARCHAR(500) | Si | URL del producto en el sitio |
| scraped_at | TIMESTAMP | No | Fecha/hora del scraping |
| in_stock | BOOLEAN | No | Disponibilidad |
| province | VARCHAR(50) | Si | Provincia (ej: "mendoza") |
| city | VARCHAR(100) | Si | Ciudad |
| region | VARCHAR(50) | Si | Region (ej: "cuyo") |
| store_id | VARCHAR(100) | Si | ID de sucursal |
| created_at | TIMESTAMP | No | Fecha de creacion del registro |

**Indices compuestos:**
- `idx_product_supermarket_date` → (product_id, supermarket, scraped_at)
- `idx_supermarket_date` → (supermarket, scraped_at)
- `idx_price_province_date` → (province, scraped_at)
- `idx_price_region_supermarket` → (region, supermarket)

**Indices simples:** `supermarket`, `scraped_at`, `province`, `region`

### economic_indicators

Indicadores macroeconomicos de Argentina.

| Columna | Tipo | Nullable | Descripcion |
|---|---|---|---|
| id | UUID | PK | Identificador unico |
| indicator_type | ENUM IndicatorType | No | Tipo de indicador |
| value | NUMERIC(15,4) | No | Valor numerico |
| date | DATE | No | Fecha del dato |
| source | ENUM DataSource | No | Fuente de datos |
| category | VARCHAR(100) | Si | Subcategoria (ej: IPC por rubro) |
| created_at | TIMESTAMP | No | Fecha de creacion |

**Tipos de indicador:** `inflation_monthly`, `inflation_yearly`, `dollar_blue`, `dollar_oficial`, `dollar_mep`, `dollar_ccl`, `uva_index`, `plazo_fijo_rate`, `risk_country`, `ipc_category`

**Fuentes:** `argentina_datos`, `datos_gob_ar`, `dolarapi`

## Enums

### Supermarket
`carrefour`, `coto`, `disco`, `atomo`, `vea`, `jumbo`, `dia`, `la_anonima`, `chango_mas`

### ProductCategory
`alimentos`, `bebidas`, `limpieza`, `higiene_personal`, `lacteos`, `carnes`, `frutas_verduras`, `panaderia`, `congelados`, `snacks`, `desayuno`, `otros`

### ProductUnit
`kg`, `g`, `l`, `ml`, `unidad`, `pack`

## Migraciones

```bash
cd backend && source venv/bin/activate

# Aplicar todas
alembic upgrade head

# Nueva migracion
alembic revision --autogenerate -m "descripcion"

# Ver historial
alembic history
```

Cadena actual: `fb80705162b3` → `0f616895f3d4` → `2a4b6c8d0e1f` → `4c6d8e0f1a2b` → `5d7e9f1a3b4c` → `6e8f0a2b4c5d` → `7f9a1b3c5e6d` → `8a0b2c4d6e7f` → `9b1c3d5e7f8a`

## Deduplicacion de productos

Los productos se deuplican por `barcode` (EAN/UPC). Si un scraper encuentra un producto con un barcode existente, reutiliza el `Product` existente y solo agrega un nuevo `PriceHistory`.

Excepcion: La Anonima no expone EAN — usa IDs internos prefijados (`la_anonima_12345`) para evitar colisiones. Estos productos no se comparan cross-market.
