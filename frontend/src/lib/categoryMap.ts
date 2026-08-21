import type { ProductCategory } from "@/types";

export interface DesignCategory {
  id: string;
  name: string;
  backendId: ProductCategory;
}

export const CATEGORIES_DESIGN: DesignCategory[] = [
  { id: "almacen",          name: "Almacén",           backendId: "alimentos"         },
  { id: "bebidas",          name: "Bebidas",           backendId: "bebidas"         },
  { id: "lacteos",          name: "Lácteos",          backendId: "lacteos"         },
  { id: "limpieza",         name: "Limpieza",          backendId: "limpieza"        },
  { id: "higiene",          name: "Higiene personal",  backendId: "higiene_personal"},
  { id: "carnes",           name: "Carnes",            backendId: "carnes"          },
  { id: "frutas",           name: "Frutas y verduras", backendId: "frutas_verduras" },
  { id: "panificados",      name: "Panificados",       backendId: "panaderia"       },
  { id: "congelados",       name: "Congelados",        backendId: "congelados"      },
  { id: "snacks",           name: "Snacks",            backendId: "snacks"          },
  { id: "desayuno",         name: "Desayuno",          backendId: "desayuno"        },
  { id: "mascotas",         name: "Mascotas",          backendId: "mascotas"        },
  { id: "bebes",            name: "Bebés",             backendId: "bebes"           },
  { id: "hogar_bazar",      name: "Hogar y Bazar",     backendId: "hogar_bazar"     },
  { id: "farmacia_salud",   name: "Salud y Farmacia",  backendId: "farmacia_salud"  },
  { id: "electro_tecnologia", name: "Electro y Tecno", backendId: "electro_tecnologia" },
  { id: "otros",            name: "Otros",             backendId: "otros"           },
];

// Design category ID → backend category ID
export const DESIGN_TO_BACKEND: Record<string, ProductCategory> = Object.fromEntries(
  CATEGORIES_DESIGN.map((c) => [c.id, c.backendId])
) as Record<string, ProductCategory>;

// Backend category ID → design category ID (first match wins)
export const BACKEND_TO_DESIGN: Partial<Record<ProductCategory, string>> = {
  alimentos:          "almacen",
  bebidas:            "bebidas",
  lacteos:            "lacteos",
  limpieza:           "limpieza",
  higiene_personal:   "higiene",
  carnes:             "carnes",
  frutas_verduras:    "frutas",
  panaderia:          "panificados",
  congelados:         "congelados",
  snacks:             "snacks",
  desayuno:           "desayuno",
  mascotas:           "mascotas",
  bebes:              "bebes",
  hogar_bazar:        "hogar_bazar",
  farmacia_salud:     "farmacia_salud",
  electro_tecnologia: "electro_tecnologia",
  otros:              "otros",
};
