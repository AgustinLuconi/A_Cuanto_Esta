"use client";

import { useQuery, useQueries } from "@tanstack/react-query";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import Image from "next/image";
import { getProductCount, getSupermarketLogos } from "@/lib/api";
import type { ProductCategory, Supermarket } from "@/types";

const CATEGORIES: { key: ProductCategory; label: string }[] = [
  { key: "alimentos", label: "Alimentos" },
  { key: "bebidas", label: "Bebidas" },
  { key: "lacteos", label: "Lácteos" },
  { key: "limpieza", label: "Limpieza" },
  { key: "higiene_personal", label: "Higiene" },
  { key: "carnes", label: "Carnes" },
  { key: "frutas_verduras", label: "Frutas y Verduras" },
  { key: "panaderia", label: "Panadería" },
  { key: "congelados", label: "Congelados" },
  { key: "snacks", label: "Snacks" },
  { key: "desayuno", label: "Desayuno" },
  { key: "otros", label: "Otros" },
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

  function setCategory(cat: ProductCategory | undefined) {
    const params = new URLSearchParams(searchParams.toString());
    if (cat) {
      params.set("categoria", cat);
    } else {
      params.delete("categoria");
    }
    router.push(`${pathname}?${params.toString()}`);
  }

  function toggleSupermarket(sm: Supermarket) {
    const params = new URLSearchParams(searchParams.toString());
    const current = params.getAll("super");
    if (current.includes(sm)) {
      params.delete("super");
      current.filter((s) => s !== sm).forEach((s) => params.append("super", s));
    } else {
      params.append("super", sm);
    }
    router.push(`${pathname}?${params.toString()}`);
  }

  const supermarkets = Object.keys(SUPERMARKET_LABELS) as Supermarket[];

  return (
    <aside className="w-64 shrink-0 space-y-6">
      {/* Categorías */}
      <div>
        <h3 className="text-xs font-semibold text-neutral uppercase tracking-wide mb-3">
          Categoría
        </h3>
        <ul className="space-y-0.5">
          <li>
            <button
              onClick={() => setCategory(undefined)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                !activeCategory
                  ? "bg-primary text-white font-medium"
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
                  onClick={() => setCategory(cat.key)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                    isActive
                      ? "bg-primary text-white font-medium"
                      : "text-neutral hover:bg-border/50 hover:text-primary"
                  }`}
                >
                  <span>{cat.label}</span>
                  {count != null && (
                    <span className={`text-xs tabular-nums ${isActive ? "text-white/70" : "text-neutral"}`}>
                      {new Intl.NumberFormat("es-AR").format(count)}
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Supermercados */}
      <div>
        <h3 className="text-xs font-semibold text-neutral uppercase tracking-wide mb-3">
          Supermercado
        </h3>
        <ul className="space-y-1">
          {supermarkets.map((sm) => {
            const isChecked = activeSupermarkets.includes(sm);
            const logoUrl = logos?.[sm];
            return (
              <li key={sm}>
                <label className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-border/50 cursor-pointer transition-colors">
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
                      width={32}
                      height={16}
                      className="object-contain"
                      unoptimized
                    />
                  )}
                  <span className="text-sm text-primary">
                    {SUPERMARKET_LABELS[sm]}
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
}
