"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/design/icons";
import { Icon } from "@/components/design/components";
import { useRegion } from "@/lib/regionContext";

// Tab icons — SVGs inline desde app.jsx del diseño de referencia
function IconResults() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M4 6h16M4 12h10M4 18h7" />
    </svg>
  );
}

function IconDashboard() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m3 17 6-6 4 4 8-8" />
      <path d="M17 7h4v4" />
    </svg>
  );
}

const TABS = [
  { label: "Buscar",     href: "/",           icon: <Icon.search width={14} height={14} /> },
  { label: "Resultados", href: "/resultados",  icon: <IconResults /> },
  { label: "Economía",   href: "/economia",    icon: <IconDashboard /> },
  { label: "Cobertura",  href: "/cobertura",   icon: <Icon.pin /> },
];

const REGIONS = ["Todas las regiones", "AMBA", "Pampeana", "Centro", "Cuyo", "NOA", "NEA", "Patagonia"];
const SUPERMARKETS = ["Todos", "Coto", "Carrefour", "Disco", "Átomo", "Vea", "Jumbo", "Día", "La Anónima", "Chango Más"];

export default function Header() {
  const pathname = usePathname();

  const { region, setRegion }          = useRegion();
  const [supermarket, setSupermarket]  = useState("Todos");
  const [regionOpen, setRegionOpen]    = useState(false);
  const [smOpen, setSmOpen]            = useState(false);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <header className="topbar">
      <Link href="/" style={{ textDecoration: "none" }}>
        <Logo size={16} />
      </Link>

      <nav className="tabs">
        {TABS.map((tab) => (
          <Link
            key={tab.href}
            href={tab.href}
            className={`tab${isActive(tab.href) ? " active" : ""}`}
          >
            <span className="tab-icon">{tab.icon}</span>
            {tab.label}
          </Link>
        ))}
      </nav>

      <div className="topbar-spacer" />

      <div className="tb-control">
        <Dropdown
          open={regionOpen}
          setOpen={setRegionOpen}
          label={<><Icon.pin /> Región: <strong>{region}</strong> <Icon.chevron /></>}
          items={REGIONS}
          selected={region}
          onSelect={setRegion}
        />
        <Dropdown
          open={smOpen}
          setOpen={setSmOpen}
          label={<>Supermercados: <strong>{supermarket}</strong> <Icon.chevron /></>}
          items={SUPERMARKETS}
          selected={supermarket}
          onSelect={setSupermarket}
        />
      </div>
    </header>
  );
}

function Dropdown({
  open, setOpen, label, items, selected, onSelect,
}: {
  open: boolean;
  setOpen: (v: boolean) => void;
  label: React.ReactNode;
  items: string[];
  selected: string;
  onSelect: (v: string) => void;
}) {
  return (
    <div style={{ position: "relative" }}>
      <button
        className="tb-pill"
        onClick={() => setOpen(!open)}
        style={{ cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6 }}
      >
        {label}
      </button>

      {open && (
        <>
          <div style={{ position: "fixed", inset: 0, zIndex: 40 }} onClick={() => setOpen(false)} />
          <div style={{
            position: "absolute", right: 0, top: "calc(100% + 6px)",
            background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 10, boxShadow: "var(--shadow-pop)",
            minWidth: 180, zIndex: 50, padding: 4,
          }}>
            {items.map((it) => (
              <button
                key={it}
                onClick={() => { onSelect(it); setOpen(false); }}
                style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  width: "100%", padding: "8px 10px",
                  background: selected === it ? "var(--primary-tint)" : "none",
                  border: 0, borderRadius: 6, cursor: "pointer",
                  fontSize: 13,
                  color: selected === it ? "var(--primary)" : "var(--fg)",
                  fontWeight: selected === it ? 600 : 400,
                }}
              >
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
