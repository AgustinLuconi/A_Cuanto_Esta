"use client";

import { useQuery } from "@tanstack/react-query";
import { getIndecPriceReference } from "@/lib/api";
import { VarBadge, fmtPrice } from "@/components/design/components";
import { fmtPeriod } from "./format";

export default function PriceReferenceSection() {
  const { data, isError } = useQuery({
    queryKey: ["indecPriceReference"],
    queryFn: getIndecPriceReference,
    staleTime: 30 * 60 * 1000,
  });

  // Sin datos suficientes (o si falla) no se muestra nada: es una sección complementaria.
  const first = data?.[0];
  if (isError || !data || !first) return null;

  const period = fmtPeriod(first.indec_period);

  return (
    <div className="card" style={{ padding: 22, marginBottom: 22 }}>
      <h2>Tus supermercados vs. el precio promedio del INDEC</h2>
      <div className="subtle" style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2, marginBottom: 16 }}>
        Mediana de los productos equivalentes con precio de las últimas 72 hs, llevada al mismo tamaño que mide el INDEC · GBA · {period}
      </div>

      <div className="pr-head">
        <div>Producto</div>
        <div>INDEC</div>
        <div>Supermercados</div>
        <div>Diferencia</div>
      </div>
      {data.map((item) => (
        <div key={item.code} className="pr-row">
          <div className="pr-prod">
            <div style={{ fontWeight: 600 }}>{item.label}</div>
            <div className="subtle" style={{ fontSize: 12 }}>por {item.reference_unit}</div>
          </div>
          <div className="pr-indec">
            <div className="pr-mobile-label">INDEC</div>
            <div className="mono" style={{ fontWeight: 600 }}>${fmtPrice(item.indec_price)}</div>
          </div>
          <div className="pr-ours">
            <div className="pr-mobile-label">Supermercados</div>
            <div className="mono" style={{ fontWeight: 600 }}>${fmtPrice(item.ours_median)}</div>
            <div className="subtle" style={{ fontSize: 12 }}>
              mitad central ${fmtPrice(item.ours_p25)}–${fmtPrice(item.ours_p75)} · {item.n_products} productos
            </div>
          </div>
          <div className="pr-diff">
            <VarBadge value={item.diff_pct} />
          </div>
        </div>
      ))}

      <div className="subtle" style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 14 }}>
        Orientativo: el INDEC mide un promedio genérico por artículo y los supermercados venden muchas marcas y tamaños.
        Solo se muestran artículos con al menos 3 ofertas equivalentes. Fuente: INDEC y precios de los supermercados de la app.
      </div>
    </div>
  );
}
