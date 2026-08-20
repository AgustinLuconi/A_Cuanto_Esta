import axios from "axios";
import { z } from "zod";
import { env } from "@/lib/env";
import {
  EconomicContextSchema,
  EconomicIndicatorSchema,
  LocationCoverageSchema,
  PriceHistoryRecordSchema,
  ProductCountSchema,
  ProductListSchema,
  ProductWithPricesSchema,
  SupermarketLogosSchema,
  type EconomicContext,
  type LocationCoverage,
  type PriceHistoryRecord,
  type ProductCategory,
  type ProductCount,
  type ProductList,
  type ProductWithPrices,
  type SupermarketLogos,
} from "@/types";

const api = axios.create({
  baseURL: env.NEXT_PUBLIC_API_URL,
});

export async function getProductCount(
  category?: ProductCategory
): Promise<ProductCount> {
  const params = category ? { category } : {};
  const { data } = await api.get("/products/count", { params });
  return ProductCountSchema.parse(data);
}

export type SortOrder = "relevance" | "price_asc" | "price_desc" | "variation";

export async function searchProducts(
  q: string,
  category?: ProductCategory,
  skip = 0,
  limit = 50,
  sort: SortOrder = "relevance",
  priceMin?: number,
  priceMax?: number,
  variationFilter?: "down" | "low" | "high",
  supermarkets?: string[],
  brand?: string,
  onlyOnSale?: boolean,
  onlyInStock?: boolean,
  minDiscount?: number
): Promise<ProductList> {
  const searchParams = new URLSearchParams({
    q,
    limit: String(limit),
    skip: String(skip),
    sort,
  });
  if (category) searchParams.append("category", category);
  if (priceMin !== undefined) searchParams.append("price_min", String(priceMin));
  if (priceMax !== undefined) searchParams.append("price_max", String(priceMax));
  if (variationFilter) searchParams.append("variation_filter", variationFilter);
  if (brand) searchParams.append("brand", brand);
  if (onlyOnSale) searchParams.append("only_on_sale", "true");
  if (onlyInStock) searchParams.append("only_in_stock", "true");
  if (minDiscount !== undefined) searchParams.append("min_discount", String(minDiscount));

  if (supermarkets && supermarkets.length > 0) {
    for (const sm of supermarkets) {
      searchParams.append("supermarkets", sm);
    }
  }

  const { data } = await api.get(`/products/search?${searchParams.toString()}`);
  return ProductListSchema.parse(data);
}

export async function getProductsList(
  category?: ProductCategory,
  limit = 50,
  skip = 0,
  sort: SortOrder = "relevance"
): Promise<ProductList> {
  const params: Record<string, string> = { limit: String(limit), skip: String(skip), sort };
  if (category) params.category = category;
  const { data } = await api.get("/products", { params });
  return ProductListSchema.parse(data);
}

export async function getProduct(id: string): Promise<ProductWithPrices> {
  const { data } = await api.get(`/products/${encodeURIComponent(id)}`);
  return ProductWithPricesSchema.parse(data);
}

export async function getPriceHistory(
  productId: string,
  days = 90
): Promise<PriceHistoryRecord[]> {
  try {
    const { data } = await api.get(
      `/products/${encodeURIComponent(productId)}/prices/history?days=${days}`
    );
    return z.array(PriceHistoryRecordSchema).parse(data);
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      return [];
    }
    throw err;
  }
}

export async function getEconomicContext(): Promise<EconomicContext> {
  const { data } = await api.get("/economic/context");
  return EconomicContextSchema.parse(data);
}

export async function getInflationHistory(
  months = 12,
  type: "monthly" | "yearly" = "monthly"
): Promise<Array<{ date: string; value: number }>> {
  const { data } = await api.get(
    `/economic/inflation/history?months=${months}&type=${type}`
  );
  const parsed = z.array(EconomicIndicatorSchema).parse(data);
  return parsed.map((r) => ({
    date: r.date,
    value: parseFloat(String(r.value)),
  }));
}

const DollarHistorySchema = z.object({
  labels: z.array(z.string()),
  blue: z.array(z.number()),
  oficial: z.array(z.number()),
});

export async function getDollarHistory(months = 6): Promise<{
  labels: string[];
  blue: number[];
  oficial: number[];
}> {
  const { data } = await api.get(`/economic/dollar/history?months=${months}`);
  return DollarHistorySchema.parse(data);
}

export async function getRiskCountryHistory(
  months = 12
): Promise<Array<{ date: string; value: number }>> {
  const { data } = await api.get(`/economic/risk-country/history?months=${months}`);
  const parsed = z.array(EconomicIndicatorSchema).parse(data);
  return parsed.map((r) => ({
    date: r.date,
    value: parseFloat(String(r.value)),
  }));
}

export async function getLocationCoverage(): Promise<LocationCoverage> {
  const { data } = await api.get("/locations/coverage");
  return LocationCoverageSchema.parse(data);
}

export async function getSupermarketLogos(): Promise<SupermarketLogos> {
  const { data } = await api.get("/supermarkets/logos");
  return SupermarketLogosSchema.parse(data);
}

export async function getProductFacets(q?: string): Promise<Record<string, number>> {
  const params: Record<string, string> = {};
  if (q) params.q = q;
  const { data } = await api.get("/products/facets", { params });
  return z.record(z.string(), z.number()).parse(data);
}
