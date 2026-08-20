import { z } from "zod";

// Single Source of Truth Arrays using `as const`
export const SUPERMARKETS = [
  "carrefour",
  "coto",
  "disco",
  "atomo",
  "vea",
  "jumbo",
  "dia",
  "la_anonima",
  "chango_mas",
] as const;

export const PRODUCT_CATEGORIES = [
  "alimentos",
  "bebidas",
  "limpieza",
  "higiene_personal",
  "lacteos",
  "carnes",
  "frutas_verduras",
  "panaderia",
  "congelados",
  "snacks",
  "desayuno",
  "otros",
] as const;

export const PRODUCT_UNITS = ["kg", "g", "l", "ml", "unidad", "pack"] as const;

// Zod Schemas
export const SupermarketSchema = z.enum(SUPERMARKETS);
export type Supermarket = z.infer<typeof SupermarketSchema>;

export const ProductCategorySchema = z.enum(PRODUCT_CATEGORIES);
export type ProductCategory = z.infer<typeof ProductCategorySchema>;

export const ProductUnitSchema = z.enum(PRODUCT_UNITS);
export type ProductUnit = z.infer<typeof ProductUnitSchema>;

export const ProductSchema = z.object({
  id: z.string(),
  name: z.string(),
  normalized_name: z.string(),
  brand: z.string().nullable().default(null),
  category: ProductCategorySchema,
  unit: ProductUnitSchema,
  quantity: z.string().nullable().default(null),
  description: z.string().nullable().default(null),
  image_url: z.string().nullable().default(null),
  barcode: z.string().nullable().default(null),
  created_at: z.string(),
  updated_at: z.string(),
  full_name: z.string(),
});
export type Product = z.infer<typeof ProductSchema>;

export const CurrentPriceSchema = z.object({
  supermarket: SupermarketSchema,
  price: z.number(),
  was_on_sale: z.boolean().default(false),
  original_price: z.number().nullable().default(null),
  discount_percentage: z.number().nullable().default(null),
  url: z.string().nullable().default(null),
  last_updated: z.string(),
  in_stock: z.boolean().default(true),
  province: z.string().nullable().default(null),
  region: z.string().nullable().default(null),
  product_image_url: z.string().nullable().default(null),
});
export type CurrentPrice = z.infer<typeof CurrentPriceSchema>;

export const PriceHistoryRecordSchema = z.object({
  id: z.string(),
  product_id: z.string(),
  supermarket: SupermarketSchema,
  price: z.preprocess((val) => Number(val), z.number()),
  was_on_sale: z.boolean().default(false),
  original_price: z.number().nullable().default(null),
  discount_percentage: z.number().nullable().default(null),
  url: z.string().nullable().default(null),
  in_stock: z.boolean().default(true),
  scraped_at: z.string(),
});
export type PriceHistoryRecord = z.infer<typeof PriceHistoryRecordSchema>;

export const ProductWithPricesSchema = ProductSchema.extend({
  current_prices: z.array(CurrentPriceSchema).default([]),
  lowest_price: z.number().nullable().default(null),
  highest_price: z.number().nullable().default(null),
  price_difference: z.number().nullable().default(null),
});
export type ProductWithPrices = z.infer<typeof ProductWithPricesSchema>;

export const EconomicContextSchema = z.object({
  inflation_monthly: z.number().nullable().default(null),
  inflation_yearly: z.number().nullable().default(null),
  dollar_blue: z.number().nullable().default(null),
  dollar_oficial: z.number().nullable().default(null),
  dollar_mayorista: z.number().nullable().default(null),
  dollar_mep: z.number().nullable().default(null),
  dollar_ccl: z.number().nullable().default(null),
  dollar_cripto: z.number().nullable().default(null),
  dollar_tarjeta: z.number().nullable().default(null),
  uva_index: z.number().nullable().default(null),
  plazo_fijo_rate: z.number().nullable().default(null),
  risk_country: z.number().nullable().default(null),
  last_updated: z.string(),
  inflation_monthly_change: z.number().nullable().default(null),
  inflation_monthly_date: z.string().nullable().default(null),
  dollar_blue_change: z.number().nullable().default(null),
  dollar_oficial_change: z.number().nullable().default(null),
  dollar_mayorista_change: z.number().nullable().default(null),
  dollar_mep_change: z.number().nullable().default(null),
  dollar_ccl_change: z.number().nullable().default(null),
  dollar_cripto_change: z.number().nullable().default(null),
  dollar_tarjeta_change: z.number().nullable().default(null),
  risk_country_change: z.number().nullable().default(null),
  inflation_ytd: z.number().nullable().default(null),
});
export type EconomicContext = z.infer<typeof EconomicContextSchema>;

export const EconomicIndicatorSchema = z.object({
  id: z.string(),
  indicator_type: z.string(),
  value: z.union([z.string(), z.number()]),
  date: z.string(),
  source: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type EconomicIndicator = z.infer<typeof EconomicIndicatorSchema>;

export const ProductListSchema = z.object({
  items: z.array(ProductSchema),
  total: z.number(),
  skip: z.number(),
  limit: z.number(),
  supermarket_counts: z.record(z.string(), z.number()).optional(),
  variation_counts: z.record(z.string(), z.number()).optional(),
});
export type ProductList = z.infer<typeof ProductListSchema>;

export const ProductCountSchema = z.object({
  count: z.number(),
});
export type ProductCount = z.infer<typeof ProductCountSchema>;

export const SupermarketLogosSchema = z.record(SupermarketSchema, z.string());
export type SupermarketLogos = z.infer<typeof SupermarketLogosSchema>;

export const LocationCoverageSchema = z.record(z.string(), z.unknown());
export type LocationCoverage = z.infer<typeof LocationCoverageSchema>;
