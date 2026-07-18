/* global React */
// Mock data for "A Cuanto Está"

const SUPERMARKETS = [
  { id: "coto",      name: "Coto",        short: "CO", color: "var(--sm-1)", coverage: "Nacional" },
  { id: "atomo",     name: "Átomo",       short: "AT", color: "var(--sm-2)", coverage: "Cuyo" },
  { id: "carrefour", name: "Carrefour",   short: "CA", color: "var(--sm-3)", coverage: "Nacional" },
  { id: "vea",       name: "Vea",         short: "VE", color: "var(--sm-4)", coverage: "AMBA + Cuyo" },
  { id: "disco",     name: "Disco",       short: "DI", color: "var(--sm-5)", coverage: "AMBA" },
  { id: "jumbo",     name: "Jumbo",       short: "JU", color: "var(--sm-6)", coverage: "Nacional" },
  { id: "dia",       name: "Día",         short: "DA", color: "var(--sm-7)", coverage: "AMBA + Centro" },
  { id: "anonima",   name: "La Anónima",  short: "LA", color: "var(--sm-8)", coverage: "Patagonia + NOA" },
  { id: "changomas", name: "Chango Más",  short: "CM", color: "var(--sm-9)", coverage: "Nacional" },
];

const SM_BY_ID = Object.fromEntries(SUPERMARKETS.map(s => [s.id, s]));

const REGIONS = [
  { id: "amba",      name: "AMBA",          provs: ["CABA", "Buenos Aires"], coverage: 0.94 },
  { id: "pampeana",  name: "Pampeana",      provs: ["Buenos Aires", "Córdoba", "Santa Fe", "La Pampa", "Entre Ríos"], coverage: 0.88 },
  { id: "centro",    name: "Centro",        provs: ["Córdoba", "Santa Fe", "Entre Ríos"], coverage: 0.85 },
  { id: "cuyo",      name: "Cuyo",          provs: ["Mendoza", "San Juan", "San Luis"], coverage: 0.79 },
  { id: "noa",       name: "NOA",           provs: ["Salta", "Jujuy", "Tucumán", "Catamarca", "Santiago del Estero", "La Rioja"], coverage: 0.66 },
  { id: "nea",       name: "NEA",           provs: ["Misiones", "Corrientes", "Chaco", "Formosa"], coverage: 0.62 },
  { id: "patagonia", name: "Patagonia",     provs: ["Neuquén", "Río Negro", "Chubut", "Santa Cruz", "Tierra del Fuego"], coverage: 0.71 },
];

const CATEGORIES = [
  { id: "lacteos",     name: "Lácteos",         icon: "🥛", count: 412 },
  { id: "bebidas",     name: "Bebidas",         icon: "🥤", count: 528 },
  { id: "carnes",      name: "Carnes",          icon: "🥩", count: 187 },
  { id: "panificados", name: "Panificados",     icon: "🍞", count: 234 },
  { id: "limpieza",    name: "Limpieza",        icon: "🧴", count: 389 },
  { id: "higiene",     name: "Higiene personal",icon: "🧼", count: 298 },
  { id: "frutas",      name: "Frutas y verduras", icon: "🥬", count: 156 },
  { id: "congelados",  name: "Congelados",      icon: "🧊", count: 142 },
  { id: "almacen",     name: "Almacén",         icon: "🛒", count: 487 },
  { id: "snacks",      name: "Snacks",          icon: "🍪", count: 213 },
  { id: "mascotas",    name: "Mascotas",        icon: "🐾", count: 124 },
  { id: "otros",       name: "Otros",           icon: "📦", count: 125 },
];

// Search results for "leche entera" — products list
const PRODUCTS = [
  {
    id: "leche-serenisima-sachet",
    name: "Leche Entera Sachet 1L",
    brand: "La Serenísima",
    category: "Lácteos",
    barcode: "7790742000018",
    lowest: 1180,
    lowestAt: "dia",
    available: 9,
    var30: 0.08,
    var7: -0.02,
    spark: [1090, 1110, 1140, 1135, 1190, 1180, 1175, 1180],
  },
  {
    id: "leche-sancor-larga-vida",
    name: "Leche Entera Larga Vida 1L",
    brand: "Sancor",
    category: "Lácteos",
    barcode: "7790580031049",
    lowest: 1290,
    lowestAt: "anonima",
    available: 8,
    var30: 0.11,
    var7: 0.012,
    spark: [1150, 1175, 1190, 1210, 1240, 1270, 1280, 1290],
  },
  {
    id: "leche-armonia-descremada",
    name: "Leche Entera Cartón 1L",
    brand: "Armonía",
    category: "Lácteos",
    barcode: "7791234560001",
    lowest: 1395,
    lowestAt: "carrefour",
    available: 5,
    var30: 0.14,
    var7: 0.04,
    spark: [1200, 1230, 1260, 1290, 1320, 1360, 1380, 1395],
  },
  {
    id: "leche-serenisima-deslactosada",
    name: "Leche Entera Deslactosada 1L",
    brand: "La Serenísima",
    category: "Lácteos",
    barcode: "7790742000339",
    lowest: 1640,
    lowestAt: "coto",
    available: 7,
    var30: 0.06,
    var7: -0.012,
    spark: [1545, 1560, 1580, 1610, 1640, 1660, 1650, 1640],
  },
  {
    id: "leche-ilolay",
    name: "Leche Entera Botella 1L",
    brand: "Ilolay",
    category: "Lácteos",
    barcode: "7791234567890",
    lowest: 1310,
    lowestAt: "changomas",
    available: 6,
    var30: 0.095,
    var7: 0,
    spark: [1190, 1210, 1240, 1260, 1290, 1300, 1310, 1310],
  },
  {
    id: "leche-serenisima-2lt",
    name: "Leche Entera Sachet 2 unidades 1L",
    brand: "La Serenísima",
    category: "Lácteos",
    barcode: "7790742000056",
    lowest: 2280,
    lowestAt: "vea",
    available: 4,
    var30: 0.07,
    var7: -0.01,
    spark: [2120, 2150, 2200, 2230, 2260, 2290, 2285, 2280],
  },
];

// Detailed product (for screen 3) — La Serenísima Sachet 1L
const PRODUCT_DETAIL = {
  ...PRODUCTS[0],
  description: "Leche entera pasteurizada en sachet de 1 litro. Contiene 3% de materia grasa.",
  prices: [
    // 26-week history, weekly. Generated to be plausible.
    // Each row: ISO-week label, price per supermarket id.
    // We'll generate via function to keep this realistic.
  ],
};

// Generate 26 weeks of price history per supermarket
(function buildHistory() {
  const startDate = new Date(2025, 10, 23); // 6 months ago from "today" ~ may 23 2026
  startDate.setMonth(startDate.getMonth() - 6);
  const weeks = 26;
  const base = { // starting prices per supermarket Nov 23, 2025
    coto: 980, atomo: 940, carrefour: 1010, vea: 970, disco: 1030, jumbo: 1050, dia: 920, anonima: 990, changomas: 950
  };
  // Approx monthly inflation factors for Argentina-ish trajectory (illustrative, not real)
  const monthlyInflation = [0.038, 0.041, 0.029, 0.033, 0.025, 0.031]; // 6 months
  // weekly factors derived
  const weeklyInflation = monthlyInflation.flatMap(m => [m/4, m/4, m/4, m/4]);

  const series = {};
  Object.keys(base).forEach(k => series[k] = []);
  let infCum = 1;
  const infSeries = [];

  // final actual prices we want each supermarket to land at (close to today's value)
  const target = {
    coto: 1240, atomo: 1210, carrefour: 1395, vea: 1230, disco: 1310, jumbo: 1410, dia: 1180, anonima: 1290, changomas: 1310
  };

  Object.keys(base).forEach(k => {
    const arr = [];
    const totalGrowth = target[k] / base[k];
    for (let i = 0; i < weeks; i++) {
      const t = i / (weeks - 1);
      // s-curve growth + noise
      const ease = 0.5 - 0.5 * Math.cos(Math.PI * t);
      const noise = (Math.sin(i * (k.charCodeAt(0)) * 0.7) + Math.cos(i * (k.charCodeAt(1)||3) * 0.3)) * 0.012;
      const price = base[k] * (1 + (totalGrowth - 1) * ease) * (1 + noise);
      arr.push(Math.round(price / 5) * 5);
    }
    series[k] = arr;
  });

  for (let i = 0; i < weeks; i++) {
    infCum *= (1 + weeklyInflation[i % weeklyInflation.length]);
    infSeries.push(infCum);
  }

  // date labels
  const labels = [];
  const d = new Date(startDate);
  for (let i = 0; i < weeks; i++) {
    labels.push(`${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth()+1).padStart(2,"0")}`);
    d.setDate(d.getDate() + 7);
  }

  PRODUCT_DETAIL.history = { labels, series, inflation: infSeries };
})();

// Comparison table for product detail
const PRODUCT_COMPARE = [
  { sm: "dia",       price: 1180, var30: 0.06, var7: -0.025, available: "Nacional",          stock: true },
  { sm: "atomo",     price: 1210, var30: 0.07, var7:  0.000, available: "Cuyo",              stock: true },
  { sm: "vea",       price: 1230, var30: 0.08, var7: -0.010, available: "AMBA + Cuyo",       stock: true },
  { sm: "coto",      price: 1240, var30: 0.09, var7:  0.015, available: "Nacional",          stock: true },
  { sm: "anonima",   price: 1290, var30: 0.11, var7:  0.020, available: "Patagonia + NOA",   stock: true },
  { sm: "changomas", price: 1310, var30: 0.095,var7:  0.005, available: "Nacional",          stock: true },
  { sm: "disco",     price: 1310, var30: 0.10, var7:  0.000, available: "AMBA",              stock: true },
  { sm: "carrefour", price: 1395, var30: 0.14, var7:  0.040, available: "Nacional",          stock: true },
  { sm: "jumbo",     price: 1410, var30: 0.13, var7:  0.025, available: "Nacional",          stock: true },
];

// Economic indicators
const ECONOMIC = {
  inflationMonth: 0.031,      // 3.1% último mes (INDEC)
  inflationMonthDelta: -0.004,
  inflationYTD: 0.094,        // acumulada 2026
  inflationLast12: 0.328,     // últimos 12 meses
  dollarBlue: 1485,
  dollarBlueDelta: 0.012,
  dollarOfficial: 1042,
  dollarOfficialDelta: 0.003,
  dollarMep: 1378,
  uva: 1024.7,
  asOfDate: "23 may 2026",
  productIndex: 0.354, // índice ACE 12m
  productIndexDelta: 0.026, // vs inflación (354 vs 328)
};

// Monthly inflation last 12 months (oldest -> newest), %
const INFLATION_12M = [
  { m: "jun '25", v: 4.6 },
  { m: "jul '25", v: 4.0 },
  { m: "ago '25", v: 3.5 },
  { m: "sep '25", v: 3.7 },
  { m: "oct '25", v: 2.9 },
  { m: "nov '25", v: 3.2 },
  { m: "dic '25", v: 3.8 },
  { m: "ene '26", v: 4.1 },
  { m: "feb '26", v: 3.5 },
  { m: "mar '26", v: 3.0 },
  { m: "abr '26", v: 2.8 },
  { m: "may '26", v: 3.1 },
];

// Dollar history (6 months, weekly samples) — blue vs official
const DOLLAR_HISTORY = (function() {
  const labels = [];
  const blue = [];
  const oficial = [];
  const d = new Date(2025, 10, 23);
  let b = 1280, o = 970;
  for (let i = 0; i < 26; i++) {
    labels.push(`${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth()+1).padStart(2,"0")}`);
    b += (Math.sin(i*0.6) * 8) + 8 + (Math.cos(i*0.9)*5);
    o += 2.7 + Math.sin(i*0.3)*2;
    blue.push(Math.round(b));
    oficial.push(Math.round(o));
    d.setDate(d.getDate() + 7);
  }
  return { labels, blue, oficial };
})();

// Suggestions for the search autocomplete
const SEARCH_SUGGESTIONS = [
  { q: "aceite girasol",    hint: "418 productos", cat: "Almacén" },
  { q: "leche entera",      hint: "62 productos",  cat: "Lácteos" },
  { q: "yerba mate",        hint: "147 productos", cat: "Almacén" },
  { q: "pan lactal",        hint: "38 productos",  cat: "Panificados" },
  { q: "harina 000",        hint: "29 productos",  cat: "Almacén" },
  { q: "fideos guiseros",   hint: "84 productos",  cat: "Almacén" },
  { q: "papel higiénico",   hint: "112 productos", cat: "Higiene" },
];

const TRENDING = [
  { q: "Aceite girasol",   change: +0.18, dir: "up"   },
  { q: "Leche entera",     change: +0.08, dir: "up"   },
  { q: "Yerba mate",       change: -0.03, dir: "down" },
  { q: "Pan lactal",       change: +0.12, dir: "up"   },
  { q: "Detergente",       change: +0.06, dir: "up"   },
  { q: "Café molido",      change: +0.21, dir: "up"   },
];

window.ACE_DATA = {
  SUPERMARKETS, SM_BY_ID, REGIONS, CATEGORIES,
  PRODUCTS, PRODUCT_DETAIL, PRODUCT_COMPARE,
  ECONOMIC, INFLATION_12M, DOLLAR_HISTORY,
  SEARCH_SUGGESTIONS, TRENDING,
};
