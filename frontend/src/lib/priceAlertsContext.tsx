"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { getPriceAlerts, getVapidPublicKey, subscribePush } from "@/lib/api";
import { deletePriceAlert } from "@/lib/api";

export interface PriceAlert {
  id: string;
  productId: string;
  targetPrice: number;
  createdAt: string;
  notifiedAtPrice: number | null; // último precio con el que ya se avisó, para no repetir
}

type PriceAlertsContextType = {
  alerts: PriceAlert[];
  addAlert: (productId: string, targetPrice: number) => Promise<void>;
  removeAlert: (productId: string) => Promise<void>;
  hasAlert: (productId: string) => boolean;
};

const PriceAlertsContext = createContext<PriceAlertsContextType>({
  alerts: [],
  addAlert: async () => {},
  removeAlert: async () => {},
  hasAlert: () => false,
});

function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const base64Safe = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64Safe);
  const output = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) {
    output[i] = rawData.charCodeAt(i);
  }
  return output;
}

/**
 * Registra el service worker (si hace falta), pide permiso de
 * notificaciones, y devuelve una PushSubscription activa -- o `null` si el
 * navegador no soporta push, o el usuario no dio permiso. La usa tanto
 * `addAlert` acá abajo como el banner de migración (Task 13).
 */
export async function getOrCreateSubscription(): Promise<PushSubscription | null> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator) || !("PushManager" in window)) {
    return null;
  }
  const registration = await navigator.serviceWorker.register("/sw.js");
  const existing = await registration.pushManager.getSubscription();
  if (existing) return existing;

  if (Notification.permission === "denied") return null;
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return null;

  const publicKey = await getVapidPublicKey();
  return registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });
}

export function PriceAlertsProvider({ children }: { children: React.ReactNode }) {
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const loadedRef = useRef(false);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    (async () => {
      if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
      try {
        const registration = await navigator.serviceWorker.getRegistration();
        const existing = await registration?.pushManager.getSubscription();
        if (!existing) return;
        const serverAlerts = await getPriceAlerts(existing.endpoint);
        setAlerts(serverAlerts);
      } catch {
        // sin conexión o browser sin soporte — se sigue sin alertas cargadas,
        // el usuario puede reintentar creando una nueva.
      }
    })();
  }, []);

  const addAlert = useCallback(async (productId: string, targetPrice: number) => {
    try {
      const subscription = await getOrCreateSubscription();
      if (!subscription) {
        window.alert("No se pudo activar la notificación (permiso denegado o navegador sin soporte).");
        return;
      }
      const subJson = subscription.toJSON() as { endpoint: string; keys: { p256dh: string; auth: string } };
      const result = await subscribePush(subJson, [{ product_id: productId, target_price: targetPrice }]);
      setAlerts(result);
    } catch (err) {
      // Sin esto, un fallo de red/SW dejaba la UI (el formulario ya
      // cerrado por el llamador, que no espera esta promesa) mostrando
      // como si la alerta se hubiera creado aunque no haya pasado nada.
      console.error("No se pudo crear la alerta de precio:", err);
      window.alert("No se pudo crear la alerta. Probá de nuevo en un momento.");
    }
  }, []);

  const removeAlert = useCallback(
    async (productId: string) => {
      const alert = alerts.find((a) => a.productId === productId);
      if (!alert) return;
      try {
        await deletePriceAlert(alert.id);
        setAlerts((prev) => prev.filter((a) => a.id !== alert.id));
      } catch (err) {
        console.error("No se pudo quitar la alerta de precio:", err);
        window.alert("No se pudo quitar la alerta. Probá de nuevo en un momento.");
      }
    },
    [alerts]
  );

  const hasAlert = useCallback((productId: string) => alerts.some((a) => a.productId === productId), [alerts]);

  return (
    <PriceAlertsContext.Provider value={{ alerts, addAlert, removeAlert, hasAlert }}>
      {children}
    </PriceAlertsContext.Provider>
  );
}

export const usePriceAlerts = () => useContext(PriceAlertsContext);
