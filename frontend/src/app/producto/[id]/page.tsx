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
  const { labels, series } = priceHistory.length > 0 ? buildPriceChartData(priceHistory) : { labels: [], series: {} };
  // Con un único día de historial, MultiLineChart no puede trazar una línea (división por
  // labels.length - 1 en su escala X produce NaN). Se exige al menos 2 días distintos antes
  // de intentar renderizar el gráfico; si no, se muestra el mismo estado vacío que para
  // "sin historial en absoluto".
  const hasChart = labels.length >= 2;
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
