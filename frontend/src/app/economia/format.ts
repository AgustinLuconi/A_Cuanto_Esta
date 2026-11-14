// "2026-10-01" -> "oct 2026". Se fuerza UTC para que la zona horaria local no
// corra el primer día del mes al mes anterior.
export function fmtPeriod(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("es-AR", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}
