import { Suspense } from "react";
import type { Metadata } from "next";
import ResultadosContent from "./ResultadosContent";
import { CATEGORIES_DESIGN } from "@/lib/categoryMap";

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; categoria?: string }>;
}): Promise<Metadata> {
  const { q: rawQ, categoria } = await searchParams;
  const q = rawQ?.trim();
  const catLabel = categoria
    ? CATEGORIES_DESIGN.find((c) => c.id === categoria)?.name
    : undefined;

  const title = q
    ? `Resultados para "${q}"`
    : catLabel
    ? catLabel
    : "Resultados";
  const description = q
    ? `Comparación de precios para "${q}" en los principales supermercados de Argentina.`
    : catLabel
    ? `Comparación de precios de productos de ${catLabel} en los principales supermercados de Argentina.`
    : "Buscá y comparná precios de productos entre los principales supermercados de Argentina.";

  return { title, description };
}

export default function ResultadosPage() {
  return (
    <Suspense fallback={
      <div className="page page-wide">
        <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 24 }}>
          <div className="col" style={{ gap: 12 }}>
            {[...Array(4)].map((_, i) => (
              <div key={i} className="card" style={{ height: 80, background: "var(--bg-2)" }} />
            ))}
          </div>
          <div className="col" style={{ gap: 12 }}>
            {[...Array(6)].map((_, i) => (
              <div key={i} className="card" style={{ height: 112, background: "var(--bg-2)" }} />
            ))}
          </div>
        </div>
      </div>
    }>
      <ResultadosContent />
    </Suspense>
  );
}
