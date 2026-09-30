import type { Metadata } from "next";
import { env } from "@/lib/env";
import { ProductWithPricesSchema } from "@/types";
import ProductDetailClient from "./ProductDetailClient";

async function fetchProductForMetadata(id: string) {
  try {
    const res = await fetch(`${env.NEXT_PUBLIC_API_URL}/products/${encodeURIComponent(id)}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return ProductWithPricesSchema.parse(await res.json());
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const product = await fetchProductForMetadata(id);
  if (!product) {
    return { title: "Producto no encontrado" };
  }

  const title = `${product.full_name} — Comparar precios`;
  const description = product.lowest_price != null
    ? `${product.full_name}: desde $${product.lowest_price.toLocaleString("es-AR")} en ${product.current_prices.length} supermercado${product.current_prices.length === 1 ? "" : "s"}. Compará precios en tiempo real en ¿A Cuánto Está?`
    : `Compará precios de ${product.full_name} entre los principales supermercados de Argentina.`;

  return {
    title,
    description,
    alternates: { canonical: `/producto/${product.id}` },
    openGraph: {
      title,
      description,
      type: "website",
      images: product.image_url ? [{ url: product.image_url }] : undefined,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: product.image_url ? [product.image_url] : undefined,
    },
  };
}

export default async function ProductoPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await fetchProductForMetadata(id);

  const jsonLd = product ? {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.full_name,
    image: product.image_url ?? undefined,
    brand: product.brand ? { "@type": "Brand", name: product.brand } : undefined,
    gtin: product.barcode ?? undefined,
    ...(product.current_prices.length > 0 && product.lowest_price != null
      ? {
          offers: {
            "@type": "AggregateOffer",
            priceCurrency: "ARS",
            lowPrice: product.lowest_price,
            highPrice: product.highest_price ?? product.lowest_price,
            offerCount: product.current_prices.length,
            availability: product.current_prices.some((p) => p.in_stock)
              ? "https://schema.org/InStock"
              : "https://schema.org/OutOfStock",
          },
        }
      : {}),
  } : null;

  return (
    <>
      {jsonLd && (
        <script
          type="application/ld+json"
          // Datos de producto scrapeados de sitios externos: escapamos "<" para que un
          // nombre de producto con "</script>" no pueda cerrar el tag antes de tiempo.
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
        />
      )}
      <ProductDetailClient id={id} />
    </>
  );
}
