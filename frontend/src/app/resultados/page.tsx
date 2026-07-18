import { Suspense } from "react";
import ResultadosContent from "./ResultadosContent";

export default function ResultadosPage() {
  return (
    <Suspense fallback={
      <div className="page page-wide">
        <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 24 }}>
          <div className="col" style={{ gap: 12 }}>
            {[...Array(4)].map((_, i) => (
              <div key={i} className="card" style={{ height: 80, background: "var(--bg-2)" }} />
            ))}
          </div>
          <div className="col" style={{ gap: 12 }}>
            {[...Array(6)].map((_, i) => (
              <div key={i} className="card" style={{ height: 112, background: "var(--bg-2)" }} />
            ))}
          </div>
        </div>
      </div>
    }>
      <ResultadosContent />
    </Suspense>
  );
}
