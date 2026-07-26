# Página de Detalle de Producto Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar el stub de `src/app/producto/[id]/page.tsx` ("próximamente") por la página real de detalle de producto: precios por supermercado, banner de diferencia, y gráfico histórico con overlay de inflación.

**Architecture:** El backend ya expone todo lo necesario (`GET /products/{id}`, `GET /products/{id}/prices/history`, `GET /economic/inflation/history`, ya usado). El trabajo es 100% frontend: nuevos tipos, un cliente API nuevo, un módulo de funciones puras que transforma la lista plana de `/prices/history` al formato `{labels, series}` que espera el componente `MultiLineChart` (ya existe, nunca usado), y la página que conecta todo.

**Tech Stack:** Next.js 14 (App Router), TypeScript, TanStack Query, componente `MultiLineChart` existente en `src/components/design/components.tsx`.

**Spec:** `docs/superpowers/specs/2026-07-26-pagina-detalle-producto-design.md`

## Global Constraints

- El frontend no tiene test runner instalado (sin Jest/Vitest). La verificación de la lógica pura (Task 3) se hace con `npx tsx` corriendo un script ad-hoc con datos de muestra — no hace falta instalar un framework de testing para esto.
- Verificación de tipos: `cd frontend && npx tsc --noEmit`.
- `npm run build` falla en este entorno local por el `?` en la ruta del proyecto (limitación conocida, no relacionada con este trabajo) — usar `npm run dev` (Turbopack) para verificación visual.
- Producto real para pruebas manuales: `7afb5f8a-843d-4d2b-898d-7a2699873db8` (Aceite Girasol Cocinero 900cc — tiene historial en 7 supermercados, 23 registros).

---

### Task 1: Tipo `PriceHistoryRecord`

**Files:**
- Modify: `frontend/src/types/index.ts`

**Interfaces:**
- Produces: `interface PriceHistoryRecord` (consumido por Task 2 y Task 3)

- [ ] **Step 1: Agregar el tipo**

En `frontend/src/types/index.ts`, agregar después de la interfaz `CurrentPrice`:

```typescript
export interface PriceHistoryRecord {
  id: string;
  product_id: string;
  supermarket: Supermarket;
  price: number;
  was_on_sale: boolean;
  original_price: number | null;
  discount_percentage: number | null;
  url: string | null;
  in_stock: boolean;
  scraped_at: string;
}
```

- [ ] **Step 2: Verificar tipos**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: agregar tipo PriceHistoryRecord"
```

---

### Task 2: `getPriceHistory()` en el cliente API

**Files:**
- Modify: `frontend/src/lib/api.ts`

**Interfaces:**
- Consumes: `PriceHistoryRecord` (Task 1)
- Produces: `getPriceHistory(productId: string, days?: number) -> Promise<PriceHistoryRecord[]>` (consumido por Task 4)

- [ ] **Step 1: Agregar la función**

En `frontend/src/lib/api.ts`, agregar después de `getProduct`:

```typescript
export async function getPriceHistory(
  productId: string,
  days = 90
): Promise<PriceHistoryRecord[]> {
  try {
    const { data } = await api.get<PriceHistoryRecord[]>(
      `/products/${productId}/prices/history?days=${days}`
    );
    return data;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      return [];
    }
    throw err;
  }
}
```

Agregar `PriceHistoryRecord` al import de tipos (la línea `import type { ... } from "@/types";` al principio del archivo).

- [ ] **Step 2: Verificar tipos**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores. Si `axios.isAxiosError` da error de tipos, confirmar que `axios` está importado como default import al principio del archivo (`import axios from "axios";` — ya está, se usa para crear la instancia `api`).

- [ ] **Step 3: Verificar contra la API real**

Con el backend corriendo (`cd backend && source venv/bin/activate && uvicorn app.main:app --reload`), en otra terminal:

```bash
curl -s "http://localhost:8000/api/v1/products/7afb5f8a-843d-4d2b-898d-7a2699873db8/prices/history?days=90" | python3 -m json.tool | head -20
```

Expected: lista JSON con registros de precio, cada uno con `supermarket`, `price`, `scraped_at`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: agregar getPriceHistory al cliente API"
```

---

### Task 3: Funciones puras para armar los datos del gráfico

**Files:**
- Create: `frontend/src/lib/priceHistoryChart.ts`

**Interfaces:**
- Consumes: `PriceHistoryRecord` (Task 1)
- Produces: `buildPriceChartData(records: PriceHistoryRecord[]) -> { labels: string[]; series: Record<string, number[]> }`, `buildInflationFactors(labels: string[], inflationMonthly: Array<{date: string; value: number}>) -> number[]` (ambas consumidas por Task 4)

**Nota de diseño (ajuste sobre el spec):** el spec dice "si un supermercado no tiene dato hasta cierta fecha, se omite hasta que aparezca". En la práctica `MultiLineChart` exige que **todas** las series tengan exactamente `labels.length` elementos — no soporta series parciales. La implementación de abajo resuelve esto con back-fill: los días anteriores al primer precio conocido de un supermercado se completan con ese primer precio (una línea plana hacia atrás), en vez de omitir el supermercado. Es la única forma de mantener el componente sin modificarlo y sin inventar una tendencia (el valor usado es siempre un precio real que existió).

- [ ] **Step 1: Implementar `buildPriceChartData`**

Crear `frontend/src/lib/priceHistoryChart.ts`:

```typescript
import type { PriceHistoryRecord } from "@/types";

export function buildPriceChartData(records: PriceHistoryRecord[]): {
  labels: string[];
  series: Record<string, number[]>;
} {
  // 1. Agrupar por supermercado -> día (YYYY-MM-DD) -> {price, scraped_at}
  //    Si hay más de un registro el mismo día, se queda con el de scraped_at más reciente.
  const bySuper = new Map<string, Map<string, { price: number; scrapedAt: string }>>();
  for (const r of records) {
    const day = r.scraped_at.slice(0, 10);
    if (!bySuper.has(r.supermarket)) bySuper.set(r.supermarket, new Map());
    const dayMap = bySuper.get(r.supermarket)!;
    const existing = dayMap.get(day);
    if (!existing || r.scraped_at > existing.scrapedAt) {
      dayMap.set(day, { price: r.price, scrapedAt: r.scraped_at });
    }
  }

  // 2. Unión de días de todos los supermercados, ordenados ascendente
  const allDays = new Set<string>();
  for (const dayMap of bySuper.values()) {
    for (const day of dayMap.keys()) allDays.add(day);
  }
  const labels = Array.from(allDays).sort();

  // 3. Serie alineada por supermercado: precio exacto si existe ese día,
  //    forward-fill del último conocido si no, back-fill con el primer
  //    precio conocido para los días anteriores al primer registro.
  const series: Record<string, number[]> = {};
  for (const [supermarket, dayMap] of bySuper.entries()) {
    const sortedDays = Array.from(dayMap.keys()).sort();
    const firstKnownPrice = dayMap.get(sortedDays[0])!.price;
    let lastKnown = firstKnownPrice;
    const values: number[] = [];
    for (const day of labels) {
      const entry = dayMap.get(day);
      if (entry) {
        lastKnown = entry.price;
        values.push(entry.price);
      } else {
        values.push(lastKnown);
      }
    }
    series[supermarket] = values;
  }

  return { labels, series };
}

export function buildInflationFactors(
  labels: string[],
  inflationMonthly: Array<{ date: string; value: number }>
): number[] {
  if (labels.length === 0) return [];

  // Factor acumulado compuesto por mes (YYYY-MM), caminando cronológicamente
  const sorted = [...inflationMonthly].sort((a, b) => a.date.localeCompare(b.date));
  const factorByMonth = new Map<string, number>();
  let cumulative = 1;
  for (const rec of sorted) {
    cumulative *= 1 + rec.value / 100;
    factorByMonth.set(rec.date.slice(0, 7), cumulative);
  }

  // Normalizar: el mes del primer label lee como 1.0
  const baseMonth = labels[0].slice(0, 7);
  const baseFactor = factorByMonth.get(baseMonth) ?? 1;

  return labels.map((day) => {
    const month = day.slice(0, 7);
    const factor = factorByMonth.get(month);
    return factor != null ? factor / baseFactor : 1;
  });
}
```

- [ ] **Step 2: Verificar con datos de muestra**

Crear un script temporal (no se commitea) en `frontend/verify_chart.ts`:

```typescript
import { buildPriceChartData, buildInflationFactors } from "./src/lib/priceHistoryChart";

const records = [
  { id: "1", product_id: "p", supermarket: "coto" as const, price: 100, was_on_sale: false, original_price: null, discount_percentage: null, url: null, in_stock: true, scraped_at: "2026-06-01T10:00:00" },
  { id: "2", product_id: "p", supermarket: "coto" as const, price: 110, was_on_sale: false, original_price: null, discount_percentage: null, url: null, in_stock: true, scraped_at: "2026-06-03T10:00:00" },
  { id: "3", product_id: "p", supermarket: "carrefour" as const, price: 95, was_on_sale: false, original_price: null, discount_percentage: null, url: null, in_stock: true, scraped_at: "2026-06-02T10:00:00" },
];

const { labels, series } = buildPriceChartData(records);
console.log("labels:", labels);
console.log("series:", series);
console.log("largos iguales?", Object.values(series).every(s => s.length === labels.length));

const inflation = buildInflationFactors(labels, [
  { date: "2026-06-30", value: 2.0 },
  { date: "2026-07-31", value: 1.5 },
]);
console.log("inflation:", inflation);
```

Run: `cd frontend && npx tsx verify_chart.ts`

Expected (verificar a mano contra este output):
```
labels: [ '2026-06-01', '2026-06-02', '2026-06-03' ]
series: {
  coto: [ 100, 100, 110 ],       // 06-01 exacto, 06-02 forward-fill (100), 06-03 exacto (110)
  carrefour: [ 95, 95, 95 ]      // 06-01 back-fill (su primer precio real, del 06-02), 06-02 exacto, 06-03 forward-fill
}
largos iguales? true
inflation: [ 1, 1, 1 ]           // las 3 fechas caen en junio, mismo mes que el primer label -> factor 1.0
```

- [ ] **Step 3: Borrar el script temporal**

```bash
rm frontend/verify_chart.ts
```

- [ ] **Step 4: Verificar tipos**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/priceHistoryChart.ts
git commit -m "feat: agregar buildPriceChartData y buildInflationFactors"
```

---

### Task 4: Página de detalle de producto

**Files:**
- Modify: `frontend/src/app/producto/[id]/page.tsx` (reemplaza el stub completo)

**Interfaces:**
- Consumes: `getProduct` (ya existe), `getPriceHistory` (Task 2), `getInflationHistory` (ya existe), `buildPriceChartData`/`buildInflationFactors` (Task 3), `MultiLineChart`/`Price`/`SMSwatch`/`ImagePlaceholder`/`Icon`/`fmtPrice` (ya existen en `@/components/design/components`)

- [ ] **Step 1: Reescribir la página completa**

Reemplazar todo el contenido de `frontend/src/app/producto/[id]/page.tsx`:

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getProduct, getPriceHistory, getInflationHistory } from "@/lib/api";
import { buildPriceChartData, buildInflationFactors } from "@/lib/priceHistoryChart";
import {
  Price, SMSwatch, ImagePlaceholder, Icon, MultiLineChart, fmtPrice,
} from "@/components/design/components";
import type { CurrentPrice } from "@/types";

export default function ProductoPage({ params }: { params: { id: string } }) {
  const { data: product, isLoading, isError } = useQuery({
    queryKey: ["product", params.id],
    queryFn: () => getProduct(params.id),
  });

  const { data: priceHistory = [] } = useQuery({
    queryKey: ["priceHistory", params.id],
    queryFn: () => getPriceHistory(params.id, 90),
    enabled: !!product,
  });

  const { data: inflationRaw = [] } = useQuery({
    queryKey: ["inflation4m"],
    queryFn: () => getInflationHistory(4, "monthly"),
    staleTime: 30 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="page" style={{ textAlign: "center", padding: "64px 0", color: "var(--fg-4)" }}>
        Cargando producto…
      </div>
    );
  }

  if (isError || !product) {
    return (
      <div className="page" style={{ textAlign: "center", padding: "64px 0" }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
        <p style={{ color: "var(--fg-3)", marginBottom: 12 }}>Producto no encontrado</p>
        <Link href="/resultados" style={{ fontSize: 13, color: "var(--primary)" }}>
          ← Volver a resultados
        </Link>
      </div>
    );
  }

  const sortedPrices = [...product.current_prices].sort((a, b) => a.price - b.price);
  const hasChart = priceHistory.length > 0;
  const { labels, series } = hasChart ? buildPriceChartData(priceHistory) : { labels: [], series: {} };
  const inflation = hasChart ? buildInflationFactors(labels, inflationRaw) : [];

  return (
    <div className="page">
      <div style={{ marginBottom: 20 }}>
        <Link href="/resultados" style={{ fontSize: 12, color: "var(--fg-3)" }}>← Volver a resultados</Link>
      </div>

      {/* HEADER */}
      <div style={{ display: "flex", gap: 24, marginBottom: 28 }}>
        {product.image_url
          ? <img src={product.image_url} alt={product.name} style={{ width: 140, height: 140, objectFit: "contain", borderRadius: 12, border: "1px solid var(--border)", flexShrink: 0 }} />
          : <ImagePlaceholder w={140} h={140} label={product.brand ?? product.name} />}
        <div>
          <div style={{ fontSize: 12, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>
            {product.brand}
          </div>
          <h1 style={{ fontSize: 26, marginBottom: 8 }}>{product.full_name}</h1>
          {product.barcode && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--fg-3)" }}>
              <Icon.barcode />
              <span className="mono">{product.barcode}</span>
            </div>
          )}
        </div>
      </div>

      {/* DIFERENCIA DE PRECIO */}
      {product.price_difference != null && product.price_difference > 0 && (
        <div className="card" style={{ padding: 16, marginBottom: 24, background: "var(--good-tint)", display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 24 }}>💡</span>
          <div>
            <strong>Podés ahorrar {fmtPrice(product.price_difference)}</strong>
            <span style={{ color: "var(--fg-3)" }}> eligiendo bien el supermercado</span>
          </div>
        </div>
      )}

      {/* PRECIOS POR SUPERMERCADO */}
      <h2 style={{ fontSize: 16, marginBottom: 12 }}>Precios por supermercado</h2>
      <div className="col" style={{ gap: 8, marginBottom: 32 }}>
        {sortedPrices.map((cp: CurrentPrice, i: number) => (
          <div key={cp.supermarket} className="card" style={{
            padding: 14, display: "flex", alignItems: "center", gap: 14,
            borderColor: i === 0 ? "oklch(0.85 0.07 150)" : undefined,
          }}>
            <SMSwatch sm={cp.supermarket} />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{cp.supermarket.replace("_", " ")}</div>
              <div style={{ display: "flex", gap: 6, marginTop: 2 }}>
                {i === 0 && <span className="badge cheapest" style={{ fontSize: 10.5 }}>⭐ Más barato</span>}
                {cp.was_on_sale && <span className="badge" style={{ fontSize: 10.5 }}>En oferta</span>}
                {!cp.in_stock && <span className="badge" style={{ fontSize: 10.5, color: "var(--fg-4)" }}>Sin stock</span>}
              </div>
            </div>
            <Price value={cp.price} size="lg" />
            {cp.url && (
              <a href={cp.url} target="_blank" rel="noopener noreferrer" className="btn secondary" style={{ fontSize: 12 }}>
                Ver <Icon.arrowR />
              </a>
            )}
          </div>
        ))}
      </div>

      {/* GRÁFICO HISTÓRICO */}
      <h2 style={{ fontSize: 16, marginBottom: 12 }}>Historial de precios</h2>
      <div className="card" style={{ padding: 22 }}>
        {hasChart ? (
          <MultiLineChart labels={labels} series={series} inflation={inflation} height={320} />
        ) : (
          <p style={{ color: "var(--fg-4)", fontSize: 13, textAlign: "center", padding: "32px 0" }}>
            Todavía no hay suficiente historial para este producto.
          </p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verificar tipos**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores

- [ ] **Step 3: Verificar visualmente con Playwright**

Con el backend (`uvicorn app.main:app --port 8000`) y el frontend (`npm run dev`) corriendo:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    page.goto("http://localhost:3000/producto/7afb5f8a-843d-4d2b-898d-7a2699873db8", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    body = page.inner_text("body")
    print("Contiene nombre del producto?", "ACEITE" in body.upper())
    print("Contiene 'Más barato'?", "Más barato" in body)
    print("Contiene 'Precios por supermercado'?", "Precios por supermercado" in body)
    page.screenshot(path="producto_detalle.png", full_page=True)
    browser.close()
```

Expected: los tres `print` en `True`, y en el screenshot: header con imagen/nombre, lista de precios ordenada de menor a mayor con el badge en el primero, y el gráfico (aunque en este entorno headless puntual el SVG puede salir en blanco por el problema conocido de `ResizeObserver` — ver nota en `docs/superpowers/plans/2026-07-26-riesgo-pais-y-dolares.md`; para confirmar el gráfico en sí, inspeccionar el DOM):

```python
    svg = page.locator("svg").last
    paths = svg.locator("path").count()
    print("cantidad de <path> en el SVG del gráfico (una por supermercado, +1 si hay overlay de inflación):", paths)
```

Expected: `paths` >= 7 (7 supermercados) para el producto de prueba, ya que ese producto tiene datos en las 7 casas.

- [ ] **Step 4: Probar el caso sin historial**

Buscar un producto sin `price_history` (o usar un UUID inexistente para el caso 404) y confirmar que la página muestra el mensaje de "producto no encontrado" o "todavía no hay suficiente historial" según corresponda, sin romper el resto del layout.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/producto/\[id\]/page.tsx
git commit -m "feat: implementar la página real de detalle de producto"
```

---

## Self-Review

**Cobertura del spec:**
- Header (imagen, marca, nombre, categoría) → Task 4 ✓ (categoría se omitió del layout final por espacio — no estaba en la lista de campos críticos del spec, se puede agregar como línea extra si hace falta, pero `brand` + `full_name` + `barcode` ya identifican el producto sin ambigüedad)
- Precios por supermercado ordenados, badges → Task 4 ✓
- Banner de diferencia → Task 4 ✓
- Gráfico con overlay de inflación, 90 días → Task 3 + Task 4 ✓
- Unión de fechas + forward-fill → Task 3 ✓ (con el ajuste de back-fill documentado)
- Estado vacío sin historial → Task 4 ✓
- Producto no encontrado → Task 4 ✓
