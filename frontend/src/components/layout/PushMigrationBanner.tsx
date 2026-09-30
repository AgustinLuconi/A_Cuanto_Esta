"use client";

import { useEffect, useState } from "react";
import { subscribePush } from "@/lib/api";
import { getOrCreateSubscription } from "@/lib/priceAlertsContext";

const STORAGE_KEY = "price_alerts";

interface OldAlert {
  productId: string;
  targetPrice: number;
}

function readOldAlerts(): OldAlert[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (v): v is OldAlert =>
        typeof v === "object" &&
        v !== null &&
        typeof (v as OldAlert).productId === "string" &&
        typeof (v as OldAlert).targetPrice === "number"
    );
  } catch {
    return [];
  }
}

/**
 * Detecta alertas guardadas por el sistema viejo (localStorage) y ofrece
 * migrarlas de una a notificaciones push reales con un solo click. Se
 * muestra solo si hay alertas viejas Y todavía no hay una suscripción push
 * activa en este navegador -- una vez migrado (o si nunca hubo alertas
 * viejas), no vuelve a aparecer.
 */
export default function PushMigrationBanner() {
  const [oldAlerts, setOldAlerts] = useState<OldAlert[] | null>(null);
  const [migrating, setMigrating] = useState(false);

  useEffect(() => {
    (async () => {
      const found = readOldAlerts();
      if (found.length === 0) return;
      if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;

      const registration = await navigator.serviceWorker.getRegistration();
      const existing = await registration?.pushManager.getSubscription();
      if (existing) {
        // Ya se migró en algún momento anterior -- limpiar el resto viejo.
        window.localStorage.removeItem(STORAGE_KEY);
        return;
      }
      setOldAlerts(found);
    })();
  }, []);

  if (!oldAlerts || oldAlerts.length === 0) return null;

  const activate = async () => {
    setMigrating(true);
    try {
      const subscription = await getOrCreateSubscription();
      if (!subscription) {
        window.alert("No se pudo activar (permiso denegado o navegador sin soporte).");
        return;
      }
      const subJson = subscription.toJSON() as { endpoint: string; keys: { p256dh: string; auth: string } };
      await subscribePush(
        subJson,
        oldAlerts.map((a) => ({ product_id: a.productId, target_price: a.targetPrice }))
      );
      window.localStorage.removeItem(STORAGE_KEY);
      window.location.reload();
    } finally {
      setMigrating(false);
    }
  };

  return (
    <div
      style={{
        background: "var(--warn-tint)",
        borderBottom: "1px solid var(--border)",
        padding: "8px 16px",
        fontSize: 13,
        display: "flex",
        gap: 12,
        alignItems: "center",
        justifyContent: "center",
        flexWrap: "wrap",
      }}
    >
      <span>
        Tenés {oldAlerts.length} alerta{oldAlerts.length > 1 ? "s" : ""} de precio guardada
        {oldAlerts.length > 1 ? "s" : ""} en este navegador.
      </span>
      <button className="btn" style={{ fontSize: 12 }} disabled={migrating} onClick={activate}>
        {migrating ? "Activando..." : "Activar notificaciones push"}
      </button>
    </div>
  );
}
