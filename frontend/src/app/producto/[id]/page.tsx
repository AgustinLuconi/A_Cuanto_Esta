import Link from "next/link";

export default function ProductoPage({ params }: { params: { id: string } }) {
  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center space-y-4">
      <p className="text-5xl">🚧</p>
      <h1 className="text-2xl font-bold text-primary">
        Detalle de producto — próximamente
      </h1>
      <p className="text-neutral text-sm">
        Producto ID: <code className="bg-border px-1 py-0.5 rounded text-xs">{params.id}</code>
      </p>
      <Link href="/resultados" className="inline-block text-sm text-primary hover:underline mt-4">
        ← Volver a resultados
      </Link>
    </main>
  );
}
