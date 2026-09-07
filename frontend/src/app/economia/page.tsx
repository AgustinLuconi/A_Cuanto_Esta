import type { Metadata } from "next";
import EconomiaContent from "./EconomiaContent";

export const metadata: Metadata = {
  title: "Dashboard económico",
  description:
    "Inflación, cotización del dólar, riesgo país y variación de precios por categoría en Argentina, actualizados en tiempo real.",
};

export default function EconomiaPage() {
  return <EconomiaContent />;
}
