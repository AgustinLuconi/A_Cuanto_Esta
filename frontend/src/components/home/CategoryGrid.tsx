"use client";

import { useQueries } from "@tanstack/react-query";
import Link from "next/link";
import { motion } from "framer-motion";
import { getProductCount } from "@/lib/api";
import type { ProductCategory } from "@/types";

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

export default function CategoryGrid() {
  const countQueries = useQueries({
    queries: CATEGORIES.map((cat) => ({
      queryKey: ["products", "count", cat.key],
      queryFn: () => getProductCount(cat.key),
    })),
  });

  return (
    <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-3">
      {CATEGORIES.map((cat, i) => {
        const count = countQueries[i]?.data?.count;
        return (
          <motion.div
            key={cat.key}
            whileHover={{ y: -4, scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            transition={{ type: "spring", stiffness: 400, damping: 25 }}
          >
            <Link
              href={`/resultados?categoria=${cat.key}`}
              className="flex flex-col items-center gap-2 p-4 bg-surface border border-border rounded-xl hover:border-primary/40 hover:shadow-md transition-all group"
            >
              <span className="text-3xl transition-transform group-hover:scale-110">{cat.emoji}</span>
              <span className="text-xs font-medium text-primary text-center leading-tight group-hover:text-primary">
                {cat.label}
              </span>
              {count != null ? (
                <span className="text-xs text-neutral tabular-nums">
                  {new Intl.NumberFormat("es-AR").format(count)}
                </span>
              ) : (
                <span className="text-xs text-border">—</span>
              )}
            </Link>
          </motion.div>
        );
      })}
    </div>
  );
}
