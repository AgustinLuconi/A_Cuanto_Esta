/* global React, ReactDOM */
const { useState, useEffect } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "deep-blue",
  "density": "comfortable",
  "showInflationLine": true
}/*EDITMODE-END*/;

// Compact tab icons (16px viewBox 24)
const TabIcons = {
  results: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M4 6h16M4 12h10M4 18h7"/></svg>,
  product: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 8l9-5 9 5-9 5z"/><path d="M3 8v8l9 5 9-5V8"/></svg>,
  dashboard: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m3 17 6-6 4 4 8-8"/><path d="M17 7h4v4"/></svg>,
};

const THEMES = {
  "deep-blue": { dataAttr: "", label: "Azul profundo" },
  "forest":    { dataAttr: "forest", label: "Verde oscuro" },
  "ink":       { dataAttr: "ink", label: "Tinta" },
};

function App() {
  // Tweaks (returns [values, setTweak])
  const [t, setTweak] = window.useTweaks ? window.useTweaks(TWEAK_DEFAULTS) : [TWEAK_DEFAULTS, () => {}];

  // App state
  const [route, setRoute] = useState({ name: "home" });
  const [region, setRegion] = useState("AMBA");
  const [supermarket, setSupermarket] = useState("Todos");
  const [query, setQuery] = useState("leche entera");

  // Apply theme
  useEffect(() => {
    const attr = THEMES[t.theme]?.dataAttr;
    if (attr) document.documentElement.setAttribute("data-theme", attr);
    else document.documentElement.removeAttribute("data-theme");
  }, [t.theme]);

  const nav = (name, payload = {}) => {
    if (payload.query) setQuery(payload.query);
    setRoute({ name, ...payload });
    window.scrollTo({ top: 0, behavior: "auto" });
  };

  const tabs = [
    { id: "home",      label: "Buscar",     icon: <Icon.search width="14" height="14"/> },
    { id: "search",    label: "Resultados", icon: <TabIcons.results/> },
    { id: "product",   label: "Producto",   icon: <TabIcons.product/> },
    { id: "dashboard", label: "Economía",   icon: <TabIcons.dashboard/> },
    { id: "map",       label: "Cobertura",  icon: <Icon.pin/> },
  ];

  // Region picker
  const [regionOpen, setRegionOpen] = useState(false);
  const [smOpen, setSmOpen] = useState(false);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand" onClick={() => nav("home")} style={{ cursor: "pointer" }}>
          {window.Logo && <window.Logo size={18}/>}
        </div>

        <nav className="tabs">
          {tabs.map(tb => (
            <button key={tb.id}
              className={"tab " + (route.name === tb.id ? "active" : "")}
              onClick={() => nav(tb.id)}>
              <span className="tab-icon">{tb.icon}</span>
              {tb.label}
            </button>
          ))}
        </nav>

        <div className="topbar-spacer"/>

        <div className="tb-control">
          <Dropdown
            open={regionOpen} setOpen={setRegionOpen}
            label={<><Icon.pin/> Región: <strong>{region}</strong> <Icon.chevron/></>}
            items={["AMBA", "Pampeana", "Centro", "Cuyo", "NOA", "NEA", "Patagonia"]}
            selected={region}
            onSelect={setRegion}
          />
          <Dropdown
            open={smOpen} setOpen={setSmOpen}
            label={<>Supermercados: <strong>{supermarket}</strong> <Icon.chevron/></>}
            items={["Todos", ...window.ACE_DATA.SUPERMARKETS.map(s => s.name)]}
            selected={supermarket}
            onSelect={setSupermarket}
          />
        </div>
      </header>

      {route.name === "home" && (
        <ScreenHome
          nav={nav} region={region} setRegion={setRegion}
          supermarket={supermarket} setSupermarket={setSupermarket}
          setTweak={setTweak} t={t}
        />
      )}
      {route.name === "search" && (
        <ScreenSearch nav={nav} query={query} setQuery={setQuery} region={region}/>
      )}
      {route.name === "product" && (
        <ScreenProduct nav={nav} product={route.product || window.ACE_DATA.PRODUCTS[0]}/>
      )}
      {route.name === "dashboard" && <ScreenDashboard nav={nav}/>}
      {route.name === "map" && <ScreenMap nav={nav}/>}

      {window.TweaksPanel && (
        <window.TweaksPanel title="Tweaks">
          <window.TweakSection title="Apariencia">
            <window.TweakRadio
              label="Color de marca"
              value={t.theme}
              options={[
                { value: "deep-blue", label: "Azul" },
                { value: "forest",    label: "Verde" },
                { value: "ink",       label: "Negro" },
              ]}
              onChange={v => setTweak("theme", v)}
            />
          </window.TweakSection>
          <window.TweakSection title="Datos">
            <window.TweakToggle
              label="Línea de inflación en gráficos"
              checked={t.showInflationLine}
              onChange={v => setTweak("showInflationLine", v)}
            />
          </window.TweakSection>
          <window.TweakSection title="Atajos">
            <window.TweakButton onClick={() => nav("product", { product: window.ACE_DATA.PRODUCTS[0] })}>
              Ver detalle de producto
            </window.TweakButton>
            <window.TweakButton onClick={() => nav("dashboard")}>
              Ver dashboard económico
            </window.TweakButton>
            <window.TweakButton onClick={() => nav("map")}>
              Ver mapa de cobertura
            </window.TweakButton>
          </window.TweakSection>
        </window.TweaksPanel>
      )}
    </div>
  );
}

function Dropdown({ open, setOpen, label, items, selected, onSelect }) {
  return (
    <div style={{ position: "relative" }}>
      <button className="tb-pill" onClick={() => setOpen(!open)} style={{ cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6 }}>
        {label}
      </button>
      {open && (
        <>
          <div style={{ position: "fixed", inset: 0, zIndex: 40 }} onClick={() => setOpen(false)}/>
          <div style={{
            position: "absolute", right: 0, top: "calc(100% + 6px)",
            background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 10, boxShadow: "var(--shadow-pop)",
            minWidth: 180, zIndex: 50, padding: 4,
          }}>
            {items.map(it => (
              <button key={it}
                onClick={() => { onSelect(it); setOpen(false); }}
                style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  width: "100%", padding: "8px 10px",
                  background: selected === it ? "var(--primary-tint)" : "none",
                  border: 0, borderRadius: 6, cursor: "pointer",
                  fontSize: 13, color: selected === it ? "var(--primary)" : "var(--fg)",
                  fontWeight: selected === it ? 600 : 400,
                }}>
                {it}
                {selected === it && <span style={{ color: "var(--primary)", fontSize: 12 }}>✓</span>}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
