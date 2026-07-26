# Página de detalle de producto

## Contexto

`src/app/producto/[id]/page.tsx` es un stub placeholder ("Detalle de
producto — próximamente") que nunca se terminó. El backend ya tiene todo
lo necesario:

- `GET /api/v1/products/{id}` → `ProductWithPrices` (ya usado en
  `ResultadosContent.tsx`): precios actuales por supermercado, precio más
  bajo/más alto, diferencia
- `GET /api/v1/products/{product_id}/prices/history` → lista plana de
  registros de precio (todas las casas mezcladas, timestamps propios de
  cada scrapeo), filtrable por `days` y `supermarket`
- `GET /api/v1/economic/inflation/history` → ya usado en `economia/page.tsx`

El frontend tiene un componente `MultiLineChart` en
`components.tsx` construido explícitamente para esto (comentario "price
history, used in product detail") pero **nunca se usó en ningún lado**
— mismo patrón que `EconomicSidebar.tsx`: código construido de antemano
para una pantalla que no se llegó a hacer.

## Decisiones

- **Ventana temporal**: últimos 90 días por defecto, sin selector en esta
  primera versión (YAGNI — se puede agregar después si hace falta)
- **Overlay de inflación**: sí se incluye, usando el mecanismo que ya
  soporta `MultiLineChart` (`inflation` prop, se multiplica contra el
  precio mediano inicial)
- **No se llama a `/prices/compare`**: sería redundante con
  `current_prices` que ya trae `GET /products/{id}`

## Estructura de la página

1. **Header**: imagen (o `ImagePlaceholder`), marca, `full_name`,
   categoría — de `getProduct(id)`
2. **Precios por supermercado**: cards ordenadas de menor a mayor precio,
   a partir de `current_prices`. Badge "más barato" en la primera (acá
   sí es siempre cierto, porque se ordena explícitamente por precio en
   el frontend antes de renderizar — no depende de un sort externo).
   Badge "en oferta" si `was_on_sale`, "sin stock" si `!in_stock`. Link
   "Ver en {supermercado}" hacia `url` si existe
3. **Banner de diferencia**: usa `lowest_price` / `highest_price` /
   `price_difference` (ya vienen en la respuesta, no hay que calcular
   nada)
4. **Gráfico histórico** (`MultiLineChart`): una línea por supermercado
   + overlay de inflación, últimos 90 días
5. **Estado vacío de historial**: si `/prices/history` devuelve 404, se
   muestra igual el resto de la página (header + precios actuales) sin
   el gráfico, con el mensaje "Todavía no hay suficiente historial"

## Armado de datos para el gráfico

### Problema
`MultiLineChart` espera `labels: string[]` (eje X compartido) y
`series: Record<string, number[]>` donde **cada array debe tener
exactamente el mismo largo que `labels`**. La respuesta de
`/prices/history` es una lista plana con timestamps propios de cada
supermercado — no vienen alineados.

### Solución
1. Agrupar los registros por supermercado
2. Tomar la **unión de fechas** (día calendario, no timestamp exacto) de
   scrapeo de todos los supermercados presentes → eje X (`labels`),
   ordenado ascendente
3. Para cada supermercado y cada fecha del eje X: si hubo un scrapeo ese
   día, usar ese precio; si no, usar el **último precio conocido**
   anterior (forward-fill). Si un supermercado no tiene ningún dato
   hasta cierta fecha (su primer scrapeo es posterior), se omite de
   `smIds` hasta que aparezca — no se inventa un precio hacia atrás
4. Si después de esto un supermercado termina con un array de un solo
   valor constante (nunca cambió de precio en la ventana), igual se
   grafica como línea plana — es información real

### Overlay de inflación
La inflación es mensual, el eje del gráfico es más granular (por día de
scrapeo). Se calcula un **factor acumulado en escalón por mes**:
- Se pide `getInflationHistory` con suficientes meses para cubrir la
  ventana (90 días → pedir 4 meses de margen)
- Para cada mes, factor acumulado = producto compuesto de `(1 + valor/100)`
  de todos los meses desde el inicio de la ventana hasta ese mes
  (inclusive)
- Cada fecha del eje X toma el factor de **su mes** (function escalón,
  no interpolación diaria — sería inventar precisión que no existe en el
  dato de origen)
- El primer valor de la serie de inflación se normaliza a `1.0` (mismo
  criterio que usa `MultiLineChart`, que multiplica contra el precio
  mediano inicial)

## Frontend — archivos

### `src/types/index.ts`
Nuevos tipos: `PriceHistoryRecord` (shape de cada item de
`/prices/history`: `supermarket`, `price`, `scraped_at`, `was_on_sale`,
`in_stock`, `url`, etc.)

### `src/lib/api.ts`
Nueva función `getPriceHistory(productId: string, days = 90):
Promise<PriceHistoryRecord[]>` — hace `GET
/products/{id}/prices/history?days=90`. Si el backend responde 404
(sin historial), devuelve `[]` en vez de propagar el error (mismo
patrón defensivo que otros clientes de este proyecto).

### `src/app/producto/[id]/page.tsx`
Reemplaza el stub completo. Usa `getProduct`, `getPriceHistory`,
`getInflationHistory` (ya existe) vía `useQuery`. Contiene la lógica de
armado de `labels`/`series`/`inflation` descrita arriba antes de pasarle
los datos a `MultiLineChart`.

## Manejo de errores

- Producto inexistente: `getProduct` ya lanza vía el backend (404) —
  mostrar página de "producto no encontrado" con link a `/resultados`
- Sin historial de precios: no es un error, es un estado válido (ver
  arriba)
- Sin `current_prices` (no debería pasar si el producto existe, pero por
  las dudas): mostrar el header igual, sin la sección de precios

## Testing / validación

- Verificar contra un producto real de Supabase que tenga historial en
  varios supermercados (ya sabemos por Task 4 que hay datos reales
  cargados)
- Verificar visualmente con Playwright que las líneas del gráfico no
  tengan longitudes desalineadas (causa típica de bugs silenciosos en
  este tipo de gráficos: una serie más corta que `labels` corre los
  puntos)
- Probar un producto sin historial para confirmar que el estado vacío
  se ve bien y no rompe el resto de la página
- `tsc --noEmit` sin errores

## Fuera de alcance

- Selector de ventana temporal (30/90/todo) — queda fijo en 90 días
- Filtro de supermercado en el gráfico (mostrar/ocultar líneas)
- `/prices/compare` no se usa (redundante con `/products/{id}`)
