"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";

const STORAGE_KEY = "changuito";

export interface ShoppingListItem {
  productId: string;
  qty: number;
}

type ShoppingListContextType = {
  items: ShoppingListItem[];
  add: (productId: string) => void;
  remove: (productId: string) => void;
  setQty: (productId: string, qty: number) => void;
  clear: () => void;
  has: (productId: string) => boolean;
};

const ShoppingListContext = createContext<ShoppingListContextType>({
  items: [],
  add: () => {},
  remove: () => {},
  setQty: () => {},
  clear: () => {},
  has: () => false,
});

function isShoppingListItem(v: unknown): v is ShoppingListItem {
  return (
    typeof v === "object" && v !== null &&
    typeof (v as ShoppingListItem).productId === "string" &&
    typeof (v as ShoppingListItem).qty === "number"
  );
}

function readStorage(): ShoppingListItem[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isShoppingListItem) : [];
  } catch {
    return [];
  }
}

function writeStorage(items: ShoppingListItem[]) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    // localStorage puede fallar (modo privado, cuota llena) — el changuito
    // simplemente no persiste entre visitas en ese caso, no es crítico.
  }
}

export function ShoppingListProvider({ children }: { children: React.ReactNode }) {
  // Arranca vacío (SSR-safe) y se hidrata desde localStorage recién montado,
  // mismo patrón que ThemeProvider — evita mismatch de hidratación.
  const [items, setItems] = useState<ShoppingListItem[]>([]);

  useEffect(() => {
    setItems(readStorage());
  }, []);

  const update = useCallback((next: ShoppingListItem[]) => {
    setItems(next);
    writeStorage(next);
  }, []);

  const add = useCallback((productId: string) => {
    setItems((prev) => {
      const next = prev.some((i) => i.productId === productId)
        ? prev.map((i) => (i.productId === productId ? { ...i, qty: i.qty + 1 } : i))
        : [...prev, { productId, qty: 1 }];
      writeStorage(next);
      return next;
    });
  }, []);

  const remove = useCallback((productId: string) => {
    setItems((prev) => {
      const next = prev.filter((i) => i.productId !== productId);
      writeStorage(next);
      return next;
    });
  }, []);

  const setQty = useCallback((productId: string, qty: number) => {
    setItems((prev) => {
      const next = qty <= 0
        ? prev.filter((i) => i.productId !== productId)
        : prev.map((i) => (i.productId === productId ? { ...i, qty } : i));
      writeStorage(next);
      return next;
    });
  }, []);

  const clear = useCallback(() => update([]), [update]);
  const has = useCallback((productId: string) => items.some((i) => i.productId === productId), [items]);

  return (
    <ShoppingListContext.Provider value={{ items, add, remove, setQty, clear, has }}>
      {children}
    </ShoppingListContext.Provider>
  );
}

export const useShoppingList = () => useContext(ShoppingListContext);
