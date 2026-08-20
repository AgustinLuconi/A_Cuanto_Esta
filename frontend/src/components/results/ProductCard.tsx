"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import Image from "next/image";
import { getProduct } from "@/lib/api";
import type { Product, Supermarket } from "@/types";

const CATEGORY_EMOJI: Record<string, string> = {
  alimentos: "🥫",
  bebidas: "🥤",
  lacteos: "🥛",
  limpieza: "🧹",
  higiene_personal: "🧴",
  carnes: "🥩",
  frutas_verduras: "🥦",
  panaderia: "🍞",
  congelados: "🧊",
  snacks: "🍿",
  desayuno: "☕",
  otros: "📦",
};

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

function fmtARS(v: number): string {
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(v);
}

export default function ProductCard({
  product,
  isCheapest,
}: {
  product: Product;
  isCheapest: boolean;
}) {
  const { data: detail, isLoading } = useQuery({
    queryKey: ["product", product.id],
    queryFn: () => getProduct(product.id),
  });

  const lowestPrice = detail?.lowest_price;
  const cheapestEntry = detail?.current_prices.find(
    (p) => p.price === lowestPrice
  );
  const availableCount = detail?.current_prices.filter(
    (p) => p.in_stock
  ).length ?? 0;
  const totalSupermarkets = 9;

  return (
    <Link
      href={`/producto/${product.id}`}
      className="block bg-surface border border-border rounded-xl p-4 hover:shadow-sm hover:border-primary/30 transition-all"
    >
      <div className="flex gap-4">
        {/* Imagen */}
        <div className="w-20 h-20 shrink-0 bg-background rounded-lg overflow-hidden flex items-center justify-center">
          {product.image_url ? (
            <Image
              src={product.image_url}
              alt={product.name}
              width={80}
              height={80}
              className="object-contain w-full h-full"
              unoptimized
            />
          ) : (
            <span className="text-3xl">
              {CATEGORY_EMOJI[product.category] ?? "📦"}
            </span>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-start justify-between gap-2">
            <div>
              {product.brand && (
                <p className="text-xs font-medium text-neutral uppercase tracking-wide">
                  {product.brand}
                </p>
              )}
              <p className="text-sm font-medium text-primary line-clamp-2 leading-snug">
                {product.name}
                {product.quantity && (
                  <span className="text-neutral font-normal">
                    {" "}· {product.quantity} {product.unit}
                  </span>
                )}
              </p>
            </div>
            {isCheapest && (
              <span className="shrink-0 px-2 py-0.5 bg-down/10 text-down text-xs font-semibold rounded-full">
                MÁS BARATO
              </span>
            )}
          </div>

          {/* Precio */}
          {isLoading ? (
            <div className="flex gap-3 items-center">
              <div className="h-6 w-20 bg-border rounded animate-pulse" />
              <div className="h-4 w-16 bg-border rounded animate-pulse" />
            </div>
          ) : (
            <div className="flex items-baseline gap-2">
              {lowestPrice != null ? (
                <>
                  <span className="text-lg font-bold text-primary tabular-nums">
                    {fmtARS(lowestPrice)}
                  </span>
                  {cheapestEntry && (
                    <span className="text-xs text-neutral">
                      en {SUPERMARKET_LABELS[cheapestEntry.supermarket] ?? cheapestEntry.supermarket}
                    </span>
                  )}
                </>
              ) : (
                <span className="text-sm text-neutral">Sin precios</span>
              )}
            </div>
          )}

          {/* Disponibilidad */}
          {!isLoading && availableCount > 0 && (
            <p className="text-xs text-neutral">
              Disponible en{" "}
              <span className="font-medium text-primary">
                {availableCount}/{totalSupermarkets}
              </span>{" "}
              supermercados ·{" "}
              <span className="text-primary font-medium hover:underline">
                Comparar precios →
              </span>
            </p>
          )}
        </div>
      </div>
    </Link>
  );
}
