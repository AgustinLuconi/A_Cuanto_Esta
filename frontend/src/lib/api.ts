import axios from "axios";
import type {
  EconomicContext,
  EconomicIndicator,
  PriceHistoryRecord,
  ProductCategory,
  ProductCount,
  ProductList,
  ProductWithPrices,
  SupermarketLogos,
} from "@/types";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

export async function getProductCount(
  category?: ProductCategory
): Promise<ProductCount> {
  const params = category ? { category } : {};
  const { data } = await api.get<ProductCount>("/products/count", { params });
  return data;
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
  variationFilter?: "down" | "low" | "high"
): Promise<ProductList> {
  const params: Record<string, string> = { q, limit: String(limit), skip: String(skip), sort };
  if (category) params.category = category;
  if (priceMin !== undefined) params.price_min = String(priceMin);
  if (priceMax !== undefined) params.price_max = String(priceMax);
  if (variationFilter) params.variation_filter = variationFilter;
  const { data } = await api.get<ProductList>("/products/search", { params });
  return data;
}

export async function getProductsList(
  category?: ProductCategory,
  limit = 50,
  skip = 0,
  sort: SortOrder = "relevance"
): Promise<ProductList> {
  const params: Record<string, string> = { limit: String(limit), skip: String(skip), sort };
  if (category) params.category = category;
  const { data } = await api.get<ProductList>("/products", { params });
  return data;
}

export async function getProduct(id: string): Promise<ProductWithPrices> {
  const { data } = await api.get<ProductWithPrices>(`/products/${id}`);
  return data;
}

export async function getPriceHistory(
  productId: string,
  days = 90
): Promise<PriceHistoryRecord[]> {
  try {
    const { data } = await api.get<PriceHistoryRecord[]>(
      `/products/${productId}/prices/history?days=${days}`
    );
    return data;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      return [];
    }
    throw err;
  }
}

export async function getEconomicContext(): Promise<EconomicContext> {
  const { data } = await api.get<EconomicContext>("/economic/context");
  return data;
}

export async function getInflationHistory(
  months = 12,
  type: "monthly" | "yearly" = "monthly"
): Promise<Array<{ date: string; value: number }>> {
  const { data } = await api.get<EconomicIndicator[]>(
    `/economic/inflation/history?months=${months}&type=${type}`
  );
  return data.map((r) => ({
    date: r.date,
    value: parseFloat(String(r.value)),
  }));
}

export async function getDollarHistory(months = 6): Promise<{
  labels: string[];
  blue: number[];
  oficial: number[];
}> {
  const { data } = await api.get<{ labels: string[]; blue: number[]; oficial: number[] }>(
    `/economic/dollar/history?months=${months}`
  );
  return data;
}

export async function getRiskCountryHistory(
  months = 12
): Promise<Array<{ date: string; value: number }>> {
  const { data } = await api.get<EconomicIndicator[]>(
    `/economic/risk-country/history?months=${months}`
  );
  return data.map((r) => ({
    date: r.date,
    value: parseFloat(String(r.value)),
  }));
}

export async function getLocationCoverage(): Promise<unknown> {
  const { data } = await api.get("/locations/coverage");
  return data;
}

export async function getSupermarketLogos(): Promise<SupermarketLogos> {
  const { data } = await api.get<SupermarketLogos>("/supermarkets/logos");
  return data;
}

export async function getProductFacets(q?: string): Promise<Record<string, number>> {
  const params: Record<string, string> = {};
  if (q) params.q = q;
  const { data } = await api.get<Record<string, number>>("/products/facets", { params });
  return data;
}
