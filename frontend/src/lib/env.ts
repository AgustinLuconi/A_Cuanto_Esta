import { z } from "zod";

const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url().default("http://localhost:8000/api/v1"),
  NEXT_PUBLIC_SITE_URL: z.string().url().default("http://localhost:3000"),
});

// NEXT_PUBLIC_SITE_URL: si no se define explícitamente, usamos VERCEL_URL
// (inyectada automáticamente por Vercel, sin protocolo) para que metadata/
// sitemap/robots tengan una URL absoluta razonable incluso en preview
// deployments. En local cae a localhost:3000.
const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ||
  (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "http://localhost:3000");

export const env = envSchema.parse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  NEXT_PUBLIC_SITE_URL: siteUrl,
});
