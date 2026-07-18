"use client";

import { useQuery } from "@tanstack/react-query";
import { getProductCount } from "@/lib/api";

export default function ProductCountBadge() {
  const { data } = useQuery({
    queryKey: ["products", "count"],
    queryFn: () => getProductCount(),
  });

  if (!data) return <span className="text-primary font-semibold">miles de</span>;

  return (
    <span className="text-primary font-semibold">
      {new Intl.NumberFormat("es-AR").format(data.count)}
    </span>
  );
}
