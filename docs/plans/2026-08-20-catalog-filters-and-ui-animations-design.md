# Design Specification: Catalog Expansion, Advanced Filters & Motion Design

**Date**: 2026-08-20  
**Project**: A Cuánto Está? (`AgustinLuconi/A_Cuanto_Esta`)  
**Status**: Approved  

---

## 1. Overview & Goals

This specification covers the full-stack enhancement of the **A Cuánto Está?** platform across three core pillars:
1. **Catalog Expansion**: Adding 5 new categories (`mascotas`, `bebes`, `hogar_bazar`, `farmacia_salud`, `electro_tecnologia`) with realistic product seed data across all 9 supermarkets.
2. **Advanced Multi-faceted Filtering**: Extending backend API endpoints and frontend search interfaces to filter by specific supermarkets, stock availability, active discounts ("Solo en Oferta"), minimum discount percentage, and brand search.
3. **Framer Motion & Micro-Interactions**: Integrating Framer Motion into the Next.js frontend for smooth layout grid transitions, fluid collapsable filter panels, active badge animations, and elevated hover interactions.

---

## 2. Architecture & Data Model Changes

### 2.1 Backend Models (`backend/app/models/product.py`)
Add the following new enum members to `ProductCategory`:
- `MASCOTAS = "mascotas"`
- `BEBES = "bebes"`
- `HOGAR_BAZAR = "hogar_bazar"`
- `FARMACIA_SALUD = "farmacia_salud"`
- `ELECTRO_TECNOLOGIA = "electro_tecnologia"`

### 2.2 Backend API Endpoints (`backend/app/api/v1/endpoints/products.py`)
Update `GET /api/v1/products/search` and `GET /api/v1/products` query parameters:
- `supermarkets: list[str] | None = Query(None)` (multi-select filter by supermarket IDs)
- `only_on_sale: bool | None = Query(None)`
- `only_in_stock: bool | None = Query(None)`
- `min_discount: float | None = Query(None, ge=0, le=100)`
- `brand: str | None = Query(None)`

Update facet calculations to return supermarket counts, category counts, and price ranges matching the active search parameters.

### 2.3 Backend Seeder Script (`backend/scripts/seed_expanded_catalog.py`)
Create a seeder script that populates realistic products, brands, and current/historical prices for all new categories (`mascotas`, `bebes`, `hogar_bazar`, `farmacia_salud`, `electro_tecnologia`) across Carrefour, Coto, Disco, Jumbo, Vea, Día, Átomo, La Anónima, and Chango Más.

---

## 3. Frontend Architecture Changes

### 3.1 Dependencies
- Install `framer-motion` in `frontend/package.json`.

### 3.2 Types & Validation (`frontend/src/types/index.ts`)
- Update `PRODUCT_CATEGORIES` array to include `"mascotas"`, `"bebes"`, `"hogar_bazar"`, `"farmacia_salud"`, `"electro_tecnologia"`.
- Update `ProductCategorySchema` Zod enum.
- Update `searchProducts` params in `frontend/src/lib/api.ts`.

### 3.3 UI Components & Motion Layer
- **`FilterSidebar.tsx`**: Multi-select checkboxes for Supermarkets with logos, "Solo en oferta" toggle switch, "En stock" toggle switch, discount slider (>10%, >20%, >30%), and Brand filter input. Smooth height animation with Framer Motion `AnimatePresence`.
- **`ResultadosContent.tsx` / Product Grid**: Wrap product list with Framer Motion `motion.div` and `layout` animations for smooth grid reflowing when filters change.
- **`ProductCard.tsx`**: Add `motion.div` hover animations (`whileHover={{ y: -4, transition: { duration: 0.2 } }}`), pill badge glow, and animated discount badges.
- **`CategoryGrid.tsx`**: Display icons/emojis for all categories including the 5 new ones.

---

## 4. Verification Plan

1. **Backend Tests**: Run `pytest` to verify new query parameters and schema validation.
2. **Data Seeder Execution**: Run `python scripts/seed_expanded_catalog.py` in `backend/` and verify products count per category.
3. **Frontend Compilation & Lint**: Run `npx tsc --noEmit` and `npm run lint` in `frontend/`.
4. **Dev Server Verification**: Verify smooth UI animations and multi-facet filtering on `http://localhost:3000/resultados`.
