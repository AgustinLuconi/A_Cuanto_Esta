/* global React */
// Pantalla 2 — Resultados de búsqueda

function ScreenSearch({ nav, query, setQuery, region }) {
  const { PRODUCTS, SUPERMARKETS, CATEGORIES, SM_BY_ID } = window.ACE_DATA;
  const [sort, setSort] = React.useState("price");
  const [smFilter, setSmFilter] = React.useState(new Set());
  const [priceRange, setPriceRange] = React.useState([0, 3000]);
  const [selectedCat, setSelectedCat] = React.useState("lacteos");

  const toggleSm = (id) => {
    const next = new Set(smFilter);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSmFilter(next);
  };

  const sorted = React.useMemo(() => {
    const arr = [...PRODUCTS];
    if (sort === "price") arr.sort((a,b) => a.lowest - b.lowest);
    if (sort === "variation") arr.sort((a,b) => b.var30 - a.var30);
    return arr;
  }, [sort]);

  return (
    <div className="page page-wide" data-screen-label="02 Resultados">
      {/* Breadcrumb + query header */}
      <div style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 12, color: "var(--fg-3)", marginBottom: 6 }}>
          <a onClick={() => nav("home")} style={{ cursor: "pointer" }}>Inicio</a>
          <span style={{ margin: "0 6px" }}>›</span>
          <span>Lácteos</span>
          <span style={{ margin: "0 6px" }}>›</span>
          <span style={{ color: "var(--fg)" }}>"{query}"</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 24, justifyContent: "space-between" }}>
          <div>
            <h1 style={{ fontSize: 24 }}>Resultados para "{query}"</h1>
            <div style={{ color: "var(--fg-3)", fontSize: 13, marginTop: 4 }}>
              <span className="mono">{sorted.length}</span> productos · monitoreados en <span className="mono">9</span> supermercados · región <strong>{region}</strong>
            </div>
          </div>

          {/* Search inline */}
          <div className="search" style={{ maxWidth: 380 }}>
            <span className="search-icon"><Icon.search/></span>
            <input value={query} onChange={e => setQuery(e.target.value)} />
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 24, alignItems: "start" }}>
        {/* SIDEBAR FILTERS */}
        <div className="col" style={{ gap: 18, position: "sticky", top: 76 }}>
          <FilterGroup title="Categoría">
            {CATEGORIES.slice(0, 6).map(c => (
              <FilterRow key={c.id}
                selected={selectedCat === c.id}
                onClick={() => setSelectedCat(c.id)}
                label={c.name}
                count={c.count}/>
            ))}
            <button className="btn ghost" style={{ padding: "4px 0", fontSize: 12 }}>Ver todas las categorías</button>
          </FilterGroup>

          <FilterGroup title="Supermercado">
            {SUPERMARKETS.map(s => (
              <label key={s.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "5px 0", cursor: "pointer", fontSize: 13 }}>
                <input type="checkbox" checked={smFilter.has(s.id)} onChange={() => toggleSm(s.id)}
                  style={{ accentColor: "var(--primary)" }}/>
                <SMSwatch sm={s.id}/>
                <span style={{ flex: 1 }}>{s.name}</span>
                <span className="mono" style={{ fontSize: 11, color: "var(--fg-3)" }}>{Math.floor(Math.random() * 5 + 2)}</span>
              </label>
            ))}
          </FilterGroup>

          <FilterGroup title="Rango de precio">
            <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
              <NumberInput value={priceRange[0]} onChange={v => setPriceRange([v, priceRange[1]])} placeholder="Mín"/>
              <NumberInput value={priceRange[1]} onChange={v => setPriceRange([priceRange[0], v])} placeholder="Máx"/>
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <button className="chip" onClick={() => setPriceRange([0, 1500])}>menos de $1.500</button>
              <button className="chip" onClick={() => setPriceRange([1500, 3000])}>$1.500 - $3.000</button>
              <button className="chip" onClick={() => setPriceRange([3000, 99999])}>más de $3.000</button>
            </div>
          </FilterGroup>

          <FilterGroup title="Variación 30 días">
            <FilterRow label="Bajaron de precio" count={4} />
            <FilterRow label="Subieron poco (&lt;5%)" count={18} />
            <FilterRow label="Subieron mucho (&gt;10%)" count={28} />
          </FilterGroup>

          <button className="btn secondary" style={{ width: "100%", justifyContent: "center" }}>
            Limpiar filtros
          </button>
        </div>

        {/* RESULTS */}
        <div className="col" style={{ gap: 16 }}>
          {/* Sort bar */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
            <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
              <span style={{ fontSize: 12, color: "var(--fg-3)", marginRight: 4 }}>Filtros activos:</span>
              <span className="chip active">Lácteos <Icon.close style={{ marginLeft: 2 }}/></span>
              <span className="chip active">{region} <Icon.close style={{ marginLeft: 2 }}/></span>
            </div>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <span style={{ fontSize: 12, color: "var(--fg-3)" }}>Ordenar por</span>
              {[
                { id: "price", label: "Precio" },
                { id: "variation", label: "Variación" },
                { id: "relevance", label: "Relevancia" },
              ].map(o => (
                <button key={o.id} className={"chip" + (sort === o.id ? " active" : "")}
                  onClick={() => setSort(o.id)}>{o.label}</button>
              ))}
            </div>
          </div>

          {/* Highlight cheapest */}
          <CheapestBanner product={sorted[0]} nav={nav}/>

          {/* Product cards */}
          {sorted.slice(1).map(p => (
            <ProductCard key={p.id} product={p} nav={nav}/>
          ))}

          <div style={{ display: "flex", justifyContent: "center", marginTop: 12 }}>
            <button className="btn secondary">Cargar más resultados</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function FilterGroup({ title, children }) {
  return (
    <div className="card" style={{ padding: 16 }}>
      <h4 style={{ marginBottom: 12 }}>{title}</h4>
      <div className="col" style={{ gap: 0 }}>{children}</div>
    </div>
  );
}

function FilterRow({ label, count, selected, onClick }) {
  return (
    <button onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "6px 8px", background: selected ? "var(--primary-tint)" : "transparent",
        border: 0, borderRadius: 6, width: "100%", textAlign: "left",
        cursor: "pointer", color: selected ? "var(--primary)" : "var(--fg)",
        fontWeight: selected ? 600 : 400, fontSize: 13,
      }}>
      <span style={{ flex: 1 }} dangerouslySetInnerHTML={{ __html: label }}/>
      <span className="mono" style={{ fontSize: 11, color: selected ? "var(--primary)" : "var(--fg-3)" }}>{count}</span>
    </button>
  );
}

function NumberInput({ value, onChange, placeholder }) {
  return (
    <div style={{ position: "relative", flex: 1 }}>
      <span style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--fg-3)", fontSize: 12, fontFamily: "var(--font-mono)" }}>$</span>
      <input type="number" value={value || ""} placeholder={placeholder}
        onChange={e => onChange(Number(e.target.value))}
        style={{
          width: "100%", padding: "8px 8px 8px 20px",
          border: "1px solid var(--border)", borderRadius: 6,
          fontSize: 13, fontFamily: "var(--font-mono)",
          background: "var(--surface)",
        }}/>
    </div>
  );
}

function CheapestBanner({ product, nav }) {
  const { SM_BY_ID } = window.ACE_DATA;
  const sm = SM_BY_ID[product.lowestAt];
  return (
    <div onClick={() => nav("product", { product })}
      className="card"
      style={{
        padding: 18,
        background: "linear-gradient(135deg, var(--good-tint) 0%, transparent 65%)",
        borderColor: "oklch(0.85 0.07 150)",
        cursor: "pointer",
        position: "relative",
        overflow: "hidden",
      }}>
      <div style={{ position: "absolute", top: 14, right: 14 }}>
        <span className="badge cheapest">⭐ Más barato</span>
      </div>
      <div style={{ display: "flex", gap: 18 }}>
        <ImagePlaceholder w={110} h={110} label="leche 1L"/>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 11, color: "var(--good)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>
            {product.brand}
          </div>
          <h2 style={{ fontSize: 22, marginBottom: 8 }}>{product.name}</h2>
          <div style={{ display: "flex", alignItems: "baseline", gap: 14, marginBottom: 10 }}>
            <Price value={product.lowest} size="lg"/>
            <VarBadge value={product.var30} period=" / 30d"/>
            <VarBadge value={product.var7} period=" / 7d"/>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 13, color: "var(--fg-2)" }}>
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <SMSwatch sm={product.lowestAt}/>
              en <strong>{sm.name}</strong>
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ display: "inline-block", width: 4, height: 4, borderRadius: "50%", background: "var(--fg-4)" }}/>
              Disponible en <strong className="mono">{product.available}/9</strong> supermercados
            </span>
          </div>
        </div>
        <div style={{ width: 160, display: "flex", flexDirection: "column", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div style={{ width: "100%", textAlign: "right" }}>
            <div style={{ fontSize: 10.5, color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>Últimos 30 días</div>
            <div style={{ width: "100%" }}>
              <Sparkline data={product.spark} color="var(--good)" width={140} height={36}/>
            </div>
          </div>
          <button className="btn" style={{ marginTop: 12 }}>
            Comparar precios
            <Icon.arrowR />
          </button>
        </div>
      </div>
    </div>
  );
}

function ProductCard({ product, nav }) {
  const { SM_BY_ID } = window.ACE_DATA;
  const sm = SM_BY_ID[product.lowestAt];
  return (
    <div className="card"
      style={{ padding: 16, cursor: "pointer", transition: "border-color .15s, transform .15s" }}
      onClick={() => nav("product", { product })}
      onMouseEnter={e => e.currentTarget.style.borderColor = "var(--border-strong)"}
      onMouseLeave={e => e.currentTarget.style.borderColor = "var(--border)"}
    >
      <div style={{ display: "grid", gridTemplateColumns: "80px 1fr 220px 160px", gap: 18, alignItems: "center" }}>
        <ImagePlaceholder w={80} h={80} label={product.brand.toLowerCase()}/>

        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 11, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 3 }}>
            {product.brand}
          </div>
          <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 6 }}>{product.name}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--fg-3)" }}>
            <Icon.barcode/>
            <span className="mono">{product.barcode}</span>
            <span style={{ width: 3, height: 3, borderRadius: "50%", background: "var(--fg-4)" }}/>
            Disponible en <strong className="mono" style={{ color: "var(--fg-2)" }}>{product.available}/9</strong>
          </div>
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 6 }}>
            <Price value={product.lowest} size="lg"/>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--fg-2)" }}>
            más barato en
            <SMSwatch sm={product.lowestAt}/>
            <strong>{sm.name}</strong>
          </div>
        </div>

        <div style={{ textAlign: "right" }}>
          <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", marginBottom: 6 }}>
            <VarBadge value={product.var30} period=" / 30d"/>
          </div>
          <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", marginBottom: 8 }}>
            <VarBadge value={product.var7} period=" / 7d"/>
          </div>
          <div style={{ width: 140, marginLeft: "auto" }}>
            <Sparkline data={product.spark} color={product.var30 > 0 ? "var(--bad)" : "var(--good)"} width={140} height={24}/>
          </div>
        </div>
      </div>
    </div>
  );
}

window.ScreenSearch = ScreenSearch;
