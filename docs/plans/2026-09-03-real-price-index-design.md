# Design Specification: Índice de precios propio y variación por categoría

**Date**: 2026-09-03
**Project**: A Cuánto Está? (`AgustinLuconi/A_Cuanto_Esta`)
**Status**: Approved

---

## 1. Overview & Goals

Reemplaza dos piezas de UI hoy hardcodeadas por cálculos reales sobre `price_history`:

1. **"Variación semanal" / "Índice A Cuanto Está"** en el home (`app/page.tsx`) — hoy es el literal `+0,8%`.
2. **Variación por categoría** en el dashboard de Economía (`app/economia/page.tsx`) — hoy es `CATEGORIES_VARIATION`, 12 categorías con porcentajes fijos, comparadas contra el IPC.

Cobertura geográfica (el tercer dato hardcodeado identificado en la auditoría del 2026-08-29) queda explícitamente fuera de este trabajo — depende de datos geográficos que hoy solo existen para Cuyo, y necesita su propia decisión de diseño.

---

## 2. Metodología del cálculo

Para una ventana de `N` días:

1. **Canasta**: solo productos con precio registrado en al menos el 70% de los días de la ventana (`≥5` de 7 días para la ventana semanal, `≥21` de 30 días para la mensual). Excluye productos recién agregados o con scrapeos intermitentes que meterían ruido en el promedio.
2. **Variación por producto**: `(último_precio - primer_precio) / primer_precio`, tomando el primer y el último precio registrado *dentro* de la ventana (no exige que caigan exactamente en el primer/último día calendario, tolera huecos).
3. **Agregación**: promedio simple (no ponderado) de las variaciones porcentuales de todos los productos de la canasta. Cada producto pesa igual, sin importar su categoría o precio.
4. Sin tabla materializada ni caché nuevo — se calcula al vuelo con una query SQL por request. El volumen actual (~186k filas en `price_history`) no lo justifica todavía; si más adelante se vuelve costoso, es una optimización aislada sin tocar esta lógica.

Ventanas: **7 días** para la variación del home, **30 días** para la variación por categoría (consistente con la comparación contra el IPC mensual que ya existe en `/analysis/price-vs-inflation`).

---

## 3. Backend — dos endpoints nuevos en `backend/app/api/v1/endpoints/analysis.py`

### `GET /api/v1/analysis/price-index?days=7`
Respuesta:
```json
{ "avg_change_pct": 0.021, "basket_size": 187, "period_days": 7 }
```
- `avg_change_pct`: fracción (0.021 = 2,1%), no porcentaje ya multiplicado — consistente con cómo el resto de la API devuelve variaciones (`inflation_monthly`, etc.), y con cómo el frontend ya normaliza (`fmtPct` multiplica x100).
- `basket_size`: cantidad de productos que entraron en el cálculo, para mostrar transparencia ("canasta de N productos") en vez del `totalCount` sin filtrar que se muestra hoy.
- Si la canasta resulta vacía (sin productos con suficiente continuidad en la ventana), devuelve `avg_change_pct: null, basket_size: 0` — el frontend debe manejar ese caso mostrando el estado vacío que ya usa para otros indicadores (`—`).

### `GET /api/v1/analysis/category-variation?days=30`
Respuesta:
```json
{ "lacteos": 0.041, "limpieza": 0.032, "...": "..." }
```
Un valor por cada una de las 17 `ProductCategory` reales del catálogo (no las 12 inventadas de `CATEGORIES_VARIATION` hoy). Categorías sin canasta suficiente en la ventana quedan ausentes del diccionario — el frontend las omite en vez de mostrar `0%` (que sería engañoso, no es que no varió, es que no hay datos suficientes).

Ambos endpoints reciben `days` como query param con un default (7 y 30 respectivamente) para poder ajustarlo sin desplegar cambios de frontend.

---

## 4. Frontend

### `app/page.tsx`
La card "Variación semanal" (dentro de `EcoMiniCard`) pasa a consumir `getPriceIndex()` (nueva función en `lib/api.ts`). El `deltaLabel` usa `basket_size` real en vez de `totalCount` (el conteo total del catálogo, que hoy se usa ahí de forma incorrecta — no refleja cuántos productos entraron en el cálculo).

### `app/economia/page.tsx`
`CATEGORIES_VARIATION` (el array hardcodeado) se elimina. El componente que ya renderiza la lista de categorías con la línea de referencia del IPC pasa a leer de `getCategoryVariation()`, mapeando cada `ProductCategory` real a su nombre de UI (reutilizando `BACKEND_TO_DESIGN`/`CATEGORIES_DESIGN` de `lib/categoryMap.ts`, ya usado en el resto de la app).

Ambos usan `isError` real (mismo patrón agregado para el bug de "Cargando indicadores" del 2026-08-29) en vez de solo chequear truthiness del dato.

---

## 5. Testing

- **Backend**: tests unitarios para la función de cálculo (mockeando `Session`, sin pegarle a Neon): canasta vacía, un producto por debajo del umbral de continuidad excluido, cálculo de variación correcto con datos armados a mano, promedio simple verificado con 2-3 productos de variaciones conocidas.
- **Verificación manual**: levantar backend+frontend, confirmar que ambas páginas muestran números reales (no `+0,8%` ni los 12 valores fijos), y que el `basket_size`/conteo de categorías tiene sentido contra los ~5.240 productos con historial suficiente identificados en la auditoría.
