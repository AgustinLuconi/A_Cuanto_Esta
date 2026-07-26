import type { PriceHistoryRecord } from "@/types";

export function buildPriceChartData(records: PriceHistoryRecord[]): {
  labels: string[];
  series: Record<string, number[]>;
} {
  // 1. Agrupar por supermercado -> día (YYYY-MM-DD) -> {price, scraped_at}
  //    Si hay más de un registro el mismo día, se queda con el de scraped_at más reciente.
  const bySuper = new Map<string, Map<string, { price: number; scrapedAt: string }>>();
  for (const r of records) {
    const day = r.scraped_at.slice(0, 10);
    if (!bySuper.has(r.supermarket)) bySuper.set(r.supermarket, new Map());
    const dayMap = bySuper.get(r.supermarket)!;
    const existing = dayMap.get(day);
    if (!existing || r.scraped_at > existing.scrapedAt) {
      dayMap.set(day, { price: r.price, scrapedAt: r.scraped_at });
    }
  }

  // 2. Unión de días de todos los supermercados, ordenados ascendente
  const allDays = new Set<string>();
  for (const dayMap of bySuper.values()) {
    for (const day of dayMap.keys()) allDays.add(day);
  }
  const labels = Array.from(allDays).sort();

  // 3. Serie alineada por supermercado: precio exacto si existe ese día,
  //    forward-fill del último conocido si no, back-fill con el primer
  //    precio conocido para los días anteriores al primer registro.
  const series: Record<string, number[]> = {};
  for (const [supermarket, dayMap] of bySuper.entries()) {
    const sortedDays = Array.from(dayMap.keys()).sort();
    const firstKnownPrice = dayMap.get(sortedDays[0])!.price;
    let lastKnown = firstKnownPrice;
    const values: number[] = [];
    for (const day of labels) {
      const entry = dayMap.get(day);
      if (entry) {
        lastKnown = entry.price;
        values.push(entry.price);
      } else {
        values.push(lastKnown);
      }
    }
    series[supermarket] = values;
  }

  return { labels, series };
}

export function buildInflationFactors(
  labels: string[],
  inflationMonthly: Array<{ date: string; value: number }>
): number[] {
  if (labels.length === 0) return [];

  // Factor acumulado compuesto por mes (YYYY-MM), caminando cronológicamente
  const sorted = [...inflationMonthly].sort((a, b) => a.date.localeCompare(b.date));
  const factorByMonth = new Map<string, number>();
  let cumulative = 1;
  for (const rec of sorted) {
    cumulative *= 1 + rec.value / 100;
    factorByMonth.set(rec.date.slice(0, 7), cumulative);
  }

  // Normalizar: el mes del primer label lee como 1.0
  const baseMonth = labels[0].slice(0, 7);
  const baseFactor = factorByMonth.get(baseMonth) ?? 1;

  return labels.map((day) => {
    const month = day.slice(0, 7);
    const factor = factorByMonth.get(month);
    return factor != null ? factor / baseFactor : 1;
  });
}
