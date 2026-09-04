# Real Price Index & Category Variation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded "+0,8%" weekly index on the home page and the 12 fixed category-variation percentages on the economía dashboard with real numbers computed from `price_history`.

**Architecture:** A single backend helper (`_compute_price_changes`) fetches all `price_history` rows in a time window in one query, groups them by product in Python, and keeps only products with price data on at least 70% of the window's days (a continuity filter — excludes noisy, intermittently-scraped products). Two thin FastAPI endpoints sit on top of it: `/analysis/price-index` (unweighted average change across the whole basket) and `/analysis/category-variation` (same average, grouped by category). The frontend swaps two hardcoded constants for calls to these endpoints.

**Tech Stack:** FastAPI + SQLAlchemy (backend/app/api/v1/endpoints/analysis.py), Next.js + TanStack Query + Zod (frontend/src/app/page.tsx, frontend/src/app/economia/page.tsx, frontend/src/lib/api.ts, frontend/src/types/index.ts).

**Spec:** `docs/plans/2026-09-03-real-price-index-design.md`

## Global Constraints

- Continuity filter: a product must have price data on **≥70%** of the window's days to enter the basket (`math.ceil(days * 0.7)` distinct days).
- Aggregation: **simple unweighted average** of each product's % change — no category or price weighting.
- Windows: **7 days** for the home page index, **30 days** for category variation.
- `avg_change_pct` and category-variation values are **fractions** (0.021 = 2.1%), matching how the rest of the API already returns variations (`inflation_monthly`, etc.) — never pre-multiplied by 100.
- No new database table, no caching layer — compute on request. `price_history` volume today (~186k rows) doesn't justify it; this plan does not include a materialized-view optimization.
- Follow the file's existing convention: `datetime.utcnow()` (naive), matching every other function already in `analysis.py` — do not introduce yet another timezone convention in this file.

---

### Task 1: `_compute_price_changes` helper

**Files:**
- Modify: `backend/app/api/v1/endpoints/analysis.py`
- Test: `backend/tests/test_analysis.py`

**Interfaces:**
- Produces: `_compute_price_changes(db: Session, days: int) -> list[tuple[float, str]]` — a list of `(change_pct, category_value)`, one entry per **(product, supermarket) pair** that meets the continuity threshold. `change_pct` is a fraction. `category_value` is `ProductCategory.value` (e.g. `"lacteos"`). Grouping is by `(product_id, supermarket)`, not `product_id` alone — a product sold at two stores has two independent price trajectories, and averaging "first price at store A" against "last price at store B" would measure the price *difference between stores*, not a price *change over time*. Tasks 2 and 3 both call this function and consume its return type directly (they only ever iterate the list's values — no caller needs to look anything up by product id).

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_analysis.py`. New imports needed:
- Add `_compute_price_changes` to the existing `from app.api.v1.endpoints.analysis import ...` line.
- Add `timedelta` to the existing `from datetime import datetime` line, making it `from datetime import datetime, timedelta`.
- Add `ProductCategory` to the existing `from app.models.product import Product` line, making it `from app.models.product import Product, ProductCategory`.
- `Supermarket` is already imported in this file (`from app.models.price_history import PriceHistory, Supermarket`).

```python
# --- _compute_price_changes: canasta y cálculo de variación -------------


def _row(product_id, supermarket, price, days_ago, category):
    return (product_id, supermarket, price, datetime.utcnow() - timedelta(days=days_ago), category)


def test_compute_price_changes_excludes_pair_below_coverage_threshold():
    # Arrange: ventana de 10 días, umbral de continuidad = ceil(10*0.7) = 7 días.
    # Este (producto, super) solo tiene 2 días distintos de precio -> por debajo del umbral.
    pid = uuid4()
    rows = [
        _row(pid, Supermarket.COTO, 100, days_ago=9, category=ProductCategory.LACTEOS),
        _row(pid, Supermarket.COTO, 110, days_ago=1, category=ProductCategory.LACTEOS),
    ]
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = rows

    result = _compute_price_changes(db, days=10)

    assert result == []


def test_compute_price_changes_includes_pair_meeting_threshold():
    # Arrange: 7 días distintos de precio en una ventana de 10 días (umbral: 7) -> entra.
    # Precio sube de 100 a 110 -> +10%.
    pid = uuid4()
    rows = [_row(pid, Supermarket.COTO, 100, days_ago=9, category=ProductCategory.LACTEOS)]
    for d in range(6, 0, -1):
        rows.append(_row(pid, Supermarket.COTO, 100 + (9 - d), days_ago=d, category=ProductCategory.LACTEOS))
    rows.append(_row(pid, Supermarket.COTO, 110, days_ago=1, category=ProductCategory.LACTEOS))
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = rows

    result = _compute_price_changes(db, days=10)

    assert len(result) == 1
    change_pct, category_value = result[0]
    assert change_pct == pytest.approx(0.10)
    assert category_value == "lacteos"


def test_compute_price_changes_returns_empty_list_when_no_rows():
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = []

    result = _compute_price_changes(db, days=7)

    assert result == []


def test_compute_price_changes_skips_pair_with_zero_first_price():
    # (producto, super) con suficiente continuidad pero precio inicial 0 -> evita división por cero.
    pid = uuid4()
    rows = [
        _row(pid, Supermarket.COTO, 0, days_ago=d, category=ProductCategory.LACTEOS)
        for d in range(6, -1, -1)
    ]
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = rows

    result = _compute_price_changes(db, days=7)

    assert result == []


def test_compute_price_changes_treats_different_supermarkets_as_independent_series():
    # Mismo producto en 2 supermercados: Coto sube 100->110 (+10%, 7 días
    # continuos, entra), Carrefour tiene solo 1 día de datos (no entra). Si
    # el agrupamiento fuera por product_id solo (sin supermarket), esto se
    # mezclaría en una sola serie con el orden equivocado — cada
    # (producto, super) debe evaluarse de forma completamente independiente.
    pid = uuid4()
    rows = [_row(pid, Supermarket.COTO, 100, days_ago=9, category=ProductCategory.LACTEOS)]
    for d in range(6, 0, -1):
        rows.append(_row(pid, Supermarket.COTO, 100 + (9 - d), days_ago=d, category=ProductCategory.LACTEOS))
    rows.append(_row(pid, Supermarket.COTO, 110, days_ago=1, category=ProductCategory.LACTEOS))
    rows.append(_row(pid, Supermarket.CARREFOUR, 9999, days_ago=5, category=ProductCategory.LACTEOS))
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = rows

    result = _compute_price_changes(db, days=10)

    assert len(result) == 1
    change_pct, category_value = result[0]
    assert change_pct == pytest.approx(0.10)  # el 9999 de Carrefour nunca entra al cálculo
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && pytest tests/test_analysis.py -k compute_price_changes -v`
Expected: FAIL with `ImportError: cannot import name '_compute_price_changes'`

- [ ] **Step 3: Implement `_compute_price_changes`**

In `backend/app/api/v1/endpoints/analysis.py`, add `from collections import defaultdict` alongside the other stdlib imports at the top of the file (`Product` is already imported — `ProductCategory` itself is never referenced by name in this file, only `.category`/`.value` on already-typed ORM results, so no change needed to the `app.models.product` import here). Then add the function after `_build_analysis_text`:

```python
_MIN_COVERAGE_RATIO = 0.7


def _compute_price_changes(db: Session, days: int) -> list[tuple[float, str]]:
    """
    Para cada (producto, supermercado) con precio registrado en al menos el
    70% de los días de la ventana de `days` días, calcula su variación de
    precio (primer precio vs. último precio dentro de la ventana). Se
    agrupa por (producto, supermercado) y no solo por producto: un mismo
    producto vendido en dos supermercados tiene dos series de precio
    independientes, y mezclarlas mediría la diferencia de precio ENTRE
    negocios en vez de el cambio de precio EN EL TIEMPO. Pares con poca
    continuidad (recién agregados, scrapeados de forma intermitente) quedan
    afuera para no meter ruido en el promedio.

    Returns:
        Lista de (change_pct, category_value) — change_pct es una fracción
        (0.02 = 2%), no un porcentaje ya multiplicado por 100. Sin orden
        garantizado; los llamadores solo necesitan iterar los valores.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    min_days = math.ceil(days * _MIN_COVERAGE_RATIO)

    rows = (
        db.query(
            PriceHistory.product_id,
            PriceHistory.supermarket,
            PriceHistory.price,
            PriceHistory.scraped_at,
            Product.category,
        )
        .join(Product, Product.id == PriceHistory.product_id)
        .filter(PriceHistory.scraped_at >= cutoff)
        .order_by(PriceHistory.product_id, PriceHistory.supermarket, PriceHistory.scraped_at.asc())
        .all()
    )

    by_pair: dict[tuple[UUID, str], list[tuple[datetime, float, str]]] = defaultdict(list)
    for product_id, supermarket, price, scraped_at, category in rows:
        by_pair[(product_id, supermarket)].append((scraped_at, float(price), category.value))

    changes: list[tuple[float, str]] = []
    for points in by_pair.values():
        distinct_days = {ts.date() for ts, _, _ in points}
        if len(distinct_days) < min_days:
            continue
        first_price = points[0][1]
        last_price = points[-1][1]
        if first_price == 0:
            continue
        category_value = points[0][2]
        changes.append(((last_price - first_price) / first_price, category_value))

    return changes
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && pytest tests/test_analysis.py -k compute_price_changes -v`
Expected: 5 passed

- [ ] **Step 5: Run the full backend suite to confirm nothing else broke**

Run: `cd backend && source venv/bin/activate && pytest -q`
Expected: all tests pass (79 existing + 5 new = 84)

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/endpoints/analysis.py backend/tests/test_analysis.py
git commit -m "feat(backend): add _compute_price_changes helper for real price index"
```

---

### Task 2: `GET /analysis/price-index` endpoint

**Files:**
- Modify: `backend/app/api/v1/endpoints/analysis.py`
- Test: `backend/tests/test_analysis.py`

**Interfaces:**
- Consumes: `_compute_price_changes(db, days) -> list[tuple[float, str]]` (Task 1).
- Produces: `GET /api/v1/analysis/price-index?days=7` → `PriceIndexResponse { avg_change_pct: float | None, basket_size: int, period_days: int }`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_analysis.py` (needs `from unittest.mock import patch` added to the existing `unittest.mock` import, and `from app.api.v1.endpoints.analysis import price_index` added to the existing analysis import line):

```python
# --- price_index: endpoint ------------------------------------------------


def test_price_index_returns_none_and_zero_basket_when_no_products_qualify():
    db = MagicMock()
    with patch("app.api.v1.endpoints.analysis._compute_price_changes", return_value=[]):
        result = price_index(days=7, db=db)

    assert result.avg_change_pct is None
    assert result.basket_size == 0
    assert result.period_days == 7


def test_price_index_averages_changes_unweighted():
    # Arrange: dos pares (producto, super), +10% y +20% -> promedio simple = 15%.
    changes = [(0.10, "lacteos"), (0.20, "limpieza")]
    db = MagicMock()
    with patch("app.api.v1.endpoints.analysis._compute_price_changes", return_value=changes):
        result = price_index(days=7, db=db)

    assert result.avg_change_pct == pytest.approx(0.15)
    assert result.basket_size == 2
    assert result.period_days == 7
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && pytest tests/test_analysis.py -k test_price_index -v`
Expected: FAIL with `ImportError: cannot import name 'price_index'`

- [ ] **Step 3: Implement the endpoint**

In `backend/app/api/v1/endpoints/analysis.py`, add after `_compute_price_changes`:

```python
class PriceIndexResponse(BaseModel):
    avg_change_pct: float | None
    basket_size: int
    period_days: int


@router.get("/price-index", response_model=PriceIndexResponse)
def price_index(
    days: int = Query(7, ge=1, le=365, description="Ventana en días"),
    db: Session = Depends(get_db),
):
    """
    Variación de precio promedio (no ponderada) de la canasta de productos
    con historial continuo suficiente en la ventana. Reemplaza el "Índice A
    Cuanto Está" hardcodeado del home.
    """
    changes = _compute_price_changes(db, days)
    if not changes:
        return PriceIndexResponse(avg_change_pct=None, basket_size=0, period_days=days)
    avg = sum(change for change, _ in changes) / len(changes)
    return PriceIndexResponse(
        avg_change_pct=round(avg, 4), basket_size=len(changes), period_days=days
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && pytest tests/test_analysis.py -k test_price_index -v`
Expected: 2 passed

- [ ] **Step 5: Manual smoke test against the real backend**

```bash
cd backend && source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
sleep 3
curl -s "http://127.0.0.1:8000/api/v1/analysis/price-index?days=7" | python3 -m json.tool
kill %1
```
Expected: JSON with `avg_change_pct` (a small fraction, likely between -0.05 and 0.05), `basket_size` (a few hundred to low thousands), `period_days: 7`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/endpoints/analysis.py backend/tests/test_analysis.py
git commit -m "feat(backend): add GET /analysis/price-index endpoint"
```

---

### Task 3: `GET /analysis/category-variation` endpoint

**Files:**
- Modify: `backend/app/api/v1/endpoints/analysis.py`
- Test: `backend/tests/test_analysis.py`

**Interfaces:**
- Consumes: `_compute_price_changes(db, days) -> list[tuple[float, str]]` (Task 1).
- Produces: `GET /api/v1/analysis/category-variation?days=30` → `dict[str, float]`, keyed by `ProductCategory.value`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_analysis.py` (add `category_variation` to the existing analysis import line):

```python
# --- category_variation: endpoint -----------------------------------------


def test_category_variation_returns_empty_dict_when_no_products_qualify():
    db = MagicMock()
    with patch("app.api.v1.endpoints.analysis._compute_price_changes", return_value=[]):
        result = category_variation(days=30, db=db)

    assert result == {}


def test_category_variation_groups_and_averages_by_category():
    # lacteos: +10%, +20% -> promedio 15%. limpieza: +4% -> promedio 4%.
    changes = [
        (0.10, "lacteos"),
        (0.20, "lacteos"),
        (0.04, "limpieza"),
    ]
    db = MagicMock()
    with patch("app.api.v1.endpoints.analysis._compute_price_changes", return_value=changes):
        result = category_variation(days=30, db=db)

    assert result == {"lacteos": pytest.approx(0.15), "limpieza": pytest.approx(0.04)}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && pytest tests/test_analysis.py -k test_category_variation -v`
Expected: FAIL with `ImportError: cannot import name 'category_variation'`

- [ ] **Step 3: Implement the endpoint**

In `backend/app/api/v1/endpoints/analysis.py`, add after `price_index`:

```python
@router.get("/category-variation")
def category_variation(
    days: int = Query(30, ge=1, le=365, description="Ventana en días"),
    db: Session = Depends(get_db),
) -> dict[str, float]:
    """
    Variación de precio promedio por categoría, para productos con
    historial continuo suficiente en la ventana. Categorías sin canasta
    suficiente quedan ausentes del diccionario en vez de aparecer en 0%
    (que implicaría "no varió" en vez de "sin datos suficientes").
    Reemplaza CATEGORIES_VARIATION hardcodeado del dashboard de economía.
    """
    changes = _compute_price_changes(db, days)
    by_category: dict[str, list[float]] = defaultdict(list)
    for change, category_value in changes:
        by_category[category_value].append(change)
    return {
        category: round(sum(vals) / len(vals), 4)
        for category, vals in by_category.items()
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && pytest tests/test_analysis.py -k test_category_variation -v`
Expected: 2 passed

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && source venv/bin/activate && pytest -q`
Expected: all pass (86 existing + 2 new = 88)

- [ ] **Step 6: Manual smoke test**

```bash
cd backend && source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
sleep 3
curl -s "http://127.0.0.1:8000/api/v1/analysis/category-variation?days=30" | python3 -m json.tool
kill %1
```
Expected: JSON object with some subset of the 17 category keys (`lacteos`, `limpieza`, `alimentos`, etc.), each a small fraction.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/endpoints/analysis.py backend/tests/test_analysis.py
git commit -m "feat(backend): add GET /analysis/category-variation endpoint"
```

---

### Task 4: Frontend API client and schemas

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/lib/api.ts`

**Interfaces:**
- Produces: `PriceIndexSchema`/`PriceIndex` type, `getPriceIndex(days = 7): Promise<PriceIndex>`, `getCategoryVariation(days = 30): Promise<Record<string, number>>` — consumed by Tasks 5 and 6.

- [ ] **Step 1: Add the Zod schema**

In `frontend/src/types/index.ts`, add after `ProductListSchema`/`ProductList` (near the other analysis-adjacent schemas):

```typescript
export const PriceIndexSchema = z.object({
  avg_change_pct: z.number().nullable(),
  basket_size: z.number(),
  period_days: z.number(),
});
export type PriceIndex = z.infer<typeof PriceIndexSchema>;
```

No `z.coerce.number()` needed here — unlike the Decimal-backed fields fixed on 2026-08-29, `avg_change_pct` comes from a plain Python `float` (via `round()`), which FastAPI serializes as a real JSON number, not a Decimal-as-string.

- [ ] **Step 2: Add the API client functions**

In `frontend/src/lib/api.ts`, add `PriceIndexSchema` and `type PriceIndex` to the existing `@/types` import block, then add near `getProductFacets`:

```typescript
export async function getPriceIndex(days = 7): Promise<PriceIndex> {
  const { data } = await api.get("/analysis/price-index", { params: { days } });
  return PriceIndexSchema.parse(data);
}

export async function getCategoryVariation(days = 30): Promise<Record<string, number>> {
  const { data } = await api.get("/analysis/category-variation", { params: { days } });
  return z.record(z.string(), z.number()).parse(data);
}
```

- [ ] **Step 3: Verify types compile**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/lib/api.ts
git commit -m "feat(frontend): add API client for price index and category variation"
```

---

### Task 5: Wire the home page "Variación semanal" card to real data

**Files:**
- Modify: `frontend/src/app/page.tsx`

**Interfaces:**
- Consumes: `getPriceIndex(days = 7): Promise<PriceIndex>` (Task 4).

- [ ] **Step 1: Add the query**

In `frontend/src/app/page.tsx`, add `getPriceIndex` to the existing `@/lib/api` import line. Add the query near the other `useQuery` calls in `Home()`:

```tsx
  const { data: priceIndex } = useQuery({
    queryKey: ["priceIndex"],
    queryFn: () => getPriceIndex(7),
    staleTime: 10 * 60 * 1000,
  });
```

- [ ] **Step 2: Replace the hardcoded card**

Replace this block (currently hardcoded `+0,8%`):

```tsx
                    <EcoMiniCard
                      label="Variación semanal"
                      source="Índice A Cuanto Está"
                      value={<span className="mono" style={{ color: "var(--bad)" }}>+0,8%</span>}
                      delta={0.008}
                      deltaLabel={`canasta de ${totalCount !== null ? totalCount.toLocaleString("es-AR") : "3.295"} productos`}
                      hideArrow
                    />
```

with:

```tsx
                    {priceIndex?.avg_change_pct != null && (
                      <EcoMiniCard
                        label="Variación semanal"
                        source="Índice A Cuanto Está"
                        value={
                          <span className="mono" style={{ color: priceIndex.avg_change_pct > 0 ? "var(--bad)" : "var(--good)" }}>
                            {fmtPct(priceIndex.avg_change_pct)}
                          </span>
                        }
                        delta={priceIndex.avg_change_pct}
                        deltaLabel={`canasta de ${priceIndex.basket_size.toLocaleString("es-AR")} productos`}
                        hideArrow
                      />
                    )}
```

This drops the `totalCount` (unfiltered catalog size) in favor of `priceIndex.basket_size` (how many products actually entered the calculation) — the two were never the same number, and showing the real one is the point of this change. If `priceIndex` hasn't loaded yet or the basket is empty (`avg_change_pct: null`), the card doesn't render at all — same pattern already used for the other cards in this block (`{eco.dollarBlue != null && (...)}`, etc.).

- [ ] **Step 3: Verify types compile**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 4: Manual verification**

```bash
cd backend && source venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000 &
cd frontend && npm run dev &
sleep 8
```
Open `http://localhost:3000` in a browser (or use the webapp-testing skill / Playwright) and confirm:
- The "Variación semanal" card shows a real, small percentage (not `+0,8%`) with a plausible basket size (hundreds to low thousands, not `3.295` or the raw catalog total).
- No console errors.

Stop both background servers when done (`kill %1 %2` or find and kill the `uvicorn`/`next dev` processes).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat(frontend): wire home page index card to real price-index endpoint"
```

---

### Task 6: Wire the economía category breakdown to real data

**Files:**
- Modify: `frontend/src/app/economia/page.tsx`

**Interfaces:**
- Consumes: `getCategoryVariation(days = 30): Promise<Record<string, number>>` (Task 4), `CATEGORIES_DESIGN` from `@/lib/categoryMap` (already used elsewhere in the codebase — each entry is `{ id: string; name: string; backendId: ProductCategory }`).

- [ ] **Step 1: Remove the hardcoded constant and add the query**

In `frontend/src/app/economia/page.tsx`:
- Delete the `CATEGORIES_VARIATION` array (lines 9-22).
- Add `getCategoryVariation` to the existing `@/lib/api` import line.
- Add `import { CATEGORIES_DESIGN } from "@/lib/categoryMap";` to the imports.
- Add the query inside `EconomiaPage()`, near the other `useQuery` calls:

```tsx
  const { data: categoryVariation } = useQuery({
    queryKey: ["categoryVariation"],
    queryFn: () => getCategoryVariation(30),
    staleTime: 30 * 60 * 1000,
  });
```

- [ ] **Step 2: Replace the rendering block**

Replace:

```tsx
            <h2>Variación por categoría (12 meses)</h2>
            <div className="subtle" style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2 }}>
              Estimación basada en productos monitoreados
            </div>
```

with:

```tsx
            <h2>Variación por categoría (30 días)</h2>
            <div className="subtle" style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2 }}>
              Promedio de variación de precio en los productos monitoreados de cada categoría
            </div>
```

Then replace the `CATEGORIES_VARIATION.map(...)` block (and its `aboveIPC`/`max`/`ipcPct` locals, which compared against `inflationYearly`) with a version driven by `categoryVariation`, compared against **`inflationMonth`** instead of `inflationYearly` — a 30-day price change belongs next to the monthly inflation rate, not the 12-month figure:

```tsx
          {CATEGORIES_DESIGN
            .filter((cat) => categoryVariation?.[cat.backendId] != null)
            .map((cat) => {
              const pct = categoryVariation![cat.backendId];
              const aboveIPC = inflationMonth != null ? pct > inflationMonth : true;
              const max = 0.15;
              const ipcPct = inflationMonth ?? 0.03;
              return (
                <div key={cat.id} style={{ padding: "8px 0", borderTop: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 500 }}>{cat.name}</span>
                    <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: aboveIPC ? "var(--bad)" : "var(--good)" }}>
                      {fmtPct(pct)}
                    </span>
                  </div>
                  <div style={{ position: "relative", height: 6, background: "var(--bg-2)", borderRadius: 3, overflow: "hidden" }}>
                    <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${Math.min(Math.abs(pct) / max, 1) * 100}%`, background: aboveIPC ? "var(--bad)" : "var(--good)" }} />
                    {inflationMonth != null && (
                      <div title={`IPC mensual: ${fmtPct(inflationMonth, { sign: false })}`}
                        style={{ position: "absolute", left: `${Math.min(ipcPct / max, 1) * 100}%`, top: -3, bottom: -3, width: 2, background: "var(--warn)" }} />
                    )}
                  </div>
                </div>
              );
            })}
```

Notes on the changes from the original:
- `key={cat}` (a display string) becomes `key={cat.id}` (the stable design-category id).
- The bar width used to be `(pct / max) * 100` with no clamping and no sign-handling, which breaks for a negative `pct` (a category whose prices fell) — `Math.min(Math.abs(pct) / max, 1) * 100` clamps to 100% and handles negative variations sensibly (bar length reflects magnitude, color already encodes direction via `aboveIPC`).
- `+{(pct * 100).toFixed(1)...}` (which always prepended a `+`, even implicitly for values that were always positive in the fake data) becomes `fmtPct(pct)`, which already prepends `+` only for positive values and formats negatives correctly.

- [ ] **Step 3: Verify types compile**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 4: Manual verification**

With both servers running (as in Task 5, Step 4), open `http://localhost:3000/economia` and confirm:
- "Variación por categoría (30 días)" shows real categories (from `CATEGORIES_DESIGN`, e.g. "Lácteos", "Limpieza") with real percentages, not the old fixed 12-category list.
- Categories with no qualifying basket in the last 30 days are simply absent from the grid (not shown as 0%).
- The reference line/tooltip says "IPC mensual", not the old 12-month framing.
- No console errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/economia/page.tsx
git commit -m "feat(frontend): wire category breakdown to real 30-day price variation"
```

---

### Task 7: Push

- [ ] **Step 1: Run full backend and frontend checks one more time**

```bash
cd backend && source venv/bin/activate && pytest -q
cd frontend && npx tsc --noEmit && npm run lint
```
Expected: all green, lint shows only the pre-existing warnings (custom font, `<img>` elements) already known from earlier sessions.

- [ ] **Step 2: Push**

```bash
git push origin main
```
