"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getProductsBulk } from "@/lib/api";
import { useShoppingList } from "@/lib/shoppingListContext";
import { Price, SMSwatch, SM_BY_ID, ImagePlaceholder, Icon, fmtPrice } from "@/components/design/components";
import type { ProductWithPrices, Supermarket } from "@/types";

export default function ChanguitoPage() {
  const { items, remove, setQty, clear } = useShoppingList();

  const { data: products = [], isLoading } = useQuery({
    queryKey: ["changuitoProducts", items.map((i) => i.productId).sort().join(",")],
    queryFn: () => getProductsBulk(items.map((i) => i.productId)),
    enabled: items.length > 0,
  });

  const productById = new Map(products.map((p) => [p.id, p]));
  // Ítems cuyo producto ya no existe en el catálogo (borrado) — se avisan
  // aparte en vez de desaparecer en silencio. Solo se evalúa una vez que la
  // consulta terminó: mientras carga, `products` está vacío y todo parecería
  // "no disponible" por error.
  const missingIds = isLoading ? [] : items.map((i) => i.productId).filter((id) => !productById.has(id));

  // Total "estrategia mixta": cada producto al precio más barato disponible,
  // sin importar en qué supermercado.
  let mixedTotal = 0;
  for (const item of items) {
    const p = productById.get(item.productId);
    if (p?.lowest_price != null) mixedTotal += p.lowest_price * item.qty;
  }

  // Total por supermercado — solo para los que tienen TODOS los productos de
  // la lista, para poder responder "¿me conviene comprar todo en un solo lugar?".
  const allSupermarkets = new Set<Supermarket>();
  for (const p of products) for (const cp of p.current_prices) allSupermarkets.add(cp.supermarket);

  const totalsBySupermarket: { supermarket: Supermarket; total: number; covers: number }[] = [];
  for (const sm of Array.from(allSupermarkets)) {
    let total = 0;
    let covers = 0;
    for (const item of items) {
      const p = productById.get(item.productId);
      const cp = p?.current_prices.find((c) => c.supermarket === sm);
      if (cp) { total += cp.price * item.qty; covers += 1; }
    }
    totalsBySupermarket.push({ supermarket: sm, total, covers });
  }
  totalsBySupermarket.sort((a, b) => b.covers - a.covers || a.total - b.total);
  const fullCoverageTotals = totalsBySupermarket.filter((t) => t.covers === items.length && items.length > 0);
  const bestFullCoverage = fullCoverageTotals[0];
  const savingsVsBest = bestFullCoverage ? bestFullCoverage.total - mixedTotal : null;

  if (items.length === 0) {
    return (
      <div className="page" style={{ textAlign: "center", padding: "64px 0" }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>🛒</div>
        <h1 style={{ fontSize: 20, marginBottom: 8 }}>Tu changuito está vacío</h1>
        <p style={{ color: "var(--fg-3)", marginBottom: 16, fontSize: 13.5 }}>
          Agregá productos desde los resultados de búsqueda o la ficha de cada producto.
        </p>
        <Link href="/resultados" className="btn">Buscar productos</Link>
      </div>
    );
  }

  return (
    <div className="page">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h1 style={{ fontSize: 22 }}>Mi changuito</h1>
        <button className="btn secondary" onClick={clear} style={{ fontSize: 12.5 }}>
          <Icon.trash /> Vaciar
        </button>
      </div>

      {missingIds.length > 0 && (
        <div className="card" style={{ padding: 12, marginBottom: 16, fontSize: 12.5, color: "var(--fg-3)" }}>
          {missingIds.length} producto{missingIds.length > 1 ? "s" : ""} de tu lista ya no está{missingIds.length > 1 ? "n" : ""} disponible{missingIds.length > 1 ? "s" : ""} y se {missingIds.length > 1 ? "excluyen" : "excluye"} del total.
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 24, alignItems: "start" }}>
        {/* LISTA */}
        <div className="col" style={{ gap: 10 }}>
          {isLoading && <div style={{ color: "var(--fg-4)", padding: "24px 0" }}>Cargando…</div>}
          {items.map((item) => {
            const p = productById.get(item.productId);
            if (!p) return null;
            const cheapest = p.current_prices.reduce((best, cp) =>
              (!best || cp.price < best.price) ? cp : best, null as ProductWithPrices["current_prices"][0] | null);
            return (
              <div key={item.productId} className="card" style={{ padding: 14, display: "flex", alignItems: "center", gap: 14 }}>
                {p.image_url
                  ? <img src={p.image_url} alt={p.name} style={{ width: 56, height: 56, objectFit: "contain", borderRadius: 8, border: "1px solid var(--border)" }} />
                  : <ImagePlaceholder w={56} h={56} label={p.brand ?? p.name} />}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Link href={`/producto/${p.id}`} style={{ fontWeight: 600, fontSize: 13.5, color: "var(--fg)", textDecoration: "none" }}>
                    {p.full_name}
                  </Link>
                  {cheapest && (
                    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--fg-3)", marginTop: 3 }}>
                      más barato en <SMSwatch sm={cheapest.supermarket} size="sm" />
                      {SM_BY_ID[cheapest.supermarket]?.name ?? cheapest.supermarket}
                    </div>
                  )}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <button className="btn secondary" style={{ padding: "4px 9px", fontSize: 13 }}
                    onClick={() => setQty(item.productId, item.qty - 1)}>−</button>
                  <span className="mono" style={{ minWidth: 20, textAlign: "center", fontSize: 13 }}>{item.qty}</span>
                  <button className="btn secondary" style={{ padding: "4px 9px", fontSize: 13 }}
                    onClick={() => setQty(item.productId, item.qty + 1)}>+</button>
                </div>
                {cheapest && <Price value={cheapest.price * item.qty} size="md" />}
                <button aria-label="Quitar" onClick={() => remove(item.productId)}
                  style={{ background: "none", border: 0, cursor: "pointer", color: "var(--fg-4)" }}>
                  <Icon.close />
                </button>
              </div>
            );
          })}
        </div>

        {/* RESUMEN */}
        <div className="card" style={{ padding: 20, position: "sticky", top: 20 }}>
          <h3 style={{ fontSize: 14, marginBottom: 14 }}>Resumen</h3>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10, fontSize: 13 }}>
            <span style={{ color: "var(--fg-3)" }}>Comprando cada producto en su super más barato</span>
          </div>
          <div style={{ marginBottom: 18 }}>
            <Price value={mixedTotal} size="xl" />
          </div>

          {fullCoverageTotals.length > 0 && (
            <>
              <div style={{ fontSize: 11, color: "var(--fg-3)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                Si comprás todo en un solo lugar
              </div>
              <div className="col" style={{ gap: 6, marginBottom: 12 }}>
                {fullCoverageTotals.slice(0, 5).map((t) => (
                  <div key={t.supermarket} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12.5 }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <SMSwatch sm={t.supermarket} size="sm" />
                      {SM_BY_ID[t.supermarket]?.name ?? t.supermarket}
                    </span>
                    <span className="mono">${fmtPrice(t.total)}</span>
                  </div>
                ))}
              </div>
              {savingsVsBest != null && savingsVsBest > 0 && (
                <div style={{ fontSize: 11.5, color: "var(--good)" }}>
                  Combinando supermercados ahorrás ${fmtPrice(savingsVsBest)} vs. el mejor lugar único.
                </div>
              )}
            </>
          )}
          {fullCoverageTotals.length === 0 && items.length > 1 && (
            <div style={{ fontSize: 11.5, color: "var(--fg-4)" }}>
              Ningún supermercado tiene todos los productos de tu lista — comparación por lugar único no disponible.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
