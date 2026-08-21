"use client";

import React from "react";

// ============================================================================
// Logo — wordmark
// ============================================================================
export function Logo({ size = 18, color = "var(--primary)" }: { size?: number; color?: string }) {
  return (
    <div style={{
      display: "inline-flex", alignItems: "center",
      fontWeight: 800, fontSize: size, letterSpacing: "-0.025em",
      color: "var(--fg)", lineHeight: 1, whiteSpace: "nowrap",
    }}>
      <span style={{ color, marginRight: 1, transform: "translateY(1px)", display: "inline-block" }}>¿</span>
      <span>a cuánto está</span>
      <span style={{ color, marginLeft: 1, transform: "translateY(-1px)", display: "inline-block" }}>?</span>
    </div>
  );
}

// ============================================================================
// Category icon system — color illustration (64×64 viewBox)
// ============================================================================
const ICON_BG: Record<string, string> = {
  lacteos:     "#eef3fb",
  bebidas:     "#f0ecfb",
  carnes:      "#fbeeed",
  panificados: "#fbf5ea",
  limpieza:    "#eaf7f7",
  higiene:     "#fbedf5",
  frutas:      "#eef8f1",
  congelados:  "#edf4fb",
  almacen:     "#f8f2e8",
  snacks:      "#fbf3eb",
  desayuno:    "#fef5e7",
  mascotas:    "#f8f2eb",
  bebes:       "#fef0f5",
  hogar_bazar: "#f2f4f8",
  farmacia_salud: "#eefaf4",
  electro_tecnologia: "#f0f4ff",
  otros:       "#eef1f7",
};

export function CatIcon({ id, size = 72 }: { id: string; size?: number }) {
  const bg = ICON_BG[id] || "#f5f5f5";

  const content: Record<string, React.ReactNode> = {

    lacteos: <>
      <ellipse cx="32" cy="51.5" rx="10" ry="2" fill="#2a5fa5" opacity="0.10"/>
      <path d="M21 23 L43 23 L44 51 a0.5 0.5 0 0 1 -0.5 0.5 L21.5 51.5 a0.5 0.5 0 0 1 -0.5 -0.5 Z"
        fill="white" stroke="#ccd8ee" strokeWidth="0.9"/>
      <path d="M21 23 C22 20.5 23 21.5 24 23 C25 20.5 26 21.5 27 23 C28 20.5 29 21.5 30 23 C31 20.5 32 21.5 33 23 C34 20.5 35 21.5 36 23 C37 20.5 38 21.5 39 23 C40 20.5 41 21.5 42 23 C43 20.5 43 21.5 43 23 Z"
        fill="#2a5fa5"/>
      <rect x="21" y="30" width="22" height="8" fill="#2a5fa5"/>
      <text x="32" y="35.6" textAnchor="middle" fontFamily="var(--font-sans)"
        fontSize="4" fontWeight="800" fill="white">LECHE</text>
      <line x1="23" y1="42" x2="41" y2="42" stroke="#ccd8ee" strokeWidth="0.9"/>
      <line x1="23" y1="44.5" x2="38" y2="44.5" stroke="#ccd8ee" strokeWidth="0.9"/>
      <line x1="23" y1="47" x2="35" y2="47" stroke="#ccd8ee" strokeWidth="0.7"/>
    </>,

    bebidas: <>
      <ellipse cx="32" cy="52.5" rx="8" ry="1.8" fill="#6240a8" opacity="0.12"/>
      <rect x="28" y="12" width="8" height="5" rx="0.8" fill="#3a2060"/>
      <path d="M29 17 L35 17 L35.5 22 L28.5 22 Z" fill="#6240a8"/>
      <path d="M23 22 L41 22 L41 52 a2 2 0 0 1 -2 2 L25 54 a2 2 0 0 1 -2 -2 Z" fill="#6240a8"/>
      <rect x="25" y="31" width="14" height="13" fill="white"/>
      <rect x="27" y="34" width="10" height="1.2" fill="#6240a8"/>
      <rect x="27" y="37" width="7" height="0.9" fill="#6240a8" opacity="0.55"/>
      <rect x="27" y="39" width="9" height="0.9" fill="#6240a8" opacity="0.45"/>
      <rect x="27" y="41" width="5.5" height="0.9" fill="#6240a8" opacity="0.35"/>
      <path d="M25 24 L27 24 L27 30 L25 30 Z" fill="white" opacity="0.18"/>
    </>,

    carnes: <>
      <ellipse cx="32" cy="46" rx="13" ry="2.5" fill="#b84040" opacity="0.12"/>
      <ellipse cx="45" cy="28" rx="4" ry="6" fill="#ede0d0"/>
      <ellipse cx="45" cy="28" rx="2" ry="3" fill="#d8c8b4"/>
      <path d="M14 30 a16 10 0 0 1 32 0 a5 4 0 0 1 -4.5 4 a4 3 0 0 0 -4 3 a7 5 0 0 1 -7 3 a7 5 0 0 1 -7 -3 a4 3 0 0 0 -4 -3 a5 4 0 0 1 -5.5 -4 z"
        fill="#b84040"/>
      <path d="M20 30 q6 -2 12 0" stroke="#f0e0d0" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
      <path d="M18 35 q7 -1.5 14 0" stroke="#f0e0d0" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
      <path d="M23 26 q4 -1.5 8 0" stroke="#f0e0d0" strokeWidth="1" fill="none" strokeLinecap="round" opacity="0.7"/>
    </>,

    panificados: <>
      <ellipse cx="32" cy="49" rx="18" ry="2.5" fill="#c08a3a" opacity="0.12"/>
      <path d="M12 38 a20 16 0 0 1 40 0 L52 46 a2 2 0 0 1 -2 2 L14 48 a2 2 0 0 1 -2 -2 Z" fill="#c08a3a"/>
      <rect x="12" y="44.5" width="40" height="3.5" fill="#8a5a18" opacity="0.2" rx="0"/>
      <path d="M17 36 q4 -5 7 -2" stroke="#7a4a10" strokeWidth="1.8" strokeLinecap="round" fill="none"/>
      <path d="M27 33.5 q4 -5 7 -2" stroke="#7a4a10" strokeWidth="1.8" strokeLinecap="round" fill="none"/>
      <path d="M37 35 q4 -5 7 -2" stroke="#7a4a10" strokeWidth="1.8" strokeLinecap="round" fill="none"/>
      <ellipse cx="28" cy="32" rx="7" ry="2.5" fill="white" opacity="0.2"/>
    </>,

    limpieza: <>
      <ellipse cx="29" cy="52.5" rx="9" ry="1.8" fill="#2a8a8a" opacity="0.12"/>
      <path d="M30 19 L45 16 L45 21 L30 21 Z" fill="#1a6060"/>
      <rect x="26" y="16.5" width="5" height="5.5" rx="0.8" fill="#0d4848"/>
      <path d="M20 21 L36 21 L37 52 a2 2 0 0 1 -2 2 L22 54 a2 2 0 0 1 -2 -2 Z" fill="#2a8a8a"/>
      <rect x="22" y="32" width="13" height="12" fill="white"/>
      <rect x="24" y="35" width="9" height="1.2" fill="#2a8a8a"/>
      <rect x="24" y="38" width="6" height="0.9" fill="#2a8a8a" opacity="0.55"/>
      <rect x="24" y="40" width="8" height="0.9" fill="#2a8a8a" opacity="0.45"/>
      <path d="M22 23 L24.5 23 L24.5 30 L22 30 Z" fill="white" opacity="0.18"/>
    </>,

    higiene: <>
      <ellipse cx="32" cy="52.5" rx="11" ry="2" fill="#c05880" opacity="0.10"/>
      <rect x="28" y="11" width="5" height="3" rx="0.6" fill="#7a2a50"/>
      <path d="M30 14 L40 14 L40 17 L34 17 L34 19 L30 19 Z" fill="#7a2a50"/>
      <rect x="22" y="19" width="20" height="3" rx="0.5" fill="#a04870"/>
      <path d="M19 22 L45 22 L46 50 a2 2 0 0 1 -2 2 L20 52 a2 2 0 0 1 -2 -2 Z" fill="#c05880"/>
      <rect x="22" y="30" width="20" height="15" fill="white"/>
      <rect x="24" y="32.5" width="16" height="2" fill="#c05880"/>
      <rect x="24" y="36" width="11" height="1.1" fill="#c05880" opacity="0.6"/>
      <rect x="24" y="38" width="14" height="1.1" fill="#c05880" opacity="0.5"/>
      <rect x="24" y="40" width="9" height="1.1" fill="#c05880" opacity="0.4"/>
      <rect x="24" y="42" width="12" height="1.1" fill="#c05880" opacity="0.4"/>
      <path d="M21 24 L23 24 L23 32 L21 32 Z" fill="white" opacity="0.18"/>
    </>,

    frutas: <>
      <ellipse cx="32" cy="50" rx="13" ry="2.5" fill="#3a8a4a" opacity="0.12"/>
      <line x1="32" y1="19" x2="33.5" y2="13.5" stroke="#5a3a1a" strokeWidth="1.6" strokeLinecap="round"/>
      <path d="M33 15 c-1 -0.5 -6 0.5 -5.5 3.5 c0 2 4 2.5 6.5 1 c1 -1 0.5 -3 -1 -4.5 z" fill="#4a9a58"/>
      <path d="M18 34 c0 -9 5.5 -15 11 -15 c2.5 0 4 1.5 3 3 c-1 -1.5 1.5 -3 4 -3 c5.5 0 11 6 11 15 c0 9 -6 16 -14 16 c-8 0 -15 -7 -15 -16 z"
        fill="#3a8a4a"/>
      <path d="M23 27 c0 -1.5 2 -3 5 -2 c0.5 3 -0.5 6 -3.5 6 c-1.5 -1 -1.5 -2 -1.5 -4 z" fill="white" opacity="0.22"/>
    </>,

    congelados: <>
      <ellipse cx="32" cy="54.5" rx="5" ry="1.4" fill="#4a8ab8" opacity="0.15"/>
      <rect x="30.5" y="40" width="3" height="14" rx="0.6" fill="#c8a878"/>
      <rect x="30.5" y="40" width="3" height="1.5" fill="#a88858" opacity="0.45"/>
      <rect x="19" y="12" width="26" height="30" rx="4" fill="#88c5e5"/>
      <path d="M19 16 q0 -4 4 -4 L41 12 q4 0 4 4 L45 19 q-2 3 -5 -1 q-3 4 -5 -1 q-3 4 -5 -1 q-3 4 -5 -1 q-3 4 -5 1 Z"
        fill="#5a3a1a"/>
      <ellipse cx="27" cy="14" rx="3.5" ry="0.9" fill="white" opacity="0.22"/>
      <path d="M22 22 L24 22 L24 39 L22 39 Z" fill="white" opacity="0.28"/>
      <circle cx="30" cy="26" r="0.7" fill="white" opacity="0.6"/>
      <circle cx="36" cy="32" r="0.6" fill="white" opacity="0.5"/>
      <circle cx="28" cy="34" r="0.6" fill="white" opacity="0.5"/>
      <circle cx="38" cy="24" r="0.5" fill="white" opacity="0.5"/>
    </>,

    almacen: <>
      <ellipse cx="32" cy="54" rx="15" ry="2" fill="#9a6a30" opacity="0.12"/>
      <rect x="14" y="14" width="36" height="40" rx="0.8" fill="#9a6a30"/>
      <rect x="14" y="14" width="36" height="2" fill="#b88a50"/>
      <rect x="48" y="14" width="2" height="40" fill="#6a4010" opacity="0.4"/>
      <rect x="16" y="18" width="32" height="6" fill="white"/>
      <text x="32" y="22.5" textAnchor="middle" fontFamily="var(--font-sans)"
        fontSize="4.5" fontWeight="800" fill="#9a6a30">FIDEOS</text>
      <rect x="18" y="28" width="28" height="22" fill="#f0d090"/>
      <g stroke="#c08a3a" strokeWidth="0.9" fill="none" strokeLinecap="round">
        <path d="M20 32 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1"/>
        <path d="M20 36 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1"/>
        <path d="M20 40 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1"/>
        <path d="M20 44 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1"/>
        <path d="M20 48 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1 q2.5 -1 5 1"/>
      </g>
    </>,

    snacks: <>
      <ellipse cx="32" cy="53.5" rx="11" ry="1.8" fill="#d07828" opacity="0.12"/>
      <path d="M18 15 q-1.5 -3 0.5 -3 q1 -2 2.5 0 q1 -2 2.5 0 q1 -2 3 0 q1 -2 3 0 q1 -2 3 0 q1 -2 3 0 q1 -2 3 0 q1 -2 2.5 0 q1.5 -2 0.5 3 z"
        fill="#b55e18"/>
      <path d="M18 14 L46 14 L44 52 a2 2 0 0 1 -2 2 L22 54 a2 2 0 0 1 -2 -2 Z" fill="#d07828"/>
      <rect x="20" y="26" width="24" height="15" fill="white"/>
      <rect x="23" y="29" width="18" height="2" fill="#d07828"/>
      <rect x="24" y="33" width="13" height="1.1" fill="#d07828" opacity="0.55"/>
      <rect x="25" y="35.2" width="9" height="1" fill="#d07828" opacity="0.4"/>
      <ellipse cx="31" cy="46.5" rx="8" ry="4.5" fill="#f0c060" transform="rotate(-6 31 46.5)"/>
      <path d="M24 44 q7 -2 15 0" stroke="#c09030" strokeWidth="0.8" fill="none"/>
      <path d="M20 15 L22 15 L21 52.5 L19 52.5 Z" fill="white" opacity="0.2"/>
    </>,

    mascotas: <>
      <ellipse cx="32" cy="52.5" rx="12" ry="2" fill="#8a5a3a" opacity="0.10"/>
      <ellipse cx="20" cy="26" rx="4.2" ry="5.2" fill="#8a5a3a"/>
      <ellipse cx="32" cy="22" rx="4.2" ry="5.2" fill="#8a5a3a"/>
      <ellipse cx="44" cy="26" rx="4.2" ry="5.2" fill="#8a5a3a"/>
      <path d="M18 40 a14 11 0 0 1 28 0 a7 7 0 0 1 -7 7.5 a5.5 4.5 0 0 1 -7 0 a5.5 4.5 0 0 1 -7 0 a7 7 0 0 1 -7 -7.5 z"
        fill="#8a5a3a"/>
    </>,

    desayuno: <>
      <ellipse cx="32" cy="53" rx="14" ry="2" fill="#a06020" opacity="0.12"/>
      <path d="M19 28 L45 28 L43 47 a4 4 0 0 1 -4 4 L25 51 a4 4 0 0 1 -4 -4 Z" fill="#d97706"/>
      <path d="M43 32 h5 a4 4 0 0 1 4 4 v2 a4 4 0 0 1 -4 4 h-5" fill="none" stroke="#d97706" strokeWidth="2.5"/>
      <path d="M26 22 q2 -4 0 -7 M32 22 q2 -4 0 -7 M38 22 q2 -4 0 -7" fill="none" stroke="#f59e0b" strokeWidth="1.2" strokeLinecap="round"/>
    </>,

    bebes: <>
      <ellipse cx="32" cy="53" rx="12" ry="2" fill="#db2777" opacity="0.10"/>
      <path d="M26 26 L38 26 L39 48 a3 3 0 0 1 -3 3 L28 51 a3 3 0 0 1 -3 -3 Z" fill="#f472b6"/>
      <rect x="28" y="20" width="8" height="6" fill="#fb7185" rx="1"/>
      <path d="M30 15 a2 2 0 0 1 4 0 v5 h-4 Z" fill="#fbcfe8"/>
      <circle cx="32" cy="38" r="4" fill="white" opacity="0.8"/>
      <path d="M30 38 h4 M32 36 v4" stroke="#db2777" strokeWidth="1"/>
    </>,

    hogar_bazar: <>
      <ellipse cx="32" cy="53" rx="13" ry="2" fill="#475569" opacity="0.12"/>
      <path d="M18 30 L32 18 L46 30 V49 a2 2 0 0 1 -2 2 H20 a2 2 0 0 1 -2 -2 Z" fill="#64748b"/>
      <path d="M28 51 V36 h8 v15 Z" fill="#cbd5e1"/>
      <rect x="37" y="24" width="4" height="6" fill="#94a3b8"/>
    </>,

    farmacia_salud: <>
      <ellipse cx="32" cy="53" rx="12" ry="2" fill="#059669" opacity="0.12"/>
      <rect x="20" y="22" width="24" height="28" rx="4" fill="#10b981"/>
      <rect x="29.5" y="28" width="5" height="16" fill="white" rx="1"/>
      <rect x="24" y="33.5" width="16" height="5" fill="white" rx="1"/>
    </>,

    electro_tecnologia: <>
      <ellipse cx="32" cy="53" rx="12" ry="2" fill="#4f46e5" opacity="0.12"/>
      <path d="M34 16 L22 34 h8 L28 50 L42 30 h-8 Z" fill="#6366f1"/>
    </>,

    otros: <>
      <ellipse cx="32" cy="53" rx="14" ry="2" fill="#5a6880" opacity="0.12"/>
      <path d="M32 13 L52 21 L32 29 L12 21 Z" fill="#8a9ab0"/>
      <path d="M12 21 L12 47 L32 55 L32 29 Z" fill="#5a6880"/>
      <path d="M52 21 L52 47 L32 55 L32 29 Z" fill="#6a7a90"/>
      <path d="M12 21 L32 29 L52 21" stroke="white" strokeWidth="0.7" opacity="0.45"/>
      <line x1="32" y1="29" x2="32" y2="55" stroke="white" strokeWidth="0.6" opacity="0.35"/>
      <path d="M22 17 L32 21 L42 17 L32 13 Z" fill="#6a7a90" opacity="0.5"/>
    </>,
  };

  return (
    <svg viewBox="0 0 64 64" width={size} height={size}>
      <circle cx="32" cy="32" r="30" fill={bg}/>
      {content[id] || null}
    </svg>
  );
}
