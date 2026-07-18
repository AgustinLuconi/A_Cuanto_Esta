import Link from "next/link";

const TRENDING = [
  { name: "Aceite girasol", variation: +18.5 },
  { name: "Leche entera 1L", variation: -3.2 },
  { name: "Yerba mate 500g", variation: +12.0 },
  { name: "Pollo entero", variation: +8.7 },
  { name: "Pan lactal", variation: +5.4 },
  { name: "Detergente 500ml", variation: -1.8 },
];

export default function TrendingChips() {
  return (
    <div className="flex flex-wrap gap-2">
      {TRENDING.map((item) => {
        const isUp = item.variation > 0;
        const isDown = item.variation < 0;
        return (
          <Link
            key={item.name}
            href={`/resultados?q=${encodeURIComponent(item.name)}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-surface border border-border rounded-full text-sm hover:border-primary/40 hover:bg-primary/5 transition-colors"
          >
            <span className="text-primary">{item.name}</span>
            <span
              className={`text-xs tabular-nums font-medium ${
                isUp ? "text-up" : isDown ? "text-down" : "text-neutral"
              }`}
            >
              {isUp ? "+" : ""}
              {item.variation.toFixed(1)}%
            </span>
          </Link>
        );
      })}
    </div>
  );
}
