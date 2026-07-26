"use client";

import { useQuery } from "@tanstack/react-query";
import { getEconomicContext } from "@/lib/api";
import { AlertTriangle } from "lucide-react";

const MESES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

function fmt(v: number | null | undefined, decimals = 1): string {
  if (v == null) return "—";
  return new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(v);
}

function fmtARS(v: number | null | undefined): string {
  if (v == null) return "—";
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(v);
}

function mesAnio(isoDate: string | null): string {
  if (!isoDate) return "último dato";
  const [year, month] = isoDate.split("-").map(Number);
  return `${MESES[month - 1]} ${year}`;
}

export function ChangeBadge({ value }: { value: number | null | undefined }) {
  if (value == null) return null;
  const isPositive = value > 0;
  const arrow = isPositive ? "↑" : "↓";
  const sign = isPositive ? "+" : "";
  const colorClass = isPositive
    ? "bg-red-100 text-red-700"
    : "bg-green-100 text-green-700";
  return (
    <span
      className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium ${colorClass}`}
    >
      {arrow} {sign}{fmt(value)}%
    </span>
  );
}

interface RowProps {
  label: string;
  source: string;
  value: string;
  badge?: React.ReactNode;
  subtitle: string;
}

function IndicatorRow({ label, source, value, badge, subtitle }: RowProps) {
  return (
    <div className="px-4 py-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-neutral">{label}</span>
        <span className="text-xs text-neutral/50">{source}</span>
      </div>
      <div className="flex items-center gap-2 mb-0.5">
        <span className="text-xl font-bold text-primary tabular-nums leading-tight">
          {value}
        </span>
        {badge}
      </div>
      <span className="text-xs text-neutral/60">{subtitle}</span>
    </div>
  );
}

export default function EconomicSidebar() {
  const { data, isLoading } = useQuery({
    queryKey: ["economic", "context"],
    queryFn: getEconomicContext,
  });

  if (isLoading) {
    return (
      <aside className="w-80 shrink-0">
        <div className="bg-surface rounded-xl border border-border p-4 space-y-3 animate-pulse">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-border rounded" />
          ))}
        </div>
      </aside>
    );
  }

  const inflSource = `INDEC · ${mesAnio(data?.inflation_monthly_date ?? null)}`;
  const yearLabel = new Date().getFullYear();
  const showAccumulatedCard =
    data?.inflation_ytd != null || data?.inflation_yearly != null;

  return (
    <aside className="w-80 shrink-0">
      <div className="bg-surface rounded-xl border border-border overflow-hidden sticky top-20">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <span className="font-semibold text-sm text-primary">
            Hoy en Argentina
          </span>
          <a
            href="/economia"
            className="text-xs text-neutral hover:text-primary transition-colors"
          >
            Ver todo →
          </a>
        </div>

        <div className="divide-y divide-border">
          <IndicatorRow
            label="Inflación mensual"
            source={inflSource}
            value={`${fmt(data?.inflation_monthly)}%`}
            badge={<ChangeBadge value={data?.inflation_monthly_change} />}
            subtitle="vs. mes anterior"
          />
          <IndicatorRow
            label="Dólar blue"
            source="Promedio paralelo"
            value={fmtARS(data?.dollar_blue)}
            badge={<ChangeBadge value={data?.dollar_blue_change} />}
            subtitle="últimas 24 hs"
          />
          <IndicatorRow
            label="Dólar oficial"
            source="BCRA"
            value={fmtARS(data?.dollar_oficial)}
            badge={<ChangeBadge value={data?.dollar_oficial_change} />}
            subtitle="últimas 24 hs"
          />
          <IndicatorRow
            label="Riesgo país"
            source="JP Morgan EMBI+"
            value={data?.risk_country != null ? `${fmt(data.risk_country, 0)} pb` : "—"}
            badge={<ChangeBadge value={data?.risk_country_change} />}
            subtitle="últimas 24 hs"
          />
        </div>

        {showAccumulatedCard && (
          <div className="m-3 bg-amber-50 border border-amber-200 rounded-lg p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <AlertTriangle size={14} className="text-amber-600 shrink-0" />
              <span className="text-xs font-semibold text-amber-800">
                Inflación acumulada {yearLabel}
              </span>
            </div>
            <div className="flex items-baseline gap-1.5 mb-1">
              <span className="text-2xl font-bold text-amber-900 tabular-nums leading-none">
                {fmt(data?.inflation_ytd ?? data?.inflation_yearly)}%
              </span>
              <span className="text-xs text-amber-700">en lo que va del año</span>
            </div>
            {data?.inflation_yearly != null && (
              <p className="text-xs text-amber-700">
                Últimos 12 meses:{" "}
                <span className="font-semibold">{fmt(data.inflation_yearly)}%</span>
              </p>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
