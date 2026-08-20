"use client";

import { useState } from "react";
import { useQuery, useQueries } from "@tanstack/react-query";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { getProductCount, getSupermarketLogos } from "@/lib/api";
import type { ProductCategory, Supermarket } from "@/types";

const CATEGORIES: { key: ProductCategory; label: string; emoji: string }[] = [
  { key: "alimentos", label: "Alimentos", emoji: "🥫" },
  { key: "bebidas", label: "Bebidas", emoji: "🥤" },
  { key: "lacteos", label: "Lácteos", emoji: "🥛" },
  { key: "limpieza", label: "Limpieza", emoji: "🧹" },
  { key: "higiene_personal", label: "Higiene", emoji: "🧴" },
  { key: "carnes", label: "Carnes", emoji: "🥩" },
  { key: "frutas_verduras", label: "Frutas y Verduras", emoji: "🥦" },
  { key: "panaderia", label: "Panadería", emoji: "🍞" },
  { key: "congelados", label: "Congelados", emoji: "🧊" },
  { key: "snacks", label: "Snacks", emoji: "🍿" },
  { key: "desayuno", label: "Desayuno", emoji: "☕" },
  { key: "mascotas", label: "Mascotas", emoji: "🐶" },
  { key: "bebes", label: "Bebés", emoji: "👶" },
  { key: "hogar_bazar", label: "Hogar y Bazar", emoji: "🏠" },
  { key: "farmacia_salud", label: "Salud y Farmacia", emoji: "💊" },
  { key: "electro_tecnologia", label: "Electro y Tecno", emoji: "⚡" },
  { key: "otros", label: "Otros", emoji: "📦" },
];

const SUPERMARKET_LABELS: Record<Supermarket, string> = {
  carrefour: "Carrefour",
  coto: "Coto",
  disco: "Disco",
  atomo: "Átomo",
  vea: "Vea",
  jumbo: "Jumbo",
  dia: "Día",
  la_anonima: "La Anónima",
  chango_mas: "Chango Más",
};

export default function FilterSidebar({
  activeSupermarkets,
}: {
  activeSupermarkets: Supermarket[];
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const activeCategory = (searchParams.get("categoria") as ProductCategory) ?? undefined;
  const isOnlyOnSale = searchParams.get("oferta") === "true";
  const isOnlyInStock = searchParams.get("stock") === "true";
  const activeBrand = searchParams.get("marca") ?? "";

  const [brandInput, setBrandInput] = useState(activeBrand);
  const [categoriesOpen, setCategoriesOpen] = useState(true);
  const [supermarketsOpen, setSupermarketsOpen] = useState(true);

  const { data: logos } = useQuery({
    queryKey: ["supermarkets", "logos"],
    queryFn: getSupermarketLogos,
  });

  const countQueries = useQueries({
    queries: CATEGORIES.map((cat) => ({
      queryKey: ["products", "count", cat.key],
      queryFn: () => getProductCount(cat.key),
    })),
  });

  function updateParam(key: string, value: string | undefined) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    router.push(`${pathname}?${params.toString()}`);
  }

  function toggleSupermarket(sm: Supermarket) {
    const params = new URLSearchParams(searchParams.toString());
    const current = params.getAll("super");
    params.delete("super");
    if (current.includes(sm)) {
      current.filter((s) => s !== sm).forEach((s) => params.append("super", s));
    } else {
      current.concat(sm).forEach((s) => params.append("super", s));
    }
    router.push(`${pathname}?${params.toString()}`);
  }

  const supermarkets = Object.keys(SUPERMARKET_LABELS) as Supermarket[];

  return (
    <aside className="w-64 shrink-0 space-y-6 bg-surface border border-border p-4 rounded-xl shadow-xs">
      {/* Título & Limpiar Filtros */}
      <div className="flex items-center justify-between pb-2 border-b border-border">
        <h2 className="text-sm font-semibold text-primary">Filtros</h2>
        {(activeCategory || isOnlyOnSale || isOnlyInStock || activeBrand || activeSupermarkets.length > 0) && (
          <button
            onClick={() => router.push(pathname)}
            className="text-xs text-primary/70 hover:text-primary underline font-medium transition-colors"
          >
            Limpiar
          </button>
        )}
      </div>

      {/* Switches Rápidos (Ofertas / Stock) */}
      <div className="space-y-2.5">
        <label className="flex items-center justify-between p-2.5 rounded-lg border border-border bg-background hover:border-primary/30 cursor-pointer transition-colors">
          <span className="text-xs font-medium text-primary flex items-center gap-1.5">
            🔥 Solo Ofertas
          </span>
          <input
            type="checkbox"
            checked={isOnlyOnSale}
            onChange={(e) => updateParam("oferta", e.target.checked ? "true" : undefined)}
            className="rounded border-border text-primary focus:ring-primary/20"
          />
        </label>

        <label className="flex items-center justify-between p-2.5 rounded-lg border border-border bg-background hover:border-primary/30 cursor-pointer transition-colors">
          <span className="text-xs font-medium text-primary flex items-center gap-1.5">
            📦 Solo En Stock
          </span>
          <input
            type="checkbox"
            checked={isOnlyInStock}
            onChange={(e) => updateParam("stock", e.target.checked ? "true" : undefined)}
            className="rounded border-border text-primary focus:ring-primary/20"
          />
        </label>
      </div>

      {/* Buscador de Marca */}
      <div>
        <h3 className="text-xs font-semibold text-neutral uppercase tracking-wide mb-2">
          Marca
        </h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            updateParam("marca", brandInput.trim() || undefined);
          }}
          className="flex gap-1.5"
        >
          <input
            type="text"
            placeholder="Ej. Arcor, Serenísima..."
            value={brandInput}
            onChange={(e) => setBrandInput(e.target.value)}
            className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-border bg-background focus:outline-none focus:border-primary"
          />
          <button
            type="submit"
            className="px-2.5 py-1.5 bg-primary text-white text-xs rounded-lg font-medium hover:bg-primary/90 transition-colors"
          >
            Buscar
          </button>
        </form>
      </div>

      {/* Categorías */}
      <div>
        <button
          onClick={() => setCategoriesOpen(!categoriesOpen)}
          className="w-full flex items-center justify-between text-xs font-semibold text-neutral uppercase tracking-wide mb-2"
        >
          <span>Categorías</span>
          <span>{categoriesOpen ? "−" : "+"}</span>
        </button>

        <AnimatePresence>
          {categoriesOpen && (
            <motion.ul
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-0.5 overflow-hidden"
            >
              <li>
                <button
                  onClick={() => updateParam("categoria", undefined)}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                    !activeCategory
                      ? "bg-primary text-white font-medium shadow-xs"
                      : "text-neutral hover:bg-border/50 hover:text-primary"
                  }`}
                >
                  <span>Todas</span>
                </button>
              </li>
              {CATEGORIES.map((cat, i) => {
                const count = countQueries[i]?.data?.count;
                const isActive = activeCategory === cat.key;
                return (
                  <li key={cat.key}>
                    <button
                      onClick={() => updateParam("categoria", cat.key)}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                        isActive
                          ? "bg-primary text-white font-medium shadow-xs"
                          : "text-neutral hover:bg-border/50 hover:text-primary"
                      }`}
                    >
                      <span className="flex items-center gap-1.5">
                        <span>{cat.emoji}</span>
                        <span>{cat.label}</span>
                      </span>
                      {count != null && (
                        <span
                          className={`tabular-nums text-[10px] ${
                            isActive ? "text-white/80" : "text-neutral"
                          }`}
                        >
                          {new Intl.NumberFormat("es-AR").format(count)}
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </motion.ul>
          )}
        </AnimatePresence>
      </div>

      {/* Supermercados */}
      <div>
        <button
          onClick={() => setSupermarketsOpen(!supermarketsOpen)}
          className="w-full flex items-center justify-between text-xs font-semibold text-neutral uppercase tracking-wide mb-2"
        >
          <span>Supermercados</span>
          <span>{supermarketsOpen ? "−" : "+"}</span>
        </button>

        <AnimatePresence>
          {supermarketsOpen && (
            <motion.ul
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-1 overflow-hidden"
            >
              {supermarkets.map((sm) => {
                const isChecked = activeSupermarkets.includes(sm);
                const logoUrl = logos?.[sm];
                return (
                  <li key={sm}>
                    <label className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-border/50 cursor-pointer transition-colors text-xs">
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleSupermarket(sm)}
                        className="rounded border-border text-primary focus:ring-primary/20"
                      />
                      {logoUrl && (
                        <Image
                          src={logoUrl}
                          alt={SUPERMARKET_LABELS[sm]}
                          width={28}
                          height={14}
                          className="object-contain"
                          unoptimized
                        />
                      )}
                      <span className="text-primary font-medium">
                        {SUPERMARKET_LABELS[sm]}
                      </span>
                    </label>
                  </li>
                );
              })}
            </motion.ul>
          )}
        </AnimatePresence>
      </div>
    </aside>
  );
}
