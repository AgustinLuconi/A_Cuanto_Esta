"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Icon, SMSwatch, SM_BY_ID } from "@/components/design/components";

const REGIONS = [
  { id: "amba",      name: "AMBA",      provs: ["Buenos Aires (GBA)", "Ciudad de Buenos Aires"] },
  { id: "pampeana",  name: "Pampeana",  provs: ["Buenos Aires (interior)", "Santa Fe", "Entre Ríos", "La Pampa"] },
  { id: "centro",    name: "Centro",    provs: ["Córdoba", "San Luis"] },
  { id: "cuyo",      name: "Cuyo",      provs: ["Mendoza", "San Juan", "San Luis"] },
  { id: "noa",       name: "NOA",       provs: ["Jujuy", "Salta", "Tucumán", "Santiago del Estero", "Catamarca", "La Rioja"] },
  { id: "nea",       name: "NEA",       provs: ["Formosa", "Chaco", "Misiones", "Corrientes"] },
  { id: "patagonia", name: "Patagonia", provs: ["Neuquén", "Río Negro", "Chubut", "Santa Cruz", "Tierra del Fuego"] },
];

const REGION_SM: Record<string, string[]> = {
  amba:      ["coto", "carrefour", "jumbo", "vea", "disco", "dia", "changomas"],
  pampeana:  ["coto", "carrefour", "jumbo", "dia", "changomas"],
  centro:    ["coto", "carrefour", "jumbo", "dia", "changomas"],
  cuyo:      ["atomo", "vea", "carrefour", "jumbo", "changomas"],
  noa:       ["anonima", "carrefour", "changomas", "coto"],
  nea:       ["carrefour", "changomas", "coto"],
  patagonia: ["anonima", "carrefour", "changomas", "jumbo"],
};

const REGION_COV: Record<string, number> = {
  amba: 0.94, pampeana: 0.88, centro: 0.85, cuyo: 0.79,
  noa: 0.66, nea: 0.62, patagonia: 0.71,
};

const TOTAL_PRODUCTS = 3295;

export default function CoberturaPage() {
  const [active, setActive] = useState("amba");
  const router = useRouter();
  const region = REGIONS.find((r) => r.id === active)!;

  return (
    <div className="page page-wide">
      <div style={{ marginBottom: 22 }}>
        <h1>Cobertura geográfica</h1>
        <div style={{ color: "var(--fg-3)", fontSize: 13.5, marginTop: 4 }}>
          <strong className="mono">9</strong> supermercados operan en <strong className="mono">24</strong> provincias agrupadas en <strong className="mono">7</strong> regiones.
          Los precios pueden variar entre regiones por costos de logística y disponibilidad.
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 380px", gap: 24, alignItems: "start" }}>
        {/* MAP */}
        <div className="card" style={{ padding: 28, position: "relative" }}>
          <ArgMap active={active} setActive={setActive} />

          {/* Coverage legend */}
          <div style={{
            position: "absolute", left: 28, bottom: 28,
            background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 10, padding: 12, fontSize: 11.5, color: "var(--fg-2)",
            display: "flex", flexDirection: "column", gap: 6,
            boxShadow: "var(--shadow-1)",
          }}>
            <div style={{ fontWeight: 700, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--fg-3)", marginBottom: 4 }}>
              Cobertura
            </div>
            <CoverageLegend pct={0.95} label="muy alta (>90%)" />
            <CoverageLegend pct={0.78} label="alta (75–90%)" />
            <CoverageLegend pct={0.65} label="media (60–75%)" />
            <CoverageLegend pct={0.5}  label="baja (<60%)" />
          </div>

          {/* Stats overlay */}
          <div style={{ position: "absolute", right: 28, top: 28, display: "flex", gap: 10 }}>
            <StatPill label="Provincias"     value="24" />
            <StatPill label="Regiones"       value="7"  />
            <StatPill label="Supermercados"  value="9"  tone="primary" />
          </div>
        </div>

        {/* SIDEBAR */}
        <div className="col" style={{ gap: 16 }}>
          {/* Active region detail */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
              <div style={{ fontSize: 11, color: "var(--fg-3)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Región seleccionada
              </div>
              <span className="badge outlined">{region.provs.length} prov.</span>
            </div>

            <h2 style={{ fontSize: 24, marginBottom: 4 }}>{region.name}</h2>
            <div style={{ color: "var(--fg-3)", fontSize: 13, marginBottom: 16 }}>
              {region.provs.slice(0, 4).join(", ")}
              {region.provs.length > 4 ? ` +${region.provs.length - 4}` : ""}
            </div>

            {/* coverage bar */}
            <div style={{ marginBottom: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
                <span style={{ fontSize: 12, color: "var(--fg-2)", fontWeight: 600 }}>Productos comparables</span>
                <span className="mono" style={{ fontSize: 18, fontWeight: 700, color: "var(--primary)" }}>
                  {(REGION_COV[region.id] * 100).toFixed(0)}%
                </span>
              </div>
              <div style={{ height: 8, background: "var(--bg-2)", borderRadius: 4, overflow: "hidden" }}>
                <div style={{ width: `${REGION_COV[region.id] * 100}%`, height: "100%", background: "var(--primary)", borderRadius: 4 }} />
              </div>
              <div style={{ fontSize: 11.5, color: "var(--fg-3)", marginTop: 5 }}>
                <strong className="mono">{Math.floor(TOTAL_PRODUCTS * REGION_COV[region.id]).toLocaleString("es-AR")}</strong> de {TOTAL_PRODUCTS.toLocaleString("es-AR")} productos relevados acá
              </div>
            </div>

            {/* supermarkets in region */}
            <div>
              <div style={{ fontSize: 11, color: "var(--fg-3)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10 }}>
                Supermercados que operan
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8 }}>
                {REGION_SM[region.id].map((s) => (
                  <div key={s} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", background: "var(--bg-2)", borderRadius: 8 }}>
                    <SMSwatch sm={s} />
                    <span style={{ fontSize: 12.5, fontWeight: 500 }}>{SM_BY_ID[s]?.name ?? s}</span>
                  </div>
                ))}
              </div>
            </div>

            <button
              className="btn"
              style={{ width: "100%", justifyContent: "center", marginTop: 18 }}
              onClick={() => router.push(`/resultados?q=leche+entera`)}
            >
              Buscar en {region.name} <Icon.arrowR />
            </button>
          </div>

          {/* All regions list */}
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--border)" }}>
              <h3>Todas las regiones</h3>
            </div>
            {REGIONS.map((r) => {
              const isActive = r.id === active;
              return (
                <button
                  key={r.id}
                  onClick={() => setActive(r.id)}
                  style={{
                    display: "flex", alignItems: "center", gap: 12,
                    width: "100%", padding: "12px 18px",
                    background: isActive ? "var(--primary-tint)" : "transparent",
                    border: 0, borderBottom: "1px solid var(--border)",
                    textAlign: "left", cursor: "pointer",
                    color: isActive ? "var(--primary)" : "var(--fg)",
                  }}
                >
                  <div style={{
                    width: 36, height: 36, borderRadius: 8,
                    background: isActive ? "var(--primary)" : `oklch(${0.95 - REGION_COV[r.id] * 0.5} 0.05 250)`,
                    border: "1px solid var(--border)",
                    display: "grid", placeItems: "center",
                    fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 700,
                    color: isActive ? "white" : "var(--fg-2)",
                  }}>
                    {(REGION_COV[r.id] * 100).toFixed(0)}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 13.5 }}>{r.name}</div>
                    <div style={{ fontSize: 11.5, color: "var(--fg-3)" }}>
                      {REGION_SM[r.id].length} supermercados · {r.provs.length} provincias
                    </div>
                  </div>
                  <Icon.arrowR style={{ color: "var(--fg-4)" }} />
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Argentina map — polígonos geométricos sugestivos en SVG 440×680
// ============================================================================
const SHAPES: Record<string, { label: string; d: string; labelPos: [number, number] }> = {
  noa:       { label: "NOA",       d: "M 150 40 L 245 35 L 260 130 L 175 145 L 155 110 Z",                                                                             labelPos: [200, 90]  },
  nea:       { label: "NEA",       d: "M 245 35 L 320 60 L 340 165 L 270 175 L 260 130 Z",                                                                             labelPos: [295, 110] },
  cuyo:      { label: "Cuyo",      d: "M 130 145 L 175 145 L 200 250 L 140 265 L 115 220 Z",                                                                           labelPos: [160, 210] },
  centro:    { label: "Centro",    d: "M 175 145 L 260 130 L 270 175 L 285 250 L 200 250 Z",                                                                           labelPos: [230, 200] },
  pampeana:  { label: "Pampeana",  d: "M 140 265 L 200 250 L 285 250 L 305 340 L 220 365 L 155 350 L 135 305 Z",                                                      labelPos: [220, 310] },
  amba:      { label: "AMBA",      d: "M 270 280 L 305 280 L 305 340 L 280 345 Z",                                                                                     labelPos: [290, 313] },
  patagonia: { label: "Patagonia", d: "M 155 350 L 220 365 L 305 340 L 290 460 L 230 580 L 195 640 L 175 580 L 155 470 L 140 410 Z",                                  labelPos: [220, 495] },
};

function ArgMap({ active, setActive }: { active: string; setActive: (id: string) => void }) {
  const fillFor = (id: string) => {
    if (id === active) return "var(--primary)";
    const c = REGION_COV[id];
    return `oklch(${0.96 - c * 0.55} 0.06 250)`;
  };

  return (
    <div style={{ width: "100%", display: "flex", justifyContent: "center" }}>
      <svg viewBox="0 0 440 680" width="100%" style={{ maxWidth: 460, height: "auto" }}>
        <defs>
          <pattern id="ocean" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="6" stroke="oklch(0.95 0.01 220)" strokeWidth="1" />
          </pattern>
        </defs>
        <rect x="0" y="0" width="440" height="680" fill="url(#ocean)" opacity="0.5" />

        {REGIONS.map((r) => {
          const s = SHAPES[r.id];
          const isActive = active === r.id;
          return (
            <g key={r.id}>
              <path
                d={s.d}
                fill={fillFor(r.id)}
                stroke="var(--surface)"
                strokeWidth="2.5"
                onClick={() => setActive(r.id)}
                style={{
                  cursor: "pointer",
                  transition: "fill .15s, filter .2s",
                  filter: isActive ? "drop-shadow(0 6px 14px oklch(0.30 0.08 250 / 0.3))" : "none",
                }}
              />
              <text
                x={s.labelPos[0]} y={s.labelPos[1]}
                textAnchor="middle" dominantBaseline="middle"
                pointerEvents="none"
                style={{ fontFamily: "var(--font-sans)", fontSize: 13, fontWeight: 700, fill: "white" }}
              >
                {s.label}
              </text>
              <text
                x={s.labelPos[0]} y={s.labelPos[1] + 16}
                textAnchor="middle" dominantBaseline="middle"
                pointerEvents="none"
                style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, fontWeight: 600, fill: "white", opacity: isActive ? 0.95 : 0.85 }}
              >
                {(REGION_COV[r.id] * 100).toFixed(0)}%
              </text>
            </g>
          );
        })}

        {/* TDF decorativo */}
        <circle cx="230" cy="652" r="6" fill="oklch(0.90 0.02 250)" />
        <text x="244" y="655" fontSize="9.5" fill="var(--fg-3)" fontFamily="var(--font-mono)">TDF</text>

        {/* Brújula */}
        <g transform="translate(380, 50)">
          <circle r="20" fill="var(--surface)" stroke="var(--border)" />
          <path d="M 0 -12 L 4 0 L 0 12 L -4 0 Z" fill="var(--primary)" />
          <text y="-22" textAnchor="middle" fontSize="9" fontFamily="var(--font-mono)" fill="var(--fg-3)">N</text>
        </g>
      </svg>
    </div>
  );
}

function StatPill({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "neutral" | "primary" }) {
  return (
    <div className="card" style={{ padding: "10px 14px", display: "flex", flexDirection: "column", boxShadow: "var(--shadow-1)" }}>
      <span style={{ fontSize: 10, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</span>
      <span className="mono" style={{ fontSize: 22, fontWeight: 700, color: tone === "primary" ? "var(--primary)" : "var(--fg)" }}>{value}</span>
    </div>
  );
}

function CoverageLegend({ pct, label }: { pct: number; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ width: 16, height: 16, borderRadius: 4, background: `oklch(${0.96 - pct * 0.55} 0.06 250)`, border: "1px solid var(--border)", flexShrink: 0 }} />
      <span>{label}</span>
    </div>
  );
}
