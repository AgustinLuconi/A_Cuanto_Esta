"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getProductsBulk } from "@/lib/api";
import { usePriceAlerts } from "@/lib/priceAlertsContext";
import { Price, ImagePlaceholder, Icon, fmtPrice } from "@/components/design/components";

export default function AlertasPage() {
  const { alerts, removeAlert } = usePriceAlerts();

  const { data: products = [], isLoading } = useQuery({
    queryKey: ["alertsProducts", alerts.map((a) => a.productId).sort().join(",")],
    queryFn: () => getProductsBulk(alerts.map((a) => a.productId)),
    enabled: alerts.length > 0,
  });

  const productById = new Map(products.map((p) => [p.id, p]));

  if (alerts.length === 0) {
    return (
      <div className="page" style={{ textAlign: "center", padding: "64px 0" }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>🔔</div>
        <h1 style={{ fontSize: 20, marginBottom: 8 }}>No tenés alertas activas</h1>
        <p style={{ color: "var(--fg-3)", marginBottom: 16, fontSize: 13.5 }}>
          Desde la ficha de un producto, tocá &quot;Avisarme si baja&quot; para que te notifiquemos cuando alcance el precio que definas.
        </p>
        <Link href="/resultados" className="btn">Buscar productos</Link>
      </div>
    );
  }

  return (
    <div className="page">
      <h1 style={{ fontSize: 22, marginBottom: 6 }}>Mis alertas de precio</h1>
      <p style={{ color: "var(--fg-3)", fontSize: 12.5, marginBottom: 20 }}>
        Te avisamos con una notificación del navegador cuando visites el sitio y el precio ya haya bajado — no es un aviso por mail ni push con el navegador cerrado.
      </p>
      <div className="col" style={{ gap: 10 }}>
        {isLoading && <div style={{ color: "var(--fg-4)", padding: "24px 0" }}>Cargando…</div>}
        {alerts.map((alert) => {
          const p = productById.get(alert.productId);
          if (!p) return null;
          const met = p.lowest_price != null && p.lowest_price <= alert.targetPrice;
          return (
            <div key={alert.productId} className="card" style={{ padding: 14, display: "flex", alignItems: "center", gap: 14 }}>
              {p.image_url
                ? <img src={p.image_url} alt={p.name} style={{ width: 56, height: 56, objectFit: "contain", borderRadius: 8, border: "1px solid var(--border)" }} />
                : <ImagePlaceholder w={56} h={56} label={p.brand ?? p.name} />}
              <div style={{ flex: 1, minWidth: 0 }}>
                <Link href={`/producto/${p.id}`} style={{ fontWeight: 600, fontSize: 13.5, color: "var(--fg)", textDecoration: "none" }}>
                  {p.full_name}
                </Link>
                <div style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 3 }}>
                  Objetivo: <span className="mono">${fmtPrice(alert.targetPrice)}</span>
                  {met && <span style={{ color: "var(--good)", fontWeight: 600 }}> · ¡cumplido!</span>}
                </div>
              </div>
              {p.lowest_price != null && <Price value={p.lowest_price} size="md" />}
              <button aria-label="Quitar alerta" onClick={() => removeAlert(alert.productId)}
                style={{ background: "none", border: 0, cursor: "pointer", color: "var(--fg-4)" }}>
                <Icon.close />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
