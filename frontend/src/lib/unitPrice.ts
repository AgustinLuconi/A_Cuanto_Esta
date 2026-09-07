import type { ProductUnit } from "@/types";

// Convierte unit+quantity a una cantidad normalizada (kg, L, o cantidad de
// unidades) para poder calcular precio por unidad de medida. `quantity` es
// texto libre que viene de los scrapers (ej. "1kg", "100g", "1L", "1un",
// "100") — casi siempre un número seguido opcionalmente de la unidad misma.
function parseQuantity(quantity: string): number | null {
  const match = quantity.match(/[\d.,]+/);
  if (!match) return null;
  const n = parseFloat(match[0].replace(",", "."));
  return Number.isFinite(n) && n > 0 ? n : null;
}

export interface UnitPriceResult {
  value: number;
  label: string; // "kg" | "L" | "u"
}

/**
 * Precio por unidad de medida (kg, L) o por unidad individual, solo cuando
 * el dato de cantidad alcanza para calcularlo con sentido. Devuelve `null`
 * si no hay cantidad registrada (la mayoría del catálogo no la tiene) o si
 * mostrarlo no aportaría nada (ej. "1 unidad" — precio por unidad = precio).
 */
export function computeUnitPrice(
  price: number,
  unit: ProductUnit,
  quantity: string | null
): UnitPriceResult | null {
  if (!quantity) return null;
  const qty = parseQuantity(quantity);
  if (!qty) return null;

  switch (unit) {
    case "kg":
      return { value: price / qty, label: "kg" };
    case "g":
      return { value: price / (qty / 1000), label: "kg" };
    case "l":
      return { value: price / qty, label: "L" };
    case "ml":
      return { value: price / (qty / 1000), label: "L" };
    case "unidad":
    case "pack":
      // Solo tiene sentido mostrarlo si el paquete trae más de 1 unidad —
      // con qty=1 el precio por unidad es idéntico al precio ya mostrado.
      return qty > 1 ? { value: price / qty, label: "u" } : null;
    default:
      return null;
  }
}
