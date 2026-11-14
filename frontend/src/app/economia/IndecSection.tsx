"use client";

import { useQuery } from "@tanstack/react-query";
import { getIndecOverview } from "@/lib/api";
import { DualLineChart, fmtPct, fmtPrice } from "@/components/design/components";
import type { LatestPoint } from "@/types";

// "2026-10-01" -> "oct 2026". Se fuerza UTC para que la zona horaria local no
// corra el primer día del mes al mes anterior.
function fmtPeriod(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("es-AR", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--fg-2)" }}>
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: color }} />
      {label}
    </span>
  );
}

function StatCard({
  label,
  main,
  detail,
  period,
}: {
  label: string;
  main: string;
  detail?: string;
  period: string;
}) {
  return (
    <div style={{ padding: 14, background: "var(--bg-2)", borderRadius: 10, border: "1px solid var(--border)" }}>
      <div style={{ fontSize: 11, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>
        {label}
      </div>
      <div className="mono" style={{ fontSize: 22, fontWeight: 700 }}>{main}</div>
      {detail && <div className="subtle" style={{ fontSize: 12, marginTop: 2 }}>{detail}</div>}
      <div className="subtle" style={{ fontSize: 11.5, marginTop: 8 }}>{period} · Fuente: INDEC</div>
    </div>
  );
}

// El INDEC publica las variaciones como porcentaje (2.1 = 2,1%); fmtPct espera fracción.
const pct = (p: LatestPoint) => fmtPct(p.value / 100, { sign: false });

export default function IndecSection() {
  const { data, isError } = useQuery({
    queryKey: ["indecOverview"],
    queryFn: getIndecOverview,
    staleTime: 30 * 60 * 1000,
  });

  // Si falla o la base todavía no tiene datos, no se muestra nada: la página
  // de economía no debe mostrar un error por una sección complementaria.
  if (isError || !data) return null;
  const hasAnyData = Object.values(data).some((v) => v !== null);
  if (!hasAnyData) return null;

  const foodAnnual = data.ipc_alimentos_interanual;
  const foodMonthly = data.ipc_alimentos_mensual;
  const generalAnnual = data.ipc_general_interanual;
  const generalMonthly = data.ipc_general_mensual;

  return (
    <div style={{ marginBottom: 22 }}>
      <div style={{ marginBottom: 12 }}>
        <h2>Datos oficiales del INDEC</h2>
        <div className="subtle" style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2 }}>
          Precios al consumidor, canasta básica y salarios
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16, marginBottom: 16 }}>
        {foodAnnual && (
          <StatCard
            label="IPC Alimentos"
            main={pct(foodAnnual)}
            detail={foodMonthly ? `${pct(foodMonthly)} el último mes` : undefined}
            period={`Interanual · ${fmtPeriod(foodAnnual.period)}`}
          />
        )}
        {generalAnnual && (
          <StatCard
            label="IPC Nivel general"
            main={pct(generalAnnual)}
            detail={generalMonthly ? `${pct(generalMonthly)} el último mes` : undefined}
            period={`Interanual · ${fmtPeriod(generalAnnual.period)}`}
          />
        )}
        {data.cba && (
          <StatCard
            label="Canasta Básica Alimentaria"
            main={"$" + fmtPrice(data.cba.value)}
            detail="por adulto equivalente · GBA"
            period={fmtPeriod(data.cba.period)}
          />
        )}
        {data.cbt && (
          <StatCard
            label="Canasta Básica Total"
            main={"$" + fmtPrice(data.cbt.value)}
            detail="por adulto equivalente · GBA"
            period={fmtPeriod(data.cbt.period)}
          />
        )}
      </div>

      {data.food_vs_wages && (
        <div className="card" style={{ padding: 22 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 18, flexWrap: "wrap", gap: 12 }}>
            <div>
              <h2>IPC Alimentos vs. salarios</h2>
              <div className="subtle" style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2 }}>
                Últimos 24 meses · base 100 en el primer mes · si la línea de precios queda arriba, el salario compra menos
              </div>
            </div>
            <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
              <LegendDot color="var(--bad)" label="IPC Alimentos" />
              <LegendDot color="var(--primary)" label="Salarios" />
            </div>
          </div>
          <DualLineChart
            labels={data.food_vs_wages.labels}
            a={data.food_vs_wages.ipc_alimentos}
            b={data.food_vs_wages.salarios}
            aLabel="IPC Alimentos"
            bLabel="Salarios"
            aColor="var(--bad)"
            bColor="var(--primary)"
            height={260}
          />
        </div>
      )}
    </div>
  );
}
