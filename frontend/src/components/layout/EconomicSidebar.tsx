function fmt(v: number | null | undefined, decimals = 1): string {
  if (v == null) return "—";
  return new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(v);
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
