"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/design/components";

export default function ProductoIndexPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  const submit = () => {
    const term = query.trim();
    if (term) router.push(`/resultados?q=${encodeURIComponent(term)}`);
  };

  return (
    <div className="page" style={{ paddingTop: 64, maxWidth: 640, margin: "0 auto" }}>
      <div style={{ textAlign: "center", marginBottom: 28 }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
        <h1 style={{ fontSize: 24, marginBottom: 8 }}>Buscá un producto</h1>
        <p style={{ color: "var(--fg-3)", fontSize: 14 }}>
          Elegí un producto para ver sus precios y su historial en los 9 supermercados.
        </p>
      </div>

      <div className="search lg" style={{ position: "relative" }}>
        <span className="search-icon"><Icon.search width={22} height={22} /></span>
        <input
          placeholder="Buscá un producto, marca o código de barras…"
          value={query}
          autoFocus
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
        />
        <button
          className="btn"
          style={{ position: "absolute", right: 8, top: 8, padding: "12px 18px" }}
          onClick={submit}
        >
          Buscar <Icon.arrowR />
        </button>
      </div>
    </div>
  );
}
