"use client";

import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { usePriceAlerts } from "@/lib/priceAlertsContext";
import { getProductsBulk } from "@/lib/api";

/**
 * Revisa las alertas de precio guardadas contra los precios actuales cada vez
 * que se carga el sitio, y dispara una Notification del navegador si alguna
 * ya cumplió su precio objetivo. No es un push real: solo se dispara mientras
 * el sitio está abierto (aunque sea en una pestaña de fondo) — no hay
 * infraestructura de push/email para avisar con el navegador cerrado.
 */
export default function PriceAlertsChecker() {
  const { alerts, markNotified } = usePriceAlerts();
  const checkedRef = useRef(false);

  const ids = alerts.map((a) => a.productId);
  const { data: products = [] } = useQuery({
    queryKey: ["priceAlertsCheck", ids.sort().join(",")],
    queryFn: () => getProductsBulk(ids),
    enabled: ids.length > 0,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (products.length === 0 || checkedRef.current) return;
    checkedRef.current = true;

    for (const alert of alerts) {
      const product = products.find((p) => p.id === alert.productId);
      if (!product || product.lowest_price == null) continue;
      if (product.lowest_price > alert.targetPrice) continue;
      if (alert.notifiedAtPrice === product.lowest_price) continue; // ya avisado a este precio

      markNotified(alert.productId, product.lowest_price);

      if (typeof window !== "undefined" && "Notification" in window && Notification.permission === "granted") {
        try {
          const n = new Notification("¡Bajó de precio!", {
            body: `${product.full_name}: ahora $${product.lowest_price.toLocaleString("es-AR")} (tu objetivo: $${alert.targetPrice.toLocaleString("es-AR")})`,
            tag: `price-alert-${alert.productId}`,
          });
          n.onclick = () => window.focus();
        } catch {
          // Notification puede fallar en algunos contextos (iframe, permisos
          // revocados a mitad de sesión) — no es crítico, se reintenta la
          // próxima carga.
        }
      }
    }
  }, [products, alerts, markNotified]);

  return null;
}
