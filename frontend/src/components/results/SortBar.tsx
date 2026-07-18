"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";

const SORT_OPTIONS = [
  { value: "relevancia", label: "Relevancia" },
  { value: "precio_asc", label: "Precio ↑" },
  { value: "precio_desc", label: "Precio ↓" },
];

export default function SortBar({ total }: { total: number }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const currentSort = searchParams.get("orden") ?? "relevancia";

  function setSort(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("orden", value);
    router.push(`${pathname}?${params.toString()}`);
  }

  return (
    <div className="flex items-center justify-between">
      <p className="text-sm text-neutral">
        <span className="font-medium text-primary tabular-nums">
          {new Intl.NumberFormat("es-AR").format(total)}
        </span>{" "}
        {total === 1 ? "producto" : "productos"}
      </p>
      <div className="flex items-center gap-1">
        <span className="text-xs text-neutral mr-1">Ordenar:</span>
        {SORT_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setSort(opt.value)}
            className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${
              currentSort === opt.value
                ? "bg-primary text-white"
                : "bg-surface border border-border text-neutral hover:text-primary hover:border-primary/40"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
