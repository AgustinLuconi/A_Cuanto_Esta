import type { ProductCategory } from "@/types";

export interface DesignCategory {
  id: string;
  name: string;
  backendId: ProductCategory;
}

export const CATEGORIES_DESIGN: DesignCategory[] = [
  { id: "lacteos",     name: "Lácteos",          backendId: "lacteos"         },
  { id: "bebidas",     name: "Bebidas",           backendId: "bebidas"         },
  { id: "carnes",      name: "Carnes",            backendId: "carnes"          },
  { id: "panificados", name: "Panificados",       backendId: "panaderia"       },
  { id: "limpieza",    name: "Limpieza",          backendId: "limpieza"        },
  { id: "higiene",     name: "Higiene personal",  backendId: "higiene_personal"},
  { id: "frutas",      name: "Frutas y verduras", backendId: "frutas_verduras" },
  { id: "congelados",  name: "Congelados",        backendId: "congelados"      },
  { id: "almacen",     name: "Almacén",           backendId: "alimentos"       },
  { id: "snacks",      name: "Snacks",            backendId: "snacks"          },
  { id: "mascotas",    name: "Mascotas",          backendId: "otros"           },
  { id: "otros",       name: "Otros",             backendId: "otros"           },
];

// Design category ID → backend category ID
export const DESIGN_TO_BACKEND: Record<string, ProductCategory> = Object.fromEntries(
  CATEGORIES_DESIGN.map((c) => [c.id, c.backendId])
) as Record<string, ProductCategory>;

// Backend category ID → design category ID (first match wins)
export const BACKEND_TO_DESIGN: Partial<Record<ProductCategory, string>> = {
  lacteos:         "lacteos",
  bebidas:         "bebidas",
  carnes:          "carnes",
  panaderia:       "panificados",
  limpieza:        "limpieza",
  higiene_personal:"higiene",
  frutas_verduras: "frutas",
  congelados:      "congelados",
  alimentos:       "almacen",
  snacks:          "snacks",
  desayuno:        "otros",
  otros:           "otros",
};
