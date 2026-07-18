"use client";

import React, { useState, useEffect, useRef, useId } from "react";

// ============================================================================
// Supermarket static data (replaces window.ACE_DATA.SM_BY_ID)
// Handles both design IDs (changomas, anonima) and backend IDs (chango_mas, la_anonima)
// ============================================================================
const SM_MAP: Record<string, { name: string; color: string; short: string }> = {
  coto:       { name: "Coto",        color: "var(--sm-1)", short: "C"  },
  carrefour:  { name: "Carrefour",   color: "var(--sm-2)", short: "CF" },
  disco:      { name: "Disco",       color: "var(--sm-3)", short: "D"  },
  atomo:      { name: "Átomo",       color: "var(--sm-4)", short: "At" },
  vea:        { name: "Vea",         color: "var(--sm-5)", short: "V"  },
  jumbo:      { name: "Jumbo",       color: "var(--sm-6)", short: "J"  },
  dia:        { name: "Dia",         color: "var(--sm-7)", short: "Dí" },
  changomas:  { name: "Chango Más",  color: "var(--sm-8)", short: "Ch" },
  chango_mas: { name: "Chango Más",  color: "var(--sm-8)", short: "Ch" },
  anonima:    { name: "La Anónima",  color: "var(--sm-9)", short: "LA" },
  la_anonima: { name: "La Anónima",  color: "var(--sm-9)", short: "LA" },
};

export const SM_BY_ID = SM_MAP;

// ============================================================================
// Number formatting (Argentine style: $2.450, +12%)
// ============================================================================
export const fmtPrice = (n: number, { decimals = 0 }: { decimals?: number } = {}): string => {
  const v = Math.abs(n).toLocaleString("es-AR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return (n < 0 ? "−" : "") + v;
};

export const fmtPct = (n: number, { decimals = 1, sign = true }: { decimals?: number; sign?: boolean } = {}): string => {
  const p = n * 100;
  const s = (sign && p > 0 ? "+" : "") + p.toFixed(decimals) + "%";
  return s.replace(".", ",");
};

export const fmtInt = (n: number): string => n.toLocaleString("es-AR");

// ============================================================================
// Price component
// ============================================================================
export function Price({ value, size = "md", currency = "$" }: { value: number; size?: "sm" | "md" | "lg" | "xl"; currency?: string }) {
  const cls = size === "xl" ? "price price-xl"
            : size === "lg" ? "price price-lg"
            : "price";
  const style = size === "sm" ? { fontSize: 14 } : {};
  return (
    <span className={cls} style={style}>
      <span className="price-currency">{currency}</span>{fmtPrice(value)}
    </span>
  );
}

// ============================================================================
// Variation badge
// ============================================================================
export function VarBadge({ value, period, large = false }: { value?: number | null; period?: string; large?: boolean }) {
  if (value === 0 || value === undefined || value === null) {
    return <span className="badge flat">0,0%</span>;
  }
  const up = value > 0;
  const cls = up ? "up" : "down";
  return (
    <span className={`badge ${cls}`} style={large ? { fontSize: 13, padding: "5px 10px" } : undefined}>
      <Arrow dir={up ? "up" : "down"} />
      {fmtPct(value)}
      {period ? <span style={{ opacity: 0.75, marginLeft: 2 }}>{period}</span> : null}
    </span>
  );
}

function Arrow({ dir }: { dir: "up" | "down" }) {
  if (dir === "up") return (
    <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
      <path d="M5 1.5 L8.5 5.5 L5.8 5.5 L5.8 8.5 L4.2 8.5 L4.2 5.5 L1.5 5.5 Z" fill="currentColor"/>
    </svg>
  );
  return (
    <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
      <path d="M5 8.5 L1.5 4.5 L4.2 4.5 L4.2 1.5 L5.8 1.5 L5.8 4.5 L8.5 4.5 Z" fill="currentColor"/>
    </svg>
  );
}

// ============================================================================
// Supermarket swatch (colored avatar circle)
// ============================================================================
export function SMSwatch({ sm, size = "md" }: { sm: string; size?: "sm" | "md" | "lg" }) {
  const s = SM_MAP[sm] || { name: String(sm), color: "var(--sm-8)", short: String(sm).slice(0, 2).toUpperCase() };
  const px = size === "lg" ? 36 : size === "sm" ? 18 : 24;
  return (
    <span
      title={s.name}
      style={{
        display: "inline-flex", alignItems: "center", justifyContent: "center",
        width: px, height: px,
        borderRadius: "50%",
        background: s.color,
        color: "white",
        fontFamily: "var(--font-sans)",
        fontWeight: 700,
        fontSize: px * 0.38,
        letterSpacing: "-0.02em",
        boxShadow: "inset 0 -1px 0 rgba(0,0,0,0.15), 0 1px 2px rgba(15,23,42,0.08)",
        flexShrink: 0,
        textTransform: "uppercase",
      }}>
      {s.short}
    </span>
  );
}

// ============================================================================
// Sparkline (mini line)
// ============================================================================
export function Sparkline({ data, color = "currentColor", width = 80, height = 28 }: { data: number[]; color?: string; width?: number; height?: number }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const pad = 2;
  const pts = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (width - pad * 2);
    const y = pad + (1 - (v - min) / (max - min || 1)) * (height - pad * 2);
    return [x, y];
  });
  const d = pts.map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const area = d + ` L ${pts[pts.length-1][0].toFixed(1)} ${height-pad} L ${pts[0][0].toFixed(1)} ${height-pad} Z`;
  return (
    <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ height }}>
      <path d={area} fill={color} opacity="0.08" />
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round"/>
    </svg>
  );
}

// ============================================================================
// Multi-line chart (price history, used in product detail)
// ============================================================================
export function MultiLineChart({ labels, series, inflation, height = 360, showInflation = true, smFilter = null }: {
  labels: string[];
  series: Record<string, number[]>;
  inflation?: number[] | null;
  height?: number;
  showInflation?: boolean;
  smFilter?: string[] | null;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<{ idx: number; x: number } | null>(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(entries => {
      setWidth(entries[0].contentRect.width);
    });
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  const pad = { t: 16, r: 24, b: 36, l: 60 };
  const w = width;
  const h = height;
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;

  const smIds = Object.keys(series).filter(k => !smFilter || smFilter.includes(k));

  const allPrices = smIds.flatMap(k => series[k]);
  let minP = Math.min(...allPrices);
  let maxP = Math.max(...allPrices);
  const span = maxP - minP;
  minP -= span * 0.12;
  maxP += span * 0.18;

  const startMedian = smIds.map(k => series[k][0]).sort((a,b)=>a-b)[Math.floor(smIds.length/2)];
  const infScaled = inflation ? inflation.map(v => startMedian * v) : null;

  const xAt = (i: number) => pad.l + (i / (labels.length - 1)) * innerW;
  const yAt = (v: number) => pad.t + (1 - (v - minP) / (maxP - minP)) * innerH;

  const ticks = 5;
  const yTicks = Array.from({length: ticks}, (_, i) => minP + (maxP - minP) * (i/(ticks-1)));
  const xStep = Math.max(1, Math.floor(labels.length / 6));

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    if (x < pad.l - 10 || x > w - pad.r + 10) { setHover(null); return; }
    const t = (x - pad.l) / innerW;
    const idx = Math.round(Math.max(0, Math.min(labels.length - 1, t * (labels.length - 1))));
    setHover({ idx, x: xAt(idx) });
  };

  return (
    <div ref={ref} style={{ position: "relative", width: "100%", minWidth: 0 }}>
      <svg width={w} height={h} style={{ display: "block" }} onMouseMove={onMove} onMouseLeave={()=>setHover(null)}>
        {yTicks.map((v, i) => (
          <g key={i}>
            <line x1={pad.l} x2={w - pad.r} y1={yAt(v)} y2={yAt(v)}
              stroke="var(--border)" strokeDasharray={i === 0 ? "0" : "2 4"} />
            <text x={pad.l - 10} y={yAt(v)} textAnchor="end" dominantBaseline="central"
              fill="var(--fg-3)" fontSize="10.5" fontFamily="var(--font-mono)">
              ${fmtPrice(v)}
            </text>
          </g>
        ))}
        {labels.map((l, i) => i % xStep === 0 ? (
          <text key={i} x={xAt(i)} y={h - pad.b + 18} textAnchor="middle"
            fill="var(--fg-3)" fontSize="10.5" fontFamily="var(--font-mono)">
            {l}
          </text>
        ) : null)}
        {showInflation && infScaled && (
          <path
            d={infScaled.map((v, i) => (i === 0 ? "M" : "L") + xAt(i).toFixed(1) + " " + yAt(v).toFixed(1)).join(" ")}
            stroke="var(--warn)" strokeWidth="2" fill="none"
            strokeDasharray="5 4"
          />
        )}
        {smIds.map(k => {
          const sm = SM_MAP[k] || { color: "var(--sm-8)" };
          const path = series[k].map((v, i) => (i === 0 ? "M" : "L") + xAt(i).toFixed(1) + " " + yAt(v).toFixed(1)).join(" ");
          return (
            <path key={k} d={path}
              stroke={sm.color} strokeWidth="2" fill="none"
              strokeLinecap="round" strokeLinejoin="round" />
          );
        })}
        {hover && (
          <g>
            <line x1={hover.x} x2={hover.x} y1={pad.t} y2={h - pad.b} stroke="var(--fg-2)" strokeDasharray="2 3" opacity="0.3"/>
            {smIds.map(k => {
              const sm = SM_MAP[k] || { color: "var(--sm-8)" };
              return <circle key={k} cx={hover.x} cy={yAt(series[k][hover.idx])} r="4" fill="white" stroke={sm.color} strokeWidth="2"/>;
            })}
            {showInflation && infScaled && (
              <circle cx={hover.x} cy={yAt(infScaled[hover.idx])} r="3.5" fill="var(--warn)" stroke="white" strokeWidth="1.5"/>
            )}
          </g>
        )}
      </svg>
      {hover && (
        <div className="chart-tooltip" style={{ left: hover.x, top: pad.t }}>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>{labels[hover.idx]}</div>
          {smIds.slice().sort((a,b)=>series[a][hover.idx]-series[b][hover.idx]).map(k => {
            const sm = SM_MAP[k] || { name: k, color: "var(--sm-8)" };
            return (
              <div className="ct-row" key={k} style={{ justifyContent: "space-between", gap: 12 }}>
                <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <span className="ct-dot" style={{ background: sm.color }} />
                  {sm.name}
                </span>
                <span className="mono">${fmtPrice(series[k][hover.idx])}</span>
              </div>
            );
          })}
          {showInflation && infScaled && (
            <div className="ct-row" style={{ justifyContent: "space-between", gap: 12, borderTop: "1px solid rgba(255,255,255,0.15)", marginTop: 4, paddingTop: 4 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <span className="ct-dot" style={{ background: "var(--warn)" }} />
                Inflación
              </span>
              <span className="mono">${fmtPrice(infScaled[hover.idx])}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Bar chart (vertical, for inflation history)
// ============================================================================
export function BarChart({ data, height = 240, color = "var(--primary)", valueFmt = (v: number) => v.toFixed(1) + "%", highlightLast = true }: {
  data: Array<{ m: string; v: number }>;
  height?: number;
  color?: string;
  valueFmt?: (v: number) => string;
  highlightLast?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(entries => setWidth(entries[0].contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  if (!data.length) return <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--fg-4)", fontSize: 13 }}>Sin datos</div>;

  const pad = { t: 24, r: 12, b: 32, l: 36 };
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const max = Math.max(...data.map(d => d.v)) * 1.15;
  const barW = innerW / data.length * 0.66;
  const step = innerW / data.length;

  return (
    <div ref={ref} style={{ width: "100%", minWidth: 0 }}>
      <svg width={width} height={height} style={{ display: "block" }}>
        {[0, 0.5, 1].map((t, i) => {
          const y = pad.t + innerH * (1 - t);
          const v = max * t;
          return (
            <g key={i}>
              <line x1={pad.l} x2={width - pad.r} y1={y} y2={y}
                stroke="var(--border)" strokeDasharray={t === 0 ? "0" : "2 4"} />
              <text x={pad.l - 8} y={y} textAnchor="end" dominantBaseline="central"
                fill="var(--fg-3)" fontSize="10" fontFamily="var(--font-mono)">{v.toFixed(1)}%</text>
            </g>
          );
        })}
        {data.map((d, i) => {
          const bh = (d.v / max) * innerH;
          const x = pad.l + step * i + (step - barW) / 2;
          const y = pad.t + innerH - bh;
          const isLast = i === data.length - 1;
          const c = (highlightLast && isLast) ? "var(--primary)" : color;
          return (
            <g key={i}>
              <rect x={x} y={y} width={barW} height={bh} fill={c} rx="3"
                opacity={(highlightLast && !isLast) ? 0.85 : 1}/>
              <text x={x + barW/2} y={y - 6} textAnchor="middle"
                fill={isLast ? "var(--primary)" : "var(--fg-2)"}
                fontSize="10.5" fontFamily="var(--font-mono)" fontWeight={isLast ? 700 : 500}>
                {valueFmt(d.v)}
              </text>
              <text x={x + barW/2} y={pad.t + innerH + 18} textAnchor="middle"
                fill="var(--fg-3)" fontSize="10.5" fontFamily="var(--font-mono)">
                {d.m}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ============================================================================
// Dual line chart (dolar blue vs oficial)
// ============================================================================
export function DualLineChart({ labels, a, b, aLabel, bLabel, aColor, bColor, height = 280 }: {
  labels: string[];
  a: number[];
  b: number[];
  aLabel: string;
  bLabel: string;
  aColor: string;
  bColor: string;
  height?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [hover, setHover] = useState<{ idx: number; x: number } | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(entries => setWidth(entries[0].contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  if (!labels.length || !a.length || !b.length) {
    return <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--fg-4)", fontSize: 13 }}>Sin datos históricos</div>;
  }

  const pad = { t: 16, r: 60, b: 32, l: 50 };
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const all = [...a, ...b];
  let minV = Math.min(...all);
  let maxV = Math.max(...all);
  const sp = maxV - minV;
  minV -= sp * 0.1; maxV += sp * 0.1;

  const xAt = (i: number) => pad.l + (i / (labels.length - 1)) * innerW;
  const yAt = (v: number) => pad.t + (1 - (v - minV) / (maxV - minV)) * innerH;

  const pathFor = (arr: number[]) => arr.map((v, i) => (i === 0 ? "M" : "L") + xAt(i).toFixed(1) + " " + yAt(v).toFixed(1)).join(" ");
  const areaFor = (arr: number[]) => pathFor(arr) + ` L ${xAt(arr.length-1)} ${pad.t + innerH} L ${xAt(0)} ${pad.t + innerH} Z`;

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    if (x < pad.l || x > width - pad.r) { setHover(null); return; }
    const t = (x - pad.l) / innerW;
    const idx = Math.round(Math.max(0, Math.min(labels.length - 1, t * (labels.length - 1))));
    setHover({ idx, x: xAt(idx) });
  };

  const yTicks = Array.from({ length: 5 }, (_, i) => minV + (maxV-minV) * (i/4));
  const xStep = Math.max(1, Math.floor(labels.length / 6));

  return (
    <div ref={ref} style={{ position: "relative", width: "100%", minWidth: 0 }}>
      <svg width={width} height={height} style={{ display: "block" }} onMouseMove={onMove} onMouseLeave={()=>setHover(null)}>
        {yTicks.map((v, i) => (
          <g key={i}>
            <line x1={pad.l} x2={width - pad.r} y1={yAt(v)} y2={yAt(v)}
              stroke="var(--border)" strokeDasharray={i === 0 ? "0" : "2 4"}/>
            <text x={pad.l - 8} y={yAt(v)} textAnchor="end" dominantBaseline="central"
              fill="var(--fg-3)" fontSize="10" fontFamily="var(--font-mono)">${fmtPrice(v)}</text>
          </g>
        ))}
        {labels.map((l, i) => i % xStep === 0 ? (
          <text key={i} x={xAt(i)} y={height - pad.b + 16} textAnchor="middle"
            fill="var(--fg-3)" fontSize="10" fontFamily="var(--font-mono)">{l}</text>
        ) : null)}
        <path d={areaFor(a)} fill={aColor} opacity="0.06"/>
        <path d={areaFor(b)} fill={bColor} opacity="0.06"/>
        <path d={pathFor(a)} stroke={aColor} strokeWidth="2" fill="none"/>
        <path d={pathFor(b)} stroke={bColor} strokeWidth="2" fill="none"/>
        <g>
          <circle cx={xAt(a.length-1)} cy={yAt(a[a.length-1])} r="4" fill={aColor}/>
          <text x={xAt(a.length-1)+10} y={yAt(a[a.length-1])} dominantBaseline="central"
            fill={aColor} fontSize="11" fontWeight="600">${fmtPrice(a[a.length-1])}</text>
          <circle cx={xAt(b.length-1)} cy={yAt(b[b.length-1])} r="4" fill={bColor}/>
          <text x={xAt(b.length-1)+10} y={yAt(b[b.length-1])} dominantBaseline="central"
            fill={bColor} fontSize="11" fontWeight="600">${fmtPrice(b[b.length-1])}</text>
        </g>
        {hover && (
          <g>
            <line x1={hover.x} x2={hover.x} y1={pad.t} y2={height-pad.b} stroke="var(--fg-2)" strokeDasharray="2 3" opacity="0.3"/>
            <circle cx={hover.x} cy={yAt(a[hover.idx])} r="4" fill="white" stroke={aColor} strokeWidth="2"/>
            <circle cx={hover.x} cy={yAt(b[hover.idx])} r="4" fill="white" stroke={bColor} strokeWidth="2"/>
          </g>
        )}
      </svg>
      {hover && (
        <div className="chart-tooltip" style={{ left: hover.x, top: pad.t }}>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>{labels[hover.idx]}</div>
          <div className="ct-row" style={{ justifyContent: "space-between", gap: 12 }}>
            <span style={{ display:"flex", alignItems:"center", gap: 5 }}><span className="ct-dot" style={{ background: aColor }}/>{aLabel}</span>
            <span className="mono">${fmtPrice(a[hover.idx])}</span>
          </div>
          <div className="ct-row" style={{ justifyContent: "space-between", gap: 12 }}>
            <span style={{ display:"flex", alignItems:"center", gap: 5 }}><span className="ct-dot" style={{ background: bColor }}/>{bLabel}</span>
            <span className="mono">${fmtPrice(b[hover.idx])}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Icon set
// ============================================================================
export const Icon = {
  search: (p: React.SVGProps<SVGSVGElement>) => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>,
  pin: (p: React.SVGProps<SVGSVGElement>) => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}><path d="M12 21s-7-7.5-7-12a7 7 0 1 1 14 0c0 4.5-7 12-7 12Z"/><circle cx="12" cy="9" r="2.5"/></svg>,
  filter: (p: React.SVGProps<SVGSVGElement>) => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}><path d="M4 6h16M7 12h10M10 18h4"/></svg>,
  chevron: (p: React.SVGProps<SVGSVGElement>) => <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" {...p}><path d="m6 9 6 6 6-6"/></svg>,
  arrowR: (p: React.SVGProps<SVGSVGElement>) => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}><path d="M5 12h14M13 6l6 6-6 6"/></svg>,
  close: (p: React.SVGProps<SVGSVGElement>) => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}><path d="M6 6 18 18M18 6 6 18"/></svg>,
  info: (p: React.SVGProps<SVGSVGElement>) => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 8h.01"/></svg>,
  trend: (p: React.SVGProps<SVGSVGElement>) => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}><path d="m3 17 6-6 4 4 8-8"/><path d="M17 7h4v4"/></svg>,
  barcode: (p: React.SVGProps<SVGSVGElement>) => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}><path d="M4 5v14M7 5v14M10 5v14M14 5v14M17 5v14M20 5v14"/></svg>,
  history: (p: React.SVGProps<SVGSVGElement>) => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/></svg>,
  bookmark: (p: React.SVGProps<SVGSVGElement>) => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}><path d="M6 4h12v18l-6-4-6 4Z"/></svg>,
  alert: (p: React.SVGProps<SVGSVGElement>) => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/></svg>,
};

// ============================================================================
// Image placeholder (dotted, with stable ID to avoid hydration mismatch)
// ============================================================================
export function ImagePlaceholder({ label = "producto", w = 80, h = 80, radius = 10 }: { label?: string; w?: number; h?: number; radius?: number }) {
  const uid = useId();
  const id = `img-ph-${uid.replace(/:/g, "")}`;
  return (
    <div style={{
      width: w, height: h, borderRadius: radius,
      background: "var(--surface)",
      border: "1px solid var(--border)",
      display: "grid", placeItems: "center",
      position: "relative", overflow: "hidden",
      flexShrink: 0,
    }}>
      <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity: 0.5 }}>
        <defs>
          <pattern id={id} width="8" height="8" patternUnits="userSpaceOnUse">
            <circle cx="4" cy="4" r="0.6" fill="var(--border-strong)"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill={`url(#${id})`}/>
      </svg>
      <svg viewBox="0 0 24 24" width={Math.min(w, h) * 0.32} height={Math.min(w, h) * 0.32}
        fill="none" stroke="var(--fg-4)" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"
        style={{ position: "relative", zIndex: 1, opacity: 0.6 }}>
        <rect x="3" y="5" width="18" height="14" rx="2"/>
        <circle cx="9" cy="11" r="1.6"/>
        <path d="M21 16 L16 11 L8 19"/>
      </svg>
    </div>
  );
}
