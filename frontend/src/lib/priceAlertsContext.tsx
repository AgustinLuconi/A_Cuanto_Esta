"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";

const STORAGE_KEY = "price_alerts";

export interface PriceAlert {
  productId: string;
  targetPrice: number;
  createdAt: string;
  notifiedAtPrice: number | null; // último precio con el que ya se avisó, para no repetir
}

type PriceAlertsContextType = {
  alerts: PriceAlert[];
  addAlert: (productId: string, targetPrice: number) => void;
  removeAlert: (productId: string) => void;
  hasAlert: (productId: string) => boolean;
  markNotified: (productId: string, price: number) => void;
};

const PriceAlertsContext = createContext<PriceAlertsContextType>({
  alerts: [],
  addAlert: () => {},
  removeAlert: () => {},
  hasAlert: () => false,
  markNotified: () => {},
});

function isAlert(v: unknown): v is PriceAlert {
  return (
    typeof v === "object" && v !== null &&
    typeof (v as PriceAlert).productId === "string" &&
    typeof (v as PriceAlert).targetPrice === "number"
  );
}

function readStorage(): PriceAlert[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isAlert) : [];
  } catch {
    return [];
  }
}

function writeStorage(alerts: PriceAlert[]) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(alerts));
  } catch {
    // localStorage puede fallar (modo privado, cuota llena) — las alertas
    // simplemente no persisten entre visitas en ese caso.
  }
}

export function PriceAlertsProvider({ children }: { children: React.ReactNode }) {
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);

  useEffect(() => {
    setAlerts(readStorage());
  }, []);

  const addAlert = useCallback((productId: string, targetPrice: number) => {
    setAlerts((prev) => {
      const next = [
        ...prev.filter((a) => a.productId !== productId),
        { productId, targetPrice, createdAt: new Date().toISOString(), notifiedAtPrice: null },
      ];
      writeStorage(next);
      return next;
    });
    if (typeof window !== "undefined" && "Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  const removeAlert = useCallback((productId: string) => {
    setAlerts((prev) => {
      const next = prev.filter((a) => a.productId !== productId);
      writeStorage(next);
      return next;
    });
  }, []);

  const hasAlert = useCallback((productId: string) => alerts.some((a) => a.productId === productId), [alerts]);

  const markNotified = useCallback((productId: string, price: number) => {
    setAlerts((prev) => {
      const next = prev.map((a) => (a.productId === productId ? { ...a, notifiedAtPrice: price } : a));
      writeStorage(next);
      return next;
    });
  }, []);

  return (
    <PriceAlertsContext.Provider value={{ alerts, addAlert, removeAlert, hasAlert, markNotified }}>
      {children}
    </PriceAlertsContext.Provider>
  );
}

export const usePriceAlerts = () => useContext(PriceAlertsContext);
