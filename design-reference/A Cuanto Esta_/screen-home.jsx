/* global React */
// Pantalla 1 — Home / Buscador

function ScreenHome({ nav, region, setRegion, supermarket, setSupermarket, setTweak, t }) {
  const { CATEGORIES, SEARCH_SUGGESTIONS, TRENDING, ECONOMIC } = window.ACE_DATA;
  const [query, setQuery] = React.useState("");
  const [focused, setFocused] = React.useState(false);

  const filtered = query
    ? SEARCH_SUGGESTIONS.filter(s => s.q.toLowerCase().includes(query.toLowerCase()))
    : SEARCH_SUGGESTIONS;

  const submit = (q) => {
    nav("search", { query: q || query });
  };

  return (
    <div className="page" data-screen-label="01 Home" style={{ paddingTop: 40 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 40, alignItems: "start" }}>
        {/* LEFT — search + categories */}
        <div>
          {/* Hero */}
          <div style={{ textAlign: "center", marginBottom: 36 }}>
            <div style={{ display: "inline-flex", gap: 6, alignItems: "center", color: "var(--fg-3)", fontSize: 12, marginBottom: 14, padding: "4px 12px", background: "var(--bg-2)", borderRadius: 999, border: "1px solid var(--border)" }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--good)", display: "inline-block" }} />
              Precios actualizados hoy · <span className="mono">{ECONOMIC.asOfDate}</span>
            </div>
            <h1 style={{ fontSize: 44, marginBottom: 8, letterSpacing: "-0.025em" }}>
              ¿A cuánto está?
            </h1>
            <p style={{ color: "var(--fg-2)", fontSize: 16, margin: 0 }}>
              Comparamos <strong className="mono">3.295</strong> productos entre <strong className="mono">9</strong> supermercados de Argentina.
            </p>
          </div>

          {/* Search box */}
          <div style={{ position: "relative", marginBottom: 32 }}>
            <div className="search lg">
              <span className="search-icon"><Icon.search width="22" height="22"/></span>
              <input
                placeholder='Buscá un producto, marca o código de barras…'
                value={query}
                onFocus={() => setFocused(true)}
                onBlur={() => setTimeout(() => setFocused(false), 150)}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") submit(); }}
              />
              <button className="btn"
                style={{ position: "absolute", right: 8, top: 8, padding: "12px 18px" }}
                onClick={() => submit()}>
                Buscar
                <Icon.arrowR />
              </button>
            </div>

            {/* autocomplete */}
            {focused && (
              <div style={{
                position: "absolute", top: "calc(100% + 6px)", left: 0, right: 0,
                background: "var(--surface)", border: "1px solid var(--border)",
                borderRadius: "var(--r-lg)", boxShadow: "var(--shadow-pop)",
                overflow: "hidden", zIndex: 10,
              }}>
                <div style={{ padding: "10px 16px", fontSize: 11, color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, borderBottom: "1px solid var(--border)" }}>
                  Sugerencias
                </div>
                {filtered.slice(0, 6).map((s, i) => (
                  <button key={s.q}
                    onMouseDown={(e) => { e.preventDefault(); submit(s.q); }}
                    style={{
                      display: "flex", width: "100%", alignItems: "center", gap: 12,
                      padding: "11px 16px", background: "none", border: 0, textAlign: "left",
                      borderTop: i ? "1px solid var(--border)" : 0,
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = "var(--bg-2)"}
                    onMouseLeave={e => e.currentTarget.style.background = "none"}
                  >
                    <Icon.search style={{ color: "var(--fg-3)" }} />
                    <span style={{ flex: 1, fontSize: 14 }}>{s.q}</span>
                    <span className="badge outlined">{s.cat}</span>
                    <span className="mono" style={{ fontSize: 11, color: "var(--fg-3)" }}>{s.hint}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Trending */}
          <div style={{ display: "flex", gap: 8, marginBottom: 48, flexWrap: "wrap", alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginRight: 4 }}>
              <Icon.trend style={{ verticalAlign: -2, marginRight: 4 }}/>
              Tendencias
            </span>
            {TRENDING.map(t => (
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
            <span className="subtle"><span className="mono">12</span> categorías · <span className="mono">3.295</span> productos</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
            {CATEGORIES.map(c => (
              <button key={c.id} className="card"
                onClick={() => submit(c.name)}
                style={{
                  display: "flex", alignItems: "center", gap: 12,
                  padding: "12px 14px",
                  background: "var(--surface)", border: "1px solid var(--border)",
                  borderRadius: "var(--r-lg)", textAlign: "left", cursor: "pointer",
                  transition: "border-color .15s, box-shadow .15s",
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--border-strong)"; e.currentTarget.style.boxShadow = "var(--shadow-2)"; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.boxShadow = "var(--shadow-1)"; }}
              >
                <div style={{ flexShrink: 0 }}>
                  {window.CatIcon && <window.CatIcon id={c.id} size={64}/>}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 600, lineHeight: 1.3 }}>{c.name}</div>
                  <div style={{ fontSize: 11.5, color: "var(--fg-3)", marginTop: 2 }}>{c.count} productos</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* RIGHT — economic widgets */}
        <div className="col" style={{ gap: 16 }}>
          {/* Indicadores económicos */}
          <div className="card" style={{ padding: 18 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
              <h3 style={{ fontSize: 13 }}>Hoy en Argentina</h3>
              <button className="btn ghost" style={{ fontSize: 11.5 }} onClick={() => nav("dashboard")}>
                Ver todo <Icon.arrowR />
              </button>
            </div>

            <EcoMiniCard
              label="Inflación mensual"
              source="INDEC · abril 2026"
              value={<><span className="mono">{(ECONOMIC.inflationMonth * 100).toFixed(1).replace(".",",")}</span><span style={{ fontSize: "0.5em", color: "var(--fg-3)" }}>%</span></>}
              delta={ECONOMIC.inflationMonthDelta}
              deltaLabel="vs. mes anterior"
            />
            <Divider />
            <EcoMiniCard
              label="Dólar blue"
              source="Promedio paralelo"
              value={<><span style={{ fontSize: "0.55em", color: "var(--fg-3)", verticalAlign: "0.4em", marginRight: 2 }}>$</span><span className="mono">{fmtPrice(ECONOMIC.dollarBlue)}</span></>}
              delta={ECONOMIC.dollarBlueDelta}
              deltaLabel="últimas 24 hs"
            />
            <Divider />
            <EcoMiniCard
              label="Dólar oficial"
              source="BCRA"
              value={<><span style={{ fontSize: "0.55em", color: "var(--fg-3)", verticalAlign: "0.4em", marginRight: 2 }}>$</span><span className="mono">{fmtPrice(ECONOMIC.dollarOfficial)}</span></>}
              delta={ECONOMIC.dollarOfficialDelta}
              deltaLabel="últimas 24 hs"
            />
            <Divider />
            <EcoMiniCard
              label="Variación semanal"
              source="Índice A Cuanto Está"
              value={<span className="mono" style={{ color: "var(--bad)" }}>+0,8%</span>}
              delta={0.008}
              deltaLabel="canasta de 3.295 productos"
              hideArrow
            />
          </div>

          {/* Alerta de inflación */}
          <div className="card" style={{
            padding: 16,
            background: "var(--warn-tint)",
            borderColor: "oklch(0.88 0.05 70)",
          }}>
            <div style={{ display: "flex", gap: 10 }}>
              <div style={{
                width: 28, height: 28, borderRadius: 8,
                background: "var(--warn)", color: "white",
                display: "grid", placeItems: "center", flexShrink: 0,
              }}>
                <Icon.alert width="16" height="16"/>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 13.5, color: "oklch(0.35 0.1 60)" }}>
                  Inflación acumulada 2026
                </div>
                <div style={{ marginTop: 8, display: "flex", alignItems: "baseline", gap: 10 }}>
                  <span className="mono" style={{ fontSize: 26, fontWeight: 700, color: "oklch(0.40 0.13 50)" }}>
                    {fmtPct(ECONOMIC.inflationYTD, { sign: false })}
                  </span>
                  <span style={{ fontSize: 11, color: "oklch(0.40 0.05 60)" }}>en lo que va del año</span>
                </div>
                <div style={{ marginTop: 6, fontSize: 11.5, color: "oklch(0.40 0.04 60)", lineHeight: 1.4 }}>
                  Últimos 12 meses: <strong className="mono">{fmtPct(ECONOMIC.inflationLast12, { sign: false })}</strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function EcoMiniCard({ label, source, value, delta, deltaLabel, hideArrow }) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: "var(--fg-2)", fontWeight: 600 }}>{label}</span>
        <span style={{ fontSize: 10.5, color: "var(--fg-4)" }}>{source}</span>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
        <div style={{ fontSize: 26, fontWeight: 700, lineHeight: 1.05 }}>{value}</div>
        {!hideArrow && delta !== undefined && (
          <VarBadge value={delta} />
        )}
      </div>
      {deltaLabel && <div style={{ fontSize: 11, color: "var(--fg-3)", marginTop: 3 }}>{deltaLabel}</div>}
    </div>
  );
}

function Divider() {
  return <div style={{ height: 1, background: "var(--border)", margin: "14px 0" }} />;
}

window.ScreenHome = ScreenHome;

