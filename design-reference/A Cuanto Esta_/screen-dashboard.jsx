/* global React */
// Pantalla 4 — Dashboard económico

function ScreenDashboard({ nav }) {
  const { ECONOMIC, INFLATION_12M, DOLLAR_HISTORY, CATEGORIES } = window.ACE_DATA;

  return (
    <div className="page page-wide" data-screen-label="04 Dashboard">
      <div style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1>Dashboard económico</h1>
          <div style={{ color: "var(--fg-3)", fontSize: 13.5, marginTop: 4 }}>
            Indicadores actualizados al <strong className="mono">{ECONOMIC.asOfDate}</strong> · fuente INDEC · BCRA · paralelo
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button className="chip active">Mensual</button>
          <button className="chip">Trimestral</button>
          <button className="chip">Anual</button>
        </div>
      </div>

      {/* TOP CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 22 }}>
        <IndicatorCard
          label="Inflación mensual"
          subtitle="último dato · INDEC"
          value={fmtPct(ECONOMIC.inflationMonth, { sign: false })}
          delta={ECONOMIC.inflationMonthDelta}
          deltaLabel="vs. mes anterior"
          tone="warn"
          spark={INFLATION_12M.slice(-6).map(d => d.v)}
          sparkColor="var(--warn)"
        />
        <IndicatorCard
          label="Dólar blue"
          subtitle="cotización paralelo"
          value={"$" + fmtPrice(ECONOMIC.dollarBlue)}
          delta={ECONOMIC.dollarBlueDelta}
          deltaLabel="últimas 24 hs"
          tone="bad"
          spark={DOLLAR_HISTORY.blue.slice(-12)}
          sparkColor="var(--bad)"
        />
        <IndicatorCard
          label="Dólar oficial"
          subtitle="BCRA · mayorista"
          value={"$" + fmtPrice(ECONOMIC.dollarOfficial)}
          delta={ECONOMIC.dollarOfficialDelta}
          deltaLabel="últimas 24 hs"
          tone="neutral"
          spark={DOLLAR_HISTORY.oficial.slice(-12)}
          sparkColor="var(--primary)"
        />
        <IndicatorCard
          label="Inflación acumulada 2026"
          subtitle="enero - abril"
          value={fmtPct(ECONOMIC.inflationYTD, { sign: false })}
          delta={0.094}
          deltaLabel={fmtPct(ECONOMIC.inflationLast12, { sign: false }) + " últimos 12 meses"}
          tone="warn"
          spark={INFLATION_12M.map(d => d.v)}
          sparkColor="var(--warn)"
          hideArrow
        />
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
            <div style={{ textAlign: "right" }}>
              <div className="mono" style={{ fontSize: 22, fontWeight: 700, color: "var(--warn)" }}>3,1%</div>
              <div className="subtle">mayo 2026</div>
            </div>
          </div>
          <BarChart data={INFLATION_12M} color="oklch(0.78 0.10 70)" height={260}/>
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
              <LegendDot color="var(--bad)" label="Blue"/>
              <LegendDot color="var(--primary)" label="Oficial"/>
            </div>
          </div>
          <DualLineChart
            labels={DOLLAR_HISTORY.labels}
            a={DOLLAR_HISTORY.blue}
            b={DOLLAR_HISTORY.oficial}
            aLabel="Blue" bLabel="Oficial"
            aColor="var(--bad)" bColor="var(--primary)"
            height={260}
          />
        </div>
      </div>

      {/* ACE INDEX HERO */}
      <div className="card" style={{ padding: 24, marginBottom: 22, background: "var(--surface)" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 24, alignItems: "center" }}>
          <div>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "var(--primary-tint)", color: "var(--primary)", padding: "4px 10px", borderRadius: 999, fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 12 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--primary)" }}/>
              Índice A Cuanto Está
            </div>
            <h2 style={{ fontSize: 22, marginBottom: 10 }}>
              Los precios monitoreados aumentaron <span className="mono" style={{ color: "var(--bad)" }}>{fmtPct(ECONOMIC.productIndex, { sign: false })}</span> en 12 meses.
            </h2>
            <p style={{ color: "var(--fg-2)", fontSize: 14.5, lineHeight: 1.55, margin: 0, maxWidth: 720 }}>
              La canasta promedio de <strong className="mono">3.295</strong> productos monitoreados está {" "}
              <strong style={{ color: "var(--bad)" }}>{(ECONOMIC.productIndexDelta*100).toFixed(1).replace(".",",")} puntos por encima</strong>{" "}
              de la inflación oficial de los últimos 12 meses ({fmtPct(ECONOMIC.inflationLast12, { sign: false })}). Categorías con mayor aumento: <strong>aceites y grasas</strong>, <strong>panificados</strong>, <strong>lácteos</strong>.
            </p>
          </div>

          {/* big stat */}
          <div style={{
            background: "var(--bg-2)", borderRadius: 14, padding: 18,
            border: "1px solid var(--border)",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 14 }}>
              <span style={{ fontSize: 11, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>ACE 12m</span>
              <span style={{ fontSize: 11, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>IPC 12m</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
              <div className="mono" style={{ fontSize: 32, fontWeight: 700, color: "var(--bad)" }}>+{(ECONOMIC.productIndex*100).toFixed(1).replace(".",",")}%</div>
              <div className="mono" style={{ fontSize: 22, fontWeight: 700, color: "var(--fg-2)" }}>+{(ECONOMIC.inflationLast12*100).toFixed(1).replace(".",",")}%</div>
            </div>
            <div style={{ height: 8, background: "var(--bg)", borderRadius: 4, overflow: "hidden", display: "flex" }}>
              <div style={{ flex: ECONOMIC.productIndex, background: "var(--bad)" }}/>
              <div style={{ width: 2 }}/>
              <div style={{ flex: ECONOMIC.inflationLast12, background: "var(--primary)" }}/>
            </div>
            <div style={{ fontSize: 11.5, color: "var(--fg-3)", marginTop: 10 }}>
              Diferencial: <strong className="mono" style={{ color: "var(--bad)" }}>+{(ECONOMIC.productIndexDelta*100).toFixed(1).replace(".",",")} pp</strong>
            </div>
          </div>
        </div>
      </div>

      {/* CATEGORY BREAKDOWN */}
      <div className="card" style={{ padding: 22 }}>
        <div className="section-head">
          <div>
            <h2>Variación por categoría (12 meses)</h2>
            <div className="subtle" style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2 }}>
              Promedio ponderado por relevancia de canasta básica
            </div>
          </div>
          <button className="btn ghost">Ver metodología <Icon.arrowR/></button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "10px 32px" }}>
          {[
            { cat: "Aceites y grasas",   pct: 0.612 },
            { cat: "Panificados",         pct: 0.488 },
            { cat: "Lácteos",             pct: 0.401 },
            { cat: "Almacén",             pct: 0.385 },
            { cat: "Higiene personal",    pct: 0.358 },
            { cat: "Limpieza",            pct: 0.341 },
            { cat: "Bebidas",             pct: 0.297 },
            { cat: "Snacks",              pct: 0.281 },
            { cat: "Carnes",              pct: 0.267 },
            { cat: "Frutas y verduras",   pct: 0.244 },
            { cat: "Congelados",          pct: 0.223 },
            { cat: "Mascotas",            pct: 0.198 },
          ].map(({cat, pct}) => {
            const aboveIPC = pct > ECONOMIC.inflationLast12;
            const max = 0.65;
            return (
              <div key={cat} style={{ padding: "8px 0", borderTop: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 500 }}>{cat}</span>
                  <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: aboveIPC ? "var(--bad)" : "var(--good)" }}>
                    +{(pct*100).toFixed(1).replace(".",",")}%
                  </span>
                </div>
                <div style={{ position: "relative", height: 6, background: "var(--bg-2)", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${(pct/max)*100}%`, background: aboveIPC ? "var(--bad)" : "var(--good)" }}/>
                  {/* inflation marker */}
                  <div title="IPC 12m" style={{ position: "absolute", left: `${(ECONOMIC.inflationLast12/max)*100}%`, top: -3, bottom: -3, width: 2, background: "var(--warn)" }}/>
                </div>
              </div>
            );
          })}
        </div>

        <div style={{ marginTop: 18, padding: 12, background: "var(--bg-2)", borderRadius: 8, display: "flex", gap: 18, fontSize: 12, color: "var(--fg-2)", flexWrap: "wrap" }}>
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ width: 12, height: 6, background: "var(--bad)", borderRadius: 2 }}/> Por encima del IPC</span>
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ width: 12, height: 6, background: "var(--good)", borderRadius: 2 }}/> Por debajo del IPC</span>
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ width: 2, height: 12, background: "var(--warn)" }}/> IPC 12 meses: {fmtPct(ECONOMIC.inflationLast12, { sign: false })}</span>
        </div>
      </div>
    </div>
  );
}

function IndicatorCard({ label, subtitle, value, delta, deltaLabel, tone, spark, sparkColor, hideArrow }) {
  return (
    <div className="card" style={{ padding: 18, display: "flex", flexDirection: "column", gap: 12 }}>
      <div>
        <div style={{ fontSize: 11.5, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</div>
        <div style={{ fontSize: 11, color: "var(--fg-4)", marginTop: 2 }}>{subtitle}</div>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
        <div className="mono" style={{ fontSize: 30, fontWeight: 700, letterSpacing: "-0.02em" }}>{value}</div>
        {!hideArrow && delta !== undefined && <VarBadge value={delta}/>}
      </div>
      {deltaLabel && <div style={{ fontSize: 11.5, color: "var(--fg-3)", marginTop: -6 }}>{deltaLabel}</div>}
      {spark && <Sparkline data={spark} color={sparkColor} height={36}/>}
    </div>
  );
}

function LegendDot({ color, label }) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--fg-2)" }}>
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: color }}/>
      {label}
    </span>
  );
}

window.ScreenDashboard = ScreenDashboard;
