"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

export default function SearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    router.push(`/resultados?q=${encodeURIComponent(trimmed)}`);
  }

  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-2xl">
      <div className="relative flex items-center">
        <Search
          size={20}
          className="absolute left-4 text-neutral pointer-events-none"
        />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscá un producto, marca o código de barras..."
          className="w-full pl-12 pr-4 py-3.5 bg-surface border border-border rounded-xl text-primary placeholder:text-neutral focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors text-sm"
        />
        <button
          type="submit"
          className="absolute right-2 px-4 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary/90 transition-colors"
        >
          Buscar
        </button>
      </div>
    </form>
  );
}
