import type { MetadataRoute } from "next";
import { env } from "@/lib/env";
import { getProductSitemapIds } from "@/lib/api";

export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = env.NEXT_PUBLIC_SITE_URL;

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: `${base}/`, changeFrequency: "daily", priority: 1 },
    { url: `${base}/resultados`, changeFrequency: "hourly", priority: 0.8 },
    { url: `${base}/economia`, changeFrequency: "daily", priority: 0.6 },
  ];

  let productRoutes: MetadataRoute.Sitemap = [];
  try {
    const products = await getProductSitemapIds();
    productRoutes = products.map((p) => ({
      url: `${base}/producto/${p.id}`,
      lastModified: p.updated_at,
      changeFrequency: "daily" as const,
      priority: 0.5,
    }));
  } catch {
    // Si el backend no responde, publicamos igual el sitemap con las rutas
    // estáticas — mejor un sitemap parcial que ninguno.
  }

  return [...staticRoutes, ...productRoutes];
}
