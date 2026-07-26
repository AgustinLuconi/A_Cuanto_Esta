"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueries } from "@tanstack/react-query";
import Link from "next/link";
import { getProductCount, getEconomicContext } from "@/lib/api";
import { CATEGORIES_DESIGN } from "@/lib/categoryMap";
import { CatIcon } from "@/components/design/icons";
import { VarBadge, fmtPrice, fmtPct, Icon } from "@/components/design/components";
import type { EconomicContext } from "@/types";

const TRENDING = [
  { q: "Aceite girasol",    change: 0.185,  dir: "up"   },
  { q: "Leche entera",      change: -0.032, dir: "down" },
  { q: "Yerba mate",        change: 0.074,  dir: "up"   },
  { q: "Arroz largo",       change: 0.091,  dir: "up"   },
  { q: "Pan lactal",        change: 0.052,  dir: "up"   },
  { q: "Fideos spaghetti",  change: -0.018, dir: "down" },
];

function parseEco(eco: EconomicContext) {
  return {
    inflationMonth:       eco.inflation_monthly != null ? parseFloat(String(eco.inflation_monthly)) / 100  : null,
    inflationMonthChange: eco.inflation_monthly_change != null ? parseFloat(String(eco.inflation_monthly_change)) / 100 : null,
    inflationYearly:      eco.inflation_yearly  != null ? parseFloat(String(eco.inflation_yearly)) / 100   : null,
    inflationYTD:         eco.inflation_ytd     != null ? parseFloat(String(eco.inflation_ytd)) / 100      : null,
    dollarBlue:           eco.dollar_blue       != null ? parseFloat(String(eco.dollar_blue))        : null,
    dollarBlueChange:     eco.dollar_blue_change != null ? parseFloat(String(eco.dollar_blue_change)) / 100 : null,
    dollarOficial:        eco.dollar_oficial    != null ? parseFloat(String(eco.dollar_oficial))     : null,
    dollarOficialChange:  eco.dollar_oficial_change != null ? parseFloat(String(eco.dollar_oficial_change)) / 100 : null,
    riskCountry:          eco.risk_country      != null ? parseFloat(String(eco.risk_country))       : null,
    riskCountryChange:    eco.risk_country_change != null ? parseFloat(String(eco.risk_country_change)) / 100 : null,
    asOfDate:             eco.last_updated
      ? new Date(eco.last_updated).toLocaleDateString("es-AR", { day: "numeric", month: "long", year: "numeric" })
      : "–",
  };
}

export default function Home() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);

  const { data: ecoData } = useQuery({
    queryKey: ["economic"],
    queryFn: getEconomicContext,
    staleTime: 5 * 60 * 1000,
  });

  const { data: countData } = useQuery({
    queryKey: ["productCount"],
    queryFn: () => getProductCount(),
    staleTime: 10 * 60 * 1000,
  });

  const categoryQueries = useQueries({
    queries: CATEGORIES_DESIGN.map((cat) => ({
      queryKey: ["productCount", cat.id],
      queryFn: () => getProductCount(cat.backendId),
      staleTime: 10 * 60 * 1000,
    })),
  });

  const totalCount = countData?.count ?? null;
  const eco = ecoData ? parseEco(ecoData) : null;

  const submit = (q?: string) => {
    const term = q ?? query;
    if (term.trim()) router.push(`/resultados?q=${encodeURIComponent(term.trim())}`);
  };

  return (
    <div className="page" style={{ paddingTop: 40 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 40, alignItems: "start" }}>

        {/* LEFT — search + categories */}
        <div>
          {/* Hero */}
          <div style={{ textAlign: "center", marginBottom: 36 }}>
            <div style={{ display: "inline-flex", gap: 6, alignItems: "center", color: "var(--fg-3)", fontSize: 12, marginBottom: 14, padding: "4px 12px", background: "var(--bg-2)", borderRadius: 999, border: "1px solid var(--border)" }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--good)", display: "inline-block" }} />
              Precios actualizados hoy
              {eco?.asOfDate && <> · <span className="mono">{eco.asOfDate}</span></>}
            </div>
            <h1 style={{ fontSize: 44, marginBottom: 8, letterSpacing: "-0.025em" }}>
              ¿A cuánto está?
            </h1>
            <p style={{ color: "var(--fg-2)", fontSize: 16, margin: 0 }}>
              Comparamos{" "}
              <strong className="mono">
                {totalCount !== null ? totalCount.toLocaleString("es-AR") : "miles de"}
              </strong>{" "}
              productos entre <strong className="mono">9</strong> supermercados de Argentina.
            </p>
          </div>

          {/* Search box */}
          <div style={{ position: "relative", marginBottom: 32 }}>
            <div className="search lg">
              <span className="search-icon"><Icon.search width={22} height={22} /></span>
              <input
                placeholder="Buscá un producto, marca o código de barras…"
                value={query}
                onFocus={() => setFocused(true)}
                onBlur={() => setTimeout(() => setFocused(false), 150)}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
              />
              <button
                className="btn"
                style={{ position: "absolute", right: 8, top: 8, padding: "12px 18px" }}
                onClick={() => submit()}
              >
                Buscar <Icon.arrowR />
              </button>
            </div>

            {/* Dropdown de tendencias al enfocar vacío */}
            {focused && !query && (
              <div style={{
                position: "absolute", top: "calc(100% + 6px)", left: 0, right: 0,
                background: "var(--surface)", border: "1px solid var(--border)",
                borderRadius: "var(--r-lg)", boxShadow: "var(--shadow-pop)",
                overflow: "hidden", zIndex: 10,
              }}>
                <div style={{ padding: "10px 16px", fontSize: 11, color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, borderBottom: "1px solid var(--border)" }}>
                  Tendencias
                </div>
                {TRENDING.map((t, i) => (
                  <button key={t.q}
                    onMouseDown={(e) => { e.preventDefault(); submit(t.q); }}
                    style={{
                      display: "flex", width: "100%", alignItems: "center", gap: 12,
                      padding: "11px 16px", background: "none", border: 0, textAlign: "left",
                      borderTop: i ? "1px solid var(--border)" : "0", cursor: "pointer",
                    }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--bg-2)"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "none"; }}
                  >
                    <Icon.search style={{ color: "var(--fg-3)" }} />
                    <span style={{ flex: 1, fontSize: 14 }}>{t.q}</span>
                    <span style={{ color: t.dir === "up" ? "var(--bad)" : "var(--good)", fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600 }}>
                      {fmtPct(t.change)}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Trending chips */}
          <div style={{ display: "flex", gap: 8, marginBottom: 48, flexWrap: "wrap", alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginRight: 4 }}>
              <Icon.trend style={{ verticalAlign: -2, marginRight: 4 }} />
              Tendencias
            </span>
            {TRENDING.map((t) => (
              <button key={t.q} className="chip" onClick={() => submit(t.q)}>
                {t.q}
                <span style={{ color: t.dir === "up" ? "var(--bad)" : "var(--good)", fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600 }}>
                  {fmtPct(t.change)}
                </span>
              </button>
            ))}
          </div>

          {/* Categories grid */}
          <div className="section-head">
            <h2>Explorar por categoría</h2>
            <span className="subtle">
              <span className="mono">12</span> categorías
              {totalCount !== null && (
                <> · <span className="mono">{totalCount.toLocaleString("es-AR")}</span> productos</>
              )}
            </span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
            {CATEGORIES_DESIGN.map((cat, i) => {
              const count = categoryQueries[i]?.data?.count;
              return (
                <button key={cat.id} className="card"
                  onClick={() => router.push(`/resultados?categoria=${cat.id}`)}
                  style={{
                    display: "flex", alignItems: "center", gap: 12,
                    padding: "12px 14px", background: "var(--surface)", border: "1px solid var(--border)",
                    borderRadius: "var(--r-lg)", textAlign: "left", cursor: "pointer",
                    transition: "border-color .15s, box-shadow .15s",
                  }}
                  onMouseEnter={(e) => { const el = e.currentTarget; el.style.borderColor = "var(--border-strong)"; el.style.boxShadow = "var(--shadow-2)"; }}
                  onMouseLeave={(e) => { const el = e.currentTarget; el.style.borderColor = "var(--border)"; el.style.boxShadow = "var(--shadow-1)"; }}
                >
                  <div style={{ flexShrink: 0 }}>
                    <CatIcon id={cat.id} size={64} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13.5, fontWeight: 600, lineHeight: 1.3 }}>{cat.name}</div>
                    <div style={{ fontSize: 11.5, color: "var(--fg-3)", marginTop: 2 }}>
                      {count != null ? `${count.toLocaleString("es-AR")} productos` : "Cargando…"}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* RIGHT — economic sidebar */}
        <div className="col" style={{ gap: 16 }}>
          <div className="card" style={{ padding: 18 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
              <h3 style={{ fontSize: 13 }}>Hoy en Argentina</h3>
              <Link href="/economia" className="btn ghost" style={{ fontSize: 11.5 }}>
                Ver todo <Icon.arrowR />
              </Link>
            </div>

            {eco ? (
              <>
                {eco.inflationMonth != null && (
                  <>
                    <EcoMiniCard
                      label="Inflación mensual"
                      source="INDEC · último dato"
                      value={
                        <><span className="mono">{(eco.inflationMonth * 100).toFixed(1).replace(".", ",")}</span>
                        <span style={{ fontSize: "0.5em", color: "var(--fg-3)" }}>%</span></>
                      }
                      delta={eco.inflationMonthChange}
                      deltaLabel="vs. mes anterior"
                    />
                    <Divider />
                  </>
                )}
                {eco.dollarBlue != null && (
                  <>
                    <EcoMiniCard
                      label="Dólar blue"
                      source="Promedio paralelo"
                      value={
                        <><span style={{ fontSize: "0.55em", color: "var(--fg-3)", verticalAlign: "0.4em", marginRight: 2 }}>$</span>
                        <span className="mono">{fmtPrice(eco.dollarBlue)}</span></>
                      }
                      delta={eco.dollarBlueChange}
                      deltaLabel="últimas 24 hs"
                    />
                    <Divider />
                  </>
                )}
                {eco.dollarOficial != null && (
                  <>
                    <EcoMiniCard
                      label="Dólar oficial"
                      source="BCRA"
                      value={
                        <><span style={{ fontSize: "0.55em", color: "var(--fg-3)", verticalAlign: "0.4em", marginRight: 2 }}>$</span>
                        <span className="mono">{fmtPrice(eco.dollarOficial)}</span></>
                      }
                      delta={eco.dollarOficialChange}
                      deltaLabel="últimas 24 hs"
                    />
                    <Divider />
                    <EcoMiniCard
                      label="Variación semanal"
                      source="Índice A Cuanto Está"
                      value={<span className="mono" style={{ color: "var(--bad)" }}>+0,8%</span>}
                      delta={0.008}
                      deltaLabel={`canasta de ${totalCount !== null ? totalCount.toLocaleString("es-AR") : "3.295"} productos`}
                      hideArrow
                    />
                  </>
                )}
                {eco.riskCountry != null && (
                  <>
                    <Divider />
                    <EcoMiniCard
                      label="Riesgo país"
                      source="JP Morgan EMBI+"
                      value={
                        <><span className="mono">{fmtPrice(eco.riskCountry)}</span>
                        <span style={{ fontSize: "0.5em", color: "var(--fg-3)", marginLeft: 4 }}>pb</span></>
                      }
                      delta={eco.riskCountryChange}
                      deltaLabel="últimas 24 hs"
                    />
                  </>
                )}
              </>
            ) : (
              <div style={{ color: "var(--fg-4)", fontSize: 13, textAlign: "center", padding: "16px 0" }}>
                Cargando indicadores…
              </div>
            )}
          </div>

          {eco?.inflationYTD != null && (
            <div className="card" style={{ padding: 16, background: "var(--warn-tint)", borderColor: "oklch(0.88 0.05 70)" }}>
              <div style={{ display: "flex", gap: 10 }}>
                <div style={{ width: 28, height: 28, borderRadius: 8, background: "var(--warn)", color: "white", display: "grid", placeItems: "center", flexShrink: 0 }}>
                  <Icon.alert width={16} height={16} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 13.5, color: "oklch(0.35 0.1 60)" }}>
                    Inflación acumulada {new Date().getFullYear()}
                  </div>
                  <div style={{ marginTop: 8, display: "flex", alignItems: "baseline", gap: 10 }}>
                    <span className="mono" style={{ fontSize: 26, fontWeight: 700, color: "oklch(0.40 0.13 50)" }}>
                      {fmtPct(eco.inflationYTD, { sign: false })}
                    </span>
                    <span style={{ fontSize: 11, color: "oklch(0.40 0.05 60)" }}>en lo que va del año</span>
                  </div>
                  <div style={{ marginTop: 6, fontSize: 11.5, color: "oklch(0.40 0.04 60)", lineHeight: 1.4 }}>
                    Últimos 12 meses: <strong className="mono">{eco.inflationYearly != null ? fmtPct(eco.inflationYearly, { sign: false }) : "– %"}</strong>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EcoMiniCard({ label, source, value, delta, deltaLabel, hideArrow }: {
  label: string;
  source: string;
  value: React.ReactNode;
  delta?: number | null;
  deltaLabel?: string;
  hideArrow?: boolean;
}) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: "var(--fg-2)", fontWeight: 600 }}>{label}</span>
        <span style={{ fontSize: 10.5, color: "var(--fg-4)" }}>{source}</span>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
        <div style={{ fontSize: 26, fontWeight: 700, lineHeight: 1.05 }}>{value}</div>
        {!hideArrow && delta != null && <VarBadge value={delta} />}
      </div>
      {deltaLabel && <div style={{ fontSize: 11, color: "var(--fg-3)", marginTop: 3 }}>{deltaLabel}</div>}
    </div>
  );
}

function Divider() {
  return <div style={{ height: 1, background: "var(--border)", margin: "14px 0" }} />;
}
