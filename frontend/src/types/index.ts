export type Supermarket =
  | "carrefour"
  | "coto"
  | "disco"
  | "atomo"
  | "vea"
  | "jumbo"
  | "dia"
  | "la_anonima"
  | "chango_mas";

export type ProductCategory =
  | "alimentos"
  | "bebidas"
  | "limpieza"
  | "higiene_personal"
  | "lacteos"
  | "carnes"
  | "frutas_verduras"
  | "panaderia"
  | "congelados"
  | "snacks"
  | "desayuno"
  | "otros";

export type ProductUnit = "kg" | "g" | "l" | "ml" | "unidad" | "pack";

export interface Product {
  id: string;
  name: string;
  normalized_name: string;
  brand: string | null;
  category: ProductCategory;
  unit: ProductUnit;
  quantity: string | null;
  description: string | null;
  image_url: string | null;
  barcode: string | null;
  created_at: string;
  updated_at: string;
  full_name: string;
}

export interface CurrentPrice {
  supermarket: Supermarket;
  price: number;
  was_on_sale: boolean;
  original_price: number | null;
  discount_percentage: number | null;
  url: string | null;
  last_updated: string;
  in_stock: boolean;
  province: string | null;
  region: string | null;
  product_image_url: string | null;
}

export interface PriceHistoryRecord {
  id: string;
  product_id: string;
  supermarket: Supermarket;
  price: number;
  was_on_sale: boolean;
  original_price: number | null;
  discount_percentage: number | null;
  url: string | null;
  in_stock: boolean;
  scraped_at: string;
}

export interface ProductWithPrices extends Product {
  current_prices: CurrentPrice[];
  lowest_price: number | null;
  highest_price: number | null;
  price_difference: number | null;
}

export interface EconomicContext {
  inflation_monthly: number | null;
  inflation_yearly: number | null;
  dollar_blue: number | null;
  dollar_oficial: number | null;
  dollar_mayorista: number | null;
  dollar_mep: number | null;
  dollar_ccl: number | null;
  dollar_cripto: number | null;
  dollar_tarjeta: number | null;
  uva_index: number | null;
  plazo_fijo_rate: number | null;
  risk_country: number | null;
  last_updated: string;
  inflation_monthly_change: number | null;
  inflation_monthly_date: string | null;
  dollar_blue_change: number | null;
  dollar_oficial_change: number | null;
  dollar_mayorista_change: number | null;
  dollar_mep_change: number | null;
  dollar_ccl_change: number | null;
  dollar_cripto_change: number | null;
  dollar_tarjeta_change: number | null;
  risk_country_change: number | null;
  inflation_ytd: number | null;
}

export interface EconomicIndicator {
  id: string;
  indicator_type: string;
  value: string | number;
  date: string;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface ProductList {
  items: Product[];
  total: number;
  skip: number;
  limit: number;
  supermarket_counts?: Record<string, number>;
  variation_counts?: Record<string, number>;
}

export interface ProductCount {
  count: number;
}

export type SupermarketLogos = Record<Supermarket, string>;
