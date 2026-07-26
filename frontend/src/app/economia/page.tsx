"use client";

import { useQuery } from "@tanstack/react-query";
import { getEconomicContext, getInflationHistory, getDollarHistory, getRiskCountryHistory } from "@/lib/api";
import { BarChart, DualLineChart, VarBadge, Sparkline, fmtPrice, fmtPct, Icon } from "@/components/design/components";
import { ChangeBadge } from "@/components/layout/EconomicSidebar";

const CATEGORIES_VARIATION = [
  { cat: "Aceites y grasas",  pct: 0.612 },
  { cat: "Panificados",       pct: 0.488 },
  { cat: "Lácteos",           pct: 0.401 },
  { cat: "Almacén",           pct: 0.385 },
  { cat: "Higiene personal",  pct: 0.358 },
  { cat: "Limpieza",          pct: 0.341 },
  { cat: "Bebidas",           pct: 0.297 },
  { cat: "Snacks",            pct: 0.281 },
  { cat: "Carnes",            pct: 0.267 },
  { cat: "Frutas y verduras", pct: 0.244 },
  { cat: "Congelados",        pct: 0.223 },
  { cat: "Mascotas",          pct: 0.198 },
];

export default function EconomiaPage() {
  const { data: eco } = useQuery({
    queryKey: ["economic"],
    queryFn: getEconomicContext,
    staleTime: 5 * 60 * 1000,
  });

  const { data: inflationRaw = [] } = useQuery({
    queryKey: ["inflation12m"],
    queryFn: () => getInflationHistory(12, "monthly"),
    staleTime: 30 * 60 * 1000,
  });

  const { data: dollarHist } = useQuery({
    queryKey: ["dollarHistory"],
    queryFn: () => getDollarHistory(6),
    staleTime: 30 * 60 * 1000,
  });

  const { data: riskCountryRaw = [] } = useQuery({
    queryKey: ["riskCountryHistory"],
    queryFn: () => getRiskCountryHistory(12),
    staleTime: 30 * 60 * 1000,
  });

  // La API ya devuelve estos valores como porcentaje (ej. 1.9 = 1,9%), no como fracción.
  // fmtPct() espera una fracción (multiplica x100 internamente) — hay que normalizar acá,
  // igual que hace parseEco() en app/page.tsx.
  const inflationMonth = eco?.inflation_monthly != null ? parseFloat(String(eco.inflation_monthly)) / 100 : null;
  const inflationYearly = eco?.inflation_yearly != null ? parseFloat(String(eco.inflation_yearly)) / 100 : null;
  const dollarBlue = eco?.dollar_blue != null ? parseFloat(String(eco.dollar_blue)) : null;
  const dollarOficial = eco?.dollar_oficial != null ? parseFloat(String(eco.dollar_oficial)) : null;
  const dollarMayorista = eco?.dollar_mayorista != null ? parseFloat(String(eco.dollar_mayorista)) : null;
  const dollarMep = eco?.dollar_mep != null ? parseFloat(String(eco.dollar_mep)) : null;
  const dollarCcl = eco?.dollar_ccl != null ? parseFloat(String(eco.dollar_ccl)) : null;
  const dollarCripto = eco?.dollar_cripto != null ? parseFloat(String(eco.dollar_cripto)) : null;
  const dollarTarjeta = eco?.dollar_tarjeta != null ? parseFloat(String(eco.dollar_tarjeta)) : null;
  const riskCountry = eco?.risk_country != null ? parseFloat(String(eco.risk_country)) : null;

  // Los campos *_change vienen como string (Decimal serializado) — parsear antes de usarlos
  const parseChange = (v: number | string | null | undefined) =>
    v != null ? parseFloat(String(v)) : null;
  const dollarOficialChange = parseChange(eco?.dollar_oficial_change);
  const dollarBlueChange = parseChange(eco?.dollar_blue_change);
  const dollarMayoristaChange = parseChange(eco?.dollar_mayorista_change);
  const dollarMepChange = parseChange(eco?.dollar_mep_change);
  const dollarCclChange = parseChange(eco?.dollar_ccl_change);
  const dollarCriptoChange = parseChange(eco?.dollar_cripto_change);
  const dollarTarjetaChange = parseChange(eco?.dollar_tarjeta_change);
  const riskCountryChange = parseChange(eco?.risk_country_change);
  const asOfDate = eco?.last_updated
    ? new Date(eco.last_updated).toLocaleDateString("es-AR", { day: "numeric", month: "long", year: "numeric" })
    : "–";

  // Convertir historial a formato BarChart: { m: "Ene", v: 3.1 }
  // r.value ya viene como porcentaje de la API (BarChart no multiplica, a diferencia de fmtPct)
  const inflationBarData = [...inflationRaw]
    .reverse()
    .map((r) => ({
      m: new Date(r.date + "T00:00:00").toLocaleDateString("es-AR", { month: "short" }),
      v: parseFloat(String(r.value)),
    }));

  const dollarLabels = dollarHist?.labels ?? [];
  const dollarBlueArr = dollarHist?.blue ?? [];
  const dollarOficialArr = dollarHist?.oficial ?? [];

  // Riesgo país se actualiza a diario (a diferencia de la inflación, que es mensual) —
  // agregamos a un punto por mes (último valor disponible de cada mes) para que el
  // gráfico tenga la misma granularidad que el resto (~12 barras, no ~300).
  const riskCountryByMonth = new Map<string, { date: string; value: number }>();
  for (const r of [...riskCountryRaw].reverse()) {
    riskCountryByMonth.set(r.date.slice(0, 7), r);
  }
  const riskCountryBarData = Array.from(riskCountryByMonth.values()).map((r) => ({
    m: new Date(r.date + "T00:00:00").toLocaleDateString("es-AR", { month: "short" }),
    v: r.value,
  }));

  const riskCountrySpark = riskCountryBarData.slice(-6).map((d) => d.v);

  // Sparklines para los indicator cards (últimos 6 meses de inflación)
  const inflationSpark = inflationBarData.slice(-6).map((d) => d.v);

  return (
    <div className="page page-wide">
      <div style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1>Dashboard económico</h1>
          <div style={{ color: "var(--fg-3)", fontSize: 13.5, marginTop: 4 }}>
            Indicadores actualizados al <strong className="mono">{asOfDate}</strong> · fuente INDEC · BCRA · paralelo
          </div>
        </div>
      </div>

      {/* TOP CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 16, marginBottom: 22 }}>
        <IndicatorCard
          label="Inflación mensual"
          subtitle="último dato · INDEC"
          value={inflationMonth != null ? fmtPct(inflationMonth, { sign: false }) : "–"}
          tone="warn"
          spark={inflationSpark}
          sparkColor="var(--warn)"
        />
        <IndicatorCard
          label="Dólar blue"
          subtitle="cotización paralelo"
          value={dollarBlue != null ? "$" + fmtPrice(dollarBlue) : "–"}
          tone="bad"
          spark={dollarBlueArr.slice(-12)}
          sparkColor="var(--bad)"
        />
        <IndicatorCard
          label="Dólar oficial"
          subtitle="BCRA · mayorista"
          value={dollarOficial != null ? "$" + fmtPrice(dollarOficial) : "–"}
          tone="neutral"
          spark={dollarOficialArr.slice(-12)}
          sparkColor="var(--primary)"
        />
        <IndicatorCard
          label="Inflación interanual"
          subtitle="últimos 12 meses"
          value={inflationYearly != null ? fmtPct(inflationYearly, { sign: false }) : "–"}
          tone="warn"
          spark={inflationBarData.map((d) => d.v)}
          sparkColor="var(--warn)"
          hideArrow
        />
        <RiskCountryCard value={riskCountry} change={riskCountryChange} spark={riskCountrySpark} />
      </div>

      {/* MAIN CHARTS */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 22 }}>
        {/* Inflación mensual */}
        <div className="card" style={{ padding: 22 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
            <div>
              <h2>Inflación mensual</h2>
              <div className="subtle" style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2 }}>
                Últimos 12 meses · IPC nacional · INDEC
              </div>
            </div>
            {inflationMonth != null && (
              <div style={{ textAlign: "right" }}>
                <div className="mono" style={{ fontSize: 22, fontWeight: 700, color: "var(--warn)" }}>
                  {(inflationMonth * 100).toFixed(1).replace(".", ",")}%
                </div>
                <div className="subtle">último dato</div>
              </div>
            )}
          </div>
          <BarChart data={inflationBarData} color="oklch(0.78 0.10 70)" height={260} />
        </div>

        {/* Dólar */}
        <div className="card" style={{ padding: 22 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 18 }}>
            <div>
              <h2>Cotización del dólar</h2>
              <div className="subtle" style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2 }}>
                Últimos 6 meses · blue vs oficial
              </div>
            </div>
            <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
              <LegendDot color="var(--bad)" label="Blue" />
              <LegendDot color="var(--primary)" label="Oficial" />
            </div>
          </div>
          <DualLineChart
            labels={dollarLabels}
            a={dollarBlueArr}
            b={dollarOficialArr}
            aLabel="Blue" bLabel="Oficial"
            aColor="var(--bad)" bColor="var(--primary)"
            height={260}
          />
        </div>
      </div>

      {/* TODOS LOS DÓLARES */}
      <div className="card" style={{ padding: 22, marginBottom: 22 }}>
        <div className="section-head">
          <div>
            <h2>Todos los dólares</h2>
            <div className="subtle" style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2 }}>
              Cotización de venta · variación vs. registro anterior
            </div>
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginTop: 16 }}>
          <DollarCard label="Oficial" value={dollarOficial} change={dollarOficialChange} />
          <DollarCard label="Blue" value={dollarBlue} change={dollarBlueChange} />
          <DollarCard label="Mayorista" value={dollarMayorista} change={dollarMayoristaChange} />
          <DollarCard label="MEP" value={dollarMep} change={dollarMepChange} />
          <DollarCard label="CCL" value={dollarCcl} change={dollarCclChange} />
          <DollarCard label="Cripto" value={dollarCripto} change={dollarCriptoChange} />
          <DollarCard label="Tarjeta" value={dollarTarjeta} change={dollarTarjetaChange} />
        </div>
      </div>

      {/* RIESGO PAÍS HISTÓRICO */}
      <div className="card" style={{ padding: 22, marginBottom: 22 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
          <div>
            <h2>Riesgo país</h2>
            <div className="subtle" style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2 }}>
              Últimos 12 meses · EMBI+ · JP Morgan
            </div>
          </div>
          {riskCountry != null && (
            <div style={{ textAlign: "right" }}>
              <div className="mono" style={{ fontSize: 22, fontWeight: 700, color: "var(--fg)" }}>
                {fmtPrice(riskCountry)} pb
              </div>
              <div className="subtle">último dato</div>
            </div>
          )}
        </div>
        <BarChart data={riskCountryBarData} color="var(--fg-3)" height={220} valueFmt={(v) => fmtPrice(v) + " pb"} />
      </div>

      {/* CATEGORY BREAKDOWN */}
      <div className="card" style={{ padding: 22 }}>
        <div className="section-head">
          <div>
            <h2>Variación por categoría (12 meses)</h2>
            <div className="subtle" style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2 }}>
              Estimación basada en productos monitoreados
            </div>
          </div>
          <button className="btn ghost">
            Ver metodología <Icon.arrowR />
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "10px 32px" }}>
          {CATEGORIES_VARIATION.map(({ cat, pct }) => {
            const aboveIPC = inflationYearly != null ? pct > inflationYearly : true;
            const max = 0.65;
            const ipcPct = inflationYearly ?? 0.60;
            return (
              <div key={cat} style={{ padding: "8px 0", borderTop: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 500 }}>{cat}</span>
                  <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: aboveIPC ? "var(--bad)" : "var(--good)" }}>
                    +{(pct * 100).toFixed(1).replace(".", ",")}%
                  </span>
                </div>
                <div style={{ position: "relative", height: 6, background: "var(--bg-2)", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${(pct / max) * 100}%`, background: aboveIPC ? "var(--bad)" : "var(--good)" }} />
                  {inflationYearly != null && (
                    <div title={`IPC 12m: ${fmtPct(inflationYearly, { sign: false })}`}
                      style={{ position: "absolute", left: `${(ipcPct / max) * 100}%`, top: -3, bottom: -3, width: 2, background: "var(--warn)" }} />
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div style={{ marginTop: 18, padding: 12, background: "var(--bg-2)", borderRadius: 8, display: "flex", gap: 18, fontSize: 12, color: "var(--fg-2)", flexWrap: "wrap" }}>
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ width: 12, height: 6, background: "var(--bad)", borderRadius: 2 }} />
            Por encima del IPC
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ width: 12, height: 6, background: "var(--good)", borderRadius: 2 }} />
            Por debajo del IPC
          </span>
          {inflationYearly != null && (
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 2, height: 12, background: "var(--warn)" }} />
              IPC 12 meses: {fmtPct(inflationYearly, { sign: false })}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function IndicatorCard({ label, subtitle, value, tone, spark, sparkColor, hideArrow, delta }: {
  label: string;
  subtitle: string;
  value: string;
  tone: "warn" | "bad" | "neutral";
  spark?: number[];
  sparkColor?: string;
  hideArrow?: boolean;
  delta?: number | null;
}) {
  const valueColor = tone === "warn" ? "var(--warn)"
    : tone === "bad" ? "var(--bad)"
    : "var(--fg)";

  return (
    <div className="card" style={{ padding: 18, display: "flex", flexDirection: "column", gap: 12 }}>
      <div>
        <div style={{ fontSize: 11.5, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</div>
        <div style={{ fontSize: 11, color: "var(--fg-4)", marginTop: 2 }}>{subtitle}</div>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
        <div className="mono" style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em", color: valueColor }}>{value}</div>
        {!hideArrow && delta != null && <VarBadge value={delta} />}
      </div>
      {spark && spark.length > 1 && (
        <Sparkline data={spark} color={sparkColor} height={36} />
      )}
    </div>
  );
}

function RiskCountryCard({ value, change, spark }: {
  value: number | null;
  change?: number | null;
  spark: number[];
}) {
  return (
    <div className="card" style={{ padding: 18, display: "flex", flexDirection: "column", gap: 12 }}>
      <div>
        <div style={{ fontSize: 11.5, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Riesgo país
        </div>
        <div style={{ fontSize: 11, color: "var(--fg-4)", marginTop: 2 }}>EMBI+ · JP Morgan</div>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
        <div className="mono" style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em" }}>
          {value != null ? fmtPrice(value) + " pb" : "–"}
        </div>
        <ChangeBadge value={change} />
      </div>
      {spark.length > 1 && <Sparkline data={spark} color="var(--fg-3)" height={36} />}
    </div>
  );
}

function DollarCard({ label, value, change }: {
  label: string;
  value: number | null;
  change?: number | null;
}) {
  return (
    <div style={{ padding: 14, background: "var(--bg-2)", borderRadius: 10, border: "1px solid var(--border)" }}>
      <div style={{ fontSize: 11, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span className="mono" style={{ fontSize: 18, fontWeight: 700 }}>
          {value != null ? "$" + fmtPrice(value) : "–"}
        </span>
        <ChangeBadge value={change} />
      </div>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--fg-2)" }}>
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: color }} />
      {label}
    </span>
  );
}
