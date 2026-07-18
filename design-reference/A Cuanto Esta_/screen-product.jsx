/* global React */
// Pantalla 3 — Detalle de producto

function ScreenProduct({ nav, product }) {
  const { PRODUCT_DETAIL, PRODUCT_COMPARE, SM_BY_ID, ECONOMIC } = window.ACE_DATA;
  const detail = PRODUCT_DETAIL; // pre-baked detail data
  const [range, setRange] = React.useState("6m"); // 1m, 3m, 6m
  // Default: show only the 4 most relevant supermarkets (cheapest + most-common) + inflation
  const DEFAULT_VISIBLE = ["dia", "coto", "carrefour", "jumbo"];
  const [visibleSm, setVisibleSm] = React.useState(new Set(DEFAULT_VISIBLE));

  const rangeWeeks = { "1m": 5, "3m": 13, "6m": 26 }[range];
  const slicedLabels = detail.history.labels.slice(-rangeWeeks);
  const slicedSeries = Object.fromEntries(
    Object.entries(detail.history.series).map(([k, arr]) => [k, arr.slice(-rangeWeeks)])
  );
  const slicedInflation = detail.history.inflation.slice(-rangeWeeks);
  // Normalize inflation so it starts at 1 for the visible window
  const start = slicedInflation[0];
  const normInflation = slicedInflation.map(v => v / start);

  // Calc 6m product change vs inflation
  const minPrices = Object.values(detail.history.series).map(arr => arr[0]).reduce((a,b)=>a+b,0) / 9;
  const maxPrices = Object.values(detail.history.series).map(arr => arr[arr.length-1]).reduce((a,b)=>a+b,0) / 9;
  const productChange = (maxPrices - minPrices) / minPrices; // ~ +35%
  const infChange = detail.history.inflation[detail.history.inflation.length-1] - 1;

  const cheapest = [...PRODUCT_COMPARE].sort((a,b)=>a.price-b.price)[0];

  return (
    <div className="page page-wide" data-screen-label="03 Detalle">
      {/* breadcrumb */}
      <div style={{ fontSize: 12, color: "var(--fg-3)", marginBottom: 16 }}>
        <a onClick={() => nav("home")} style={{ cursor: "pointer" }}>Inicio</a>
        <span style={{ margin: "0 6px" }}>›</span>
        <a onClick={() => nav("search", { query: "leche entera" })} style={{ cursor: "pointer" }}>Lácteos</a>
        <span style={{ margin: "0 6px" }}>›</span>
        <span style={{ color: "var(--fg)" }}>{detail.name}</span>
      </div>

      {/* HEADER */}
      <div className="card" style={{ padding: 24, marginBottom: 20 }}>
        <div style={{ display: "grid", gridTemplateColumns: "160px 1fr 280px", gap: 28, alignItems: "center" }}>
          <ImagePlaceholder w={160} h={160} label="sachet 1L" radius={14}/>

          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <span className="badge outlined">Lácteos</span>
              <span className="badge outlined">Sachet 1L</span>
              <span style={{ fontSize: 12, color: "var(--fg-3)", display: "flex", alignItems: "center", gap: 6 }}>
                <Icon.barcode/> <span className="mono">{detail.barcode}</span>
              </span>
            </div>
            <h1 style={{ fontSize: 30, marginBottom: 4 }}>{detail.name}</h1>
            <div style={{ color: "var(--fg-2)", fontSize: 15, marginBottom: 14 }}>
              <strong>{detail.brand}</strong> · {detail.description}
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn secondary">
                <Icon.bookmark/> Guardar producto
              </button>
              <button className="btn secondary">
                <Icon.alert/> Alerta de precio
              </button>
            </div>
          </div>

          {/* Cheapest summary */}
          <div style={{
            background: "var(--good-tint)",
            border: "1px solid oklch(0.85 0.07 150)",
            borderRadius: 12, padding: 18,
          }}>
            <div style={{ fontSize: 10.5, color: "var(--good)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>
              Más barato hoy
            </div>
            <Price value={cheapest.price} size="xl"/>
            <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
              <SMSwatch sm={cheapest.sm}/>
              <strong>{SM_BY_ID[cheapest.sm].name}</strong>
            </div>
            <div style={{ marginTop: 8, fontSize: 11.5, color: "oklch(0.40 0.05 150)" }}>
              Ahorrás hasta <strong className="mono">${fmtPrice(PRODUCT_COMPARE[PRODUCT_COMPARE.length-1].price - cheapest.price)}</strong> vs. el más caro
            </div>
          </div>
        </div>
      </div>

      {/* CONTEXT CALLOUT — inflation comparison */}
      <ContextCallout productChange={productChange} infChange={infChange}/>

      {/* COMPARE TABLE */}
      <div className="card" style={{ padding: 0, marginBottom: 20, overflow: "hidden" }}>
        <div style={{ padding: "18px 22px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2>Comparación entre supermercados</h2>
            <div style={{ color: "var(--fg-3)", fontSize: 12.5, marginTop: 2 }}>
              Precio actual · Variación 30 días · Cobertura geográfica
            </div>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <span className="chip active">Todos (9)</span>
            <span className="chip">Disponibles (9)</span>
            <span className="chip">No disponibles (0)</span>
          </div>
        </div>
        <table className="compare">
          <thead>
            <tr>
              <th style={{ width: 40 }}>#</th>
              <th>Supermercado</th>
              <th>Precio actual</th>
              <th>Variación 30d</th>
              <th>Variación 7d</th>
              <th>Tendencia</th>
              <th>Disponible en</th>
              <th>vs. más barato</th>
            </tr>
          </thead>
          <tbody>
            {PRODUCT_COMPARE.map((row, i) => {
              const sm = SM_BY_ID[row.sm];
              const isCheap = i === 0;
              const diff = row.price - cheapest.price;
              const series = detail.history.series[row.sm];
              const spark = series ? series.slice(-13) : [];
              return (
                <tr key={row.sm} className={isCheap ? "cheapest" : ""}>
                  <td>
                    <span className="mono" style={{ fontSize: 12, color: "var(--fg-3)" }}>{i+1}</span>
                  </td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <SMSwatch sm={row.sm} size="lg"/>
                      <div>
                        <div style={{ fontWeight: 600 }}>{sm.name}</div>
                        <div className="subtle">{sm.coverage}</div>
                      </div>
                      {isCheap && <span className="badge cheapest" style={{ marginLeft: 4 }}>Más barato</span>}
                    </div>
                  </td>
                  <td><Price value={row.price} size="md"/></td>
                  <td><VarBadge value={row.var30}/></td>
                  <td><VarBadge value={row.var7}/></td>
                  <td style={{ width: 110 }}>
                    <Sparkline data={spark} color={row.var30 > 0 ? "var(--bad)" : "var(--good)"} width={100} height={26}/>
                  </td>
                  <td><span className="subtle" style={{ fontSize: 12.5, color: "var(--fg-2)" }}>{row.available}</span></td>
                  <td>
                    {diff === 0
                      ? <span className="mono" style={{ color: "var(--good)", fontWeight: 600, fontSize: 12.5 }}>—</span>
                      : <span className="mono" style={{ color: "var(--bad)", fontSize: 12.5 }}>+${fmtPrice(diff)}</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* CHART */}
      <div className="card" style={{ padding: 22, marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20, flexWrap: "wrap", gap: 14 }}>
          <div>
            <h2>Evolución del precio</h2>
            <div style={{ color: "var(--fg-3)", fontSize: 12.5, marginTop: 2 }}>
              Una línea por supermercado · línea punteada = inflación acumulada del período
            </div>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {[
              { id: "1m", label: "1 mes" },
              { id: "3m", label: "3 meses" },
              { id: "6m", label: "6 meses" },
            ].map(o => (
              <button key={o.id} className={"chip" + (range === o.id ? " active" : "")}
                onClick={() => setRange(o.id)}>{o.label}</button>
            ))}
          </div>
        </div>

        <MultiLineChart
          labels={slicedLabels}
          series={Object.fromEntries(Object.entries(slicedSeries).filter(([k]) => visibleSm.has(k)))}
          inflation={normInflation}
          height={380}
        />

        {/* Legend */}
        <div style={{ marginTop: 16, padding: 14, background: "var(--bg-2)", borderRadius: 10, display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
          <span style={{ fontSize: 11, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginRight: 6 }}>
            Mostrando {visibleSm.size}/9
          </span>
          {Object.keys(slicedSeries).map(k => {
            const sm = SM_BY_ID[k];
            const on = visibleSm.has(k);
            return (
              <button key={k}
                onClick={() => {
                  const n = new Set(visibleSm);
                  on ? n.delete(k) : n.add(k);
                  setVisibleSm(n);
                }}
                style={{
                  display: "flex", alignItems: "center", gap: 7,
                  background: on ? "var(--surface)" : "transparent",
                  border: on ? "1px solid " + sm.color : "1px dashed var(--border-strong)",
                  padding: "5px 10px", borderRadius: 999,
                  cursor: "pointer",
                  opacity: on ? 1 : 0.55,
                  transition: "opacity .15s, background .15s",
                }}>
                <span style={{ width: 14, height: 3, background: sm.color, borderRadius: 2, opacity: on ? 1 : 0.4 }}/>
                <span style={{ fontSize: 12, fontWeight: 600, color: on ? "var(--fg)" : "var(--fg-3)" }}>{sm.name}</span>
              </button>
            );
          })}
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 7,
            padding: "5px 10px", background: "var(--warn-tint)", borderRadius: 999, border: "1px solid oklch(0.85 0.07 70)" }}>
            <span style={{ width: 18, height: 0, borderTop: "2.5px dashed var(--warn)" }}/>
            <span style={{ fontSize: 12, fontWeight: 600, color: "oklch(0.40 0.12 60)" }}>Inflación acumulada</span>
          </div>
        </div>
      </div>

      {/* MORE INSIGHTS */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        <InsightCard
          label="Diferencia entre extremos"
          value={`$${fmtPrice(PRODUCT_COMPARE[PRODUCT_COMPARE.length-1].price - cheapest.price)}`}
          detail={`${SM_BY_ID[PRODUCT_COMPARE[0].sm].name} vs. ${SM_BY_ID[PRODUCT_COMPARE[PRODUCT_COMPARE.length-1].sm].name}`}
          accent="primary"
        />
        <InsightCard
          label="Precio promedio nacional"
          value={`$${fmtPrice(PRODUCT_COMPARE.reduce((s,r)=>s+r.price,0) / PRODUCT_COMPARE.length)}`}
          detail="promedio entre 9 supermercados"
          accent="neutral"
        />
        <InsightCard
          label="Última actualización"
          value="hace 3 horas"
          detail={`23/05/2026 · 06:15 hs`}
          accent="neutral"
          mono={false}
        />
      </div>
    </div>
  );
}

function ContextCallout({ productChange, infChange }) {
  const aboveInflation = productChange > infChange;
  const diff = productChange - infChange;
  return (
    <div style={{
      padding: 22, borderRadius: 14,
      background: aboveInflation ? "var(--bad-tint)" : "var(--good-tint)",
      border: "1px solid " + (aboveInflation ? "oklch(0.85 0.09 25)" : "oklch(0.85 0.07 150)"),
      marginBottom: 20,
      display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 18, alignItems: "center",
    }}>
      <div style={{
        width: 44, height: 44, borderRadius: 12,
        background: aboveInflation ? "var(--bad)" : "var(--good)",
        color: "white", display: "grid", placeItems: "center",
      }}>
        <Icon.trend width="22" height="22"/>
      </div>
      <div>
        <div style={{ fontSize: 12.5, color: aboveInflation ? "oklch(0.40 0.12 25)" : "oklch(0.40 0.10 150)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>
          Contexto · últimos 6 meses
        </div>
        <div style={{ fontSize: 17, lineHeight: 1.5, color: "var(--fg)" }}>
          Este producto aumentó <strong className="mono" style={{ color: aboveInflation ? "var(--bad)" : "var(--good)" }}>{fmtPct(productChange, { sign: false })}</strong>{" "}
          en 6 meses. La inflación del mismo período fue <strong className="mono">{fmtPct(infChange, { sign: false })}</strong>.
          Aumentó <strong style={{ color: aboveInflation ? "var(--bad)" : "var(--good)" }}>{aboveInflation ? "por encima" : "por debajo"}</strong> de la inflación
          {" "}<span className="mono" style={{ color: aboveInflation ? "var(--bad)" : "var(--good)" }}>
            ({diff >= 0 ? "+" : ""}{(diff*100).toFixed(1).replace(".",",")} pp)
          </span>.
        </div>
      </div>
      <button className="btn secondary">Ver metodología</button>
    </div>
  );
}

function InsightCard({ label, value, detail, accent = "primary" }) {
  return (
    <div className="card" style={{ padding: 18 }}>
      <div style={{ fontSize: 11, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>
        {label}
      </div>
      <div className="mono" style={{ fontSize: 24, fontWeight: 700, color: accent === "primary" ? "var(--primary)" : "var(--fg)" }}>
        {value}
      </div>
      <div style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 4 }}>{detail}</div>
    </div>
  );
}

window.ScreenProduct = ScreenProduct;
