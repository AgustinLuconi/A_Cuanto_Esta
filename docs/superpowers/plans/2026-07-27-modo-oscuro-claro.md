# Modo Claro/Oscuro Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar modo claro/oscuro real al frontend, siguiendo `prefers-color-scheme` del sistema con override manual persistido, sin romper el sistema de diseño existente basado en variables CSS.

**Architecture:** `next-themes` gestiona la detección/persistencia/anti-flash mediante el atributo `data-theme` en `<html>` (mecanismo que ya existe en el CSS pero nunca se activaba). Se define una paleta oscura completa en `styles.css` bajo `[data-theme="dark"]`, y se migran ~14 colores `oklch()` hardcodeados en componentes a variables (nuevas o existentes) para que también respondan al tema.

**Tech Stack:** Next.js 14 (App Router), `next-themes`, CSS custom properties (OKLCH).

**Spec:** `docs/superpowers/specs/2026-07-27-modo-oscuro-claro-design.md`

## Global Constraints

- Atributo del tema: `data-theme`, valores `"light"` / `"dark"` (reemplaza a los `"forest"`/`"ink"` muertos, que se eliminan).
- `defaultTheme="system"`, `enableSystem` — sigue el SO por defecto, override manual persistido por la librería.
- Los colores de swatch por supermercado (`--sm-1`..`--sm-9`) y los íconos de categoría (`CatIcon`, hex fijos) **no cambian** entre temas — están fuera de alcance.
- `--good`, `--bad`, `--warn` (los 3 colores de estado en su forma "sólida", no las variantes `-tint`) **no cambian de luminosidad entre temas** — decisión verificada con cálculo de contraste real (ver Task 1): mantenerlos siempre en su mismo valor da mejor balance entre "legible como texto sobre fondo oscuro" y "fondo sólido con texto blanco encima" que aclararlos en oscuro.
- Verificación de tipos: `cd frontend && npx tsc --noEmit` debe pasar sin errores en cada tarea.
- El proyecto vive en una ruta con un `?` literal (`A_Cuanto_Esta?`) que rompe la resolución de alias de `npx tsx` y `npm run build` (limitación conocida, no relacionada con este trabajo). Usar `npm run dev` (Turbopack) para verificación visual, y scripts Node planos (sin imports de alias) para lo que se pueda verificar fuera del navegador.

---

### Task 1: `next-themes` + paleta oscura en `styles.css`

**Files:**
- Modify: `frontend/package.json` (agregar dependencia)
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/components/design/styles.css`

**Interfaces:**
- Produces: tokens CSS nuevos consumidos por Task 3 y Task 4:
  `--good-border`, `--warn-ink`, `--warn-border`, `--primary-glow`,
  `--tooltip-bg`, `--tooltip-fg` (estos últimos dos son invariantes de
  tema, solo en `:root`). `ThemeProvider` envolviendo el árbol, consumido
  por `useTheme()` en Task 2 y Task 4.

- [ ] **Step 1: Instalar `next-themes`**

Run: `cd frontend && npm install next-themes`

- [ ] **Step 2: Envolver el árbol en `ThemeProvider`**

En `frontend/src/app/layout.tsx`, agregar el import y envolver `children`:

```tsx
import type { Metadata } from "next";
import { ThemeProvider } from "next-themes";
import "./globals.css";
import "@/components/design/styles.css";
import QueryProvider from "@/components/layout/QueryProvider";
import Header from "@/components/layout/Header";
import { RegionProvider } from "@/lib/regionContext";

export const metadata: Metadata = {
  title: "¿A Cuánto Está? — Comparador de precios en supermercados argentinos",
  description:
    "Comparamos precios de más de 3.000 productos en 9 supermercados argentinos con contexto económico en tiempo real.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="app">
        <ThemeProvider attribute="data-theme" defaultTheme="system" enableSystem>
          <QueryProvider>
            <RegionProvider>
              <Header />
              {children}
            </RegionProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
```

`suppressHydrationWarning` en `<html>` es requerido por `next-themes`: el
script anti-flash de la librería fija `data-theme` antes de que React
hidrate, así que el atributo en el primer render del servidor y el del
cliente difieren a propósito — sin este flag Next.js tira un warning de
hidratación en consola por algo que es intencional y correcto.

- [ ] **Step 3: Reemplazar el bloque `:root` y las variantes muertas en `styles.css`**

En `frontend/src/components/design/styles.css`, reemplazar desde la
línea 5 (`:root {`) hasta la línea 62 (el cierre de `[data-theme="ink"]`)
por lo siguiente:

```css
:root {
  --bg: oklch(0.985 0.003 90);
  --bg-2: oklch(0.965 0.005 90);
  --surface: #ffffff;
  --surface-2: oklch(0.975 0.004 90);
  --border: oklch(0.92 0.005 90);
  --border-strong: oklch(0.85 0.006 90);
  --fg: oklch(0.20 0.02 250);
  --fg-2: oklch(0.40 0.015 250);
  --fg-3: oklch(0.55 0.012 250);
  --fg-4: oklch(0.70 0.008 250);

  --primary: oklch(0.30 0.08 250);
  --primary-hover: oklch(0.26 0.085 250);
  --primary-tint: oklch(0.95 0.02 250);
  --primary-ink: #ffffff;
  --primary-glow: oklch(0.30 0.08 250 / 0.3);

  --good: oklch(0.55 0.14 150);
  --good-tint: oklch(0.95 0.04 150);
  --good-border: oklch(0.85 0.07 150);
  --bad: oklch(0.55 0.18 25);
  --bad-tint: oklch(0.96 0.03 25);
  --warn: oklch(0.70 0.15 70);
  --warn-tint: oklch(0.96 0.04 70);
  --warn-ink: oklch(0.38 0.09 60);
  --warn-border: oklch(0.88 0.05 70);

  --r-sm: 6px;
  --r-md: 10px;
  --r-lg: 14px;
  --r-xl: 20px;

  --shadow-1: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 1px rgba(15, 23, 42, 0.03);
  --shadow-2: 0 4px 14px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04);
  --shadow-pop: 0 18px 40px -12px rgba(15, 23, 42, 0.18), 0 4px 10px rgba(15, 23, 42, 0.06);

  --font-sans: "Manrope", "Helvetica Neue", Helvetica, ui-sans-serif, system-ui, sans-serif;
  --font-mono: "Manrope", "Helvetica Neue", Helvetica, ui-sans-serif, system-ui, sans-serif;

  /* Per-supermarket swatch colors (original, not copied from real brands).
     Decorativos — no cambian entre temas claro/oscuro a propósito. */
  --sm-1: oklch(0.55 0.16 28);   /* coral red */
  --sm-2: oklch(0.55 0.15 60);   /* amber */
  --sm-3: oklch(0.62 0.14 145);  /* green */
  --sm-4: oklch(0.50 0.14 195);  /* teal */
  --sm-5: oklch(0.45 0.14 250);  /* blue */
  --sm-6: oklch(0.45 0.16 290);  /* violet */
  --sm-7: oklch(0.55 0.16 340);  /* pink */
  --sm-8: oklch(0.40 0.04 250);  /* slate */
  --sm-9: oklch(0.60 0.12 100);  /* olive */

  /* Tooltip de gráficos: siempre "chip oscuro con texto claro",
     independiente del tema de la página — no se sobreescribe en
     [data-theme="dark"]. */
  --tooltip-bg: oklch(0.20 0.02 250);
  --tooltip-fg: #ffffff;
}

[data-theme="dark"] {
  --bg: oklch(0.16 0.006 250);
  --bg-2: oklch(0.20 0.007 250);
  --surface: oklch(0.19 0.008 250);
  --surface-2: oklch(0.23 0.008 250);
  --border: oklch(0.30 0.01 250);
  --border-strong: oklch(0.40 0.012 250);
  --fg: oklch(0.93 0.005 90);
  --fg-2: oklch(0.78 0.008 90);
  --fg-3: oklch(0.62 0.01 90);
  --fg-4: oklch(0.46 0.01 90);

  --primary: oklch(0.72 0.09 250);
  --primary-hover: oklch(0.78 0.09 250);
  --primary-tint: oklch(0.26 0.03 250);
  --primary-ink: oklch(0.15 0.02 250);
  --primary-glow: oklch(0.72 0.09 250 / 0.35);

  /* --good/--bad/--warn NO cambian de L entre temas — ver Global
     Constraints: mismo valor da mejor balance de contraste en ambos
     roles (texto sobre fondo, y fondo sólido con texto blanco encima)
     que aclararlos. Solo cambian sus variantes -tint/-border/-ink. */
  --good-tint: oklch(0.24 0.05 150);
  --good-border: oklch(0.40 0.10 150);
  --bad-tint: oklch(0.22 0.05 25);
  --warn-tint: oklch(0.28 0.05 70);
  --warn-ink: oklch(0.88 0.06 70);
  --warn-border: oklch(0.35 0.06 70);

  --shadow-1: 0 1px 2px rgba(0, 0, 0, 0.3), 0 1px 1px rgba(0, 0, 0, 0.2);
  --shadow-2: 0 4px 14px rgba(0, 0, 0, 0.35), 0 1px 2px rgba(0, 0, 0, 0.25);
  --shadow-pop: 0 18px 40px -12px rgba(0, 0, 0, 0.5), 0 4px 10px rgba(0, 0, 0, 0.3);
}
```

- [ ] **Step 4: Corregir `.chart-tooltip` y `.badge.warn` para usar los tokens nuevos**

En el mismo archivo, buscar:

```css
.chart-tooltip {
  position: absolute;
  pointer-events: none;
  background: var(--fg);
  color: white;
```

Reemplazar por:

```css
.chart-tooltip {
  position: absolute;
  pointer-events: none;
  background: var(--tooltip-bg);
  color: var(--tooltip-fg);
```

(Motivo: `.chart-tooltip` asumía que `--fg` siempre es oscuro para usarlo
como fondo de un "chip" oscuro con texto blanco — en el tema oscuro
`--fg` pasa a ser claro, así que sin este cambio el tooltip quedaría con
fondo casi blanco y texto blanco encima, ilegible.)

Buscar también:

```css
.badge.warn { background: var(--warn-tint); color: oklch(0.45 0.12 60); }
```

Reemplazar por:

```css
.badge.warn { background: var(--warn-tint); color: var(--warn-ink); }
```

- [ ] **Step 5: Verificar el contraste de la paleta oscura con un script real**

Crear un script temporal (no se commitea) `frontend/contrast-check.js`:

```javascript
function oklchToLinearSRGB(L, C, H) {
  const hRad = (H * Math.PI) / 180;
  const a = C * Math.cos(hRad);
  const b = C * Math.sin(hRad);
  const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = L - 0.0894841775 * a - 1.2914855480 * b;
  const l = l_ ** 3, m = m_ ** 3, s = s_ ** 3;
  const r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s;
  const g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s;
  const bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s;
  return [r, g, bl].map((v) => Math.min(1, Math.max(0, v)));
}
function relativeLuminance([r, g, b]) { return 0.2126 * r + 0.7152 * g + 0.0722 * b; }
function contrastRatio(o1, o2) {
  const L1 = relativeLuminance(oklchToLinearSRGB(...o1));
  const L2 = relativeLuminance(oklchToLinearSRGB(...o2));
  const hi = Math.max(L1, L2), lo = Math.min(L1, L2);
  return (hi + 0.05) / (lo + 0.05);
}
const white = [1, 0, 0];
const pairs = [
  ["DARK fg / bg",                 [0.93, 0.005, 90],  [0.16, 0.006, 250]],
  ["DARK primary-ink / primary",   [0.15, 0.02, 250],  [0.72, 0.09, 250]],
  ["DARK white / good (badge)",    white,               [0.55, 0.14, 150]],
  ["DARK white / bad (badge)",     white,               [0.55, 0.18, 25]],
  ["DARK warn-ink / warn-tint",    [0.88, 0.06, 70],   [0.28, 0.05, 70]],
  ["DARK good / good-tint (text)", [0.55, 0.14, 150],  [0.24, 0.05, 150]],
  ["DARK bad / bad-tint (text)",   [0.55, 0.18, 25],   [0.22, 0.05, 25]],
];
for (const [name, c1, c2] of pairs) {
  console.log(`${name}: ${contrastRatio(c1, c2).toFixed(2)}:1`);
}
```

Run: `node frontend/contrast-check.js`

Expected (valores ya verificados al escribir este plan — confirmar que
coinciden):
```
DARK fg / bg: 15.79:1
DARK primary-ink / primary: 7.97:1
DARK white / good (badge): 4.55:1
DARK white / bad (badge): 5.32:1
DARK warn-ink / warn-tint: 10.17:1
DARK good / good-tint (text): 3.56:1
DARK bad / bad-tint (text): 3.30:1
```

Los dos últimos (3.56 y 3.30) están por debajo del umbral estricto de
texto normal (4.5:1) pero por encima del umbral de UI/texto grande
(3:1) — aceptable acá porque el uso real es texto de badge en negrita a
11-11.5px (`badge.up`/`badge.down`), no párrafos. Si el número no
coincide con lo esperado, hay un typo al copiar los valores del Step 3 —
revisar antes de seguir.

- [ ] **Step 6: Borrar el script temporal**

```bash
rm frontend/contrast-check.js
```

- [ ] **Step 7: Verificar tipos**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/app/layout.tsx frontend/src/components/design/styles.css
git commit -m "feat: agregar next-themes y paleta de modo oscuro"
```

---

### Task 2: Toggle de tema en el header

**Files:**
- Modify: `frontend/src/components/design/components.tsx` (agregar íconos `sun`/`moon` al objeto `Icon`)
- Create: `frontend/src/components/layout/ThemeToggle.tsx`
- Modify: `frontend/src/components/layout/Header.tsx`

**Interfaces:**
- Consumes: `ThemeProvider` (Task 1)
- Produces: `export default function ThemeToggle()`, montado en `Header.tsx`

- [ ] **Step 1: Agregar íconos sol/luna**

En `frontend/src/components/design/components.tsx`, dentro del objeto
`Icon` (busca `export const Icon = {`), agregar dos entradas nuevas,
siguiendo el mismo estilo que las existentes (por ejemplo, justo después
de la entrada `alert`):

```typescript
  sun: (p: React.SVGProps<SVGSVGElement>) => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>,
  moon: (p: React.SVGProps<SVGSVGElement>) => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/></svg>,
```

- [ ] **Step 2: Crear el componente `ThemeToggle`**

Crear `frontend/src/components/layout/ThemeToggle.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Icon } from "@/components/design/components";

export default function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    // Evita el mismatch de hidratación: en el server no sabemos el tema
    // real hasta que el cliente monta (next-themes ya resolvió
    // resolvedTheme vía su script anti-flash, pero React no lo sabe
    // hasta este punto). Placeholder del mismo tamaño para no saltar el layout.
    return <div className="tb-pill" style={{ width: 34, height: 30 }} />;
  }

  const isDark = resolvedTheme === "dark";

  return (
    <button
      className="tb-pill"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      title={isDark ? "Modo claro" : "Modo oscuro"}
      style={{ cursor: "pointer" }}
    >
      {isDark ? <Icon.sun /> : <Icon.moon />}
    </button>
  );
}
```

- [ ] **Step 3: Montar el toggle en el header**

En `frontend/src/components/layout/Header.tsx`, agregar el import:

```typescript
import ThemeToggle from "@/components/layout/ThemeToggle";
```

Y dentro del `<div className="tb-control">`, agregar `<ThemeToggle />`
como primer hijo (antes de los dos `<Dropdown>` de Región/Supermercados):

```tsx
      <div className="tb-control">
        <ThemeToggle />
        <Dropdown
          open={regionOpen}
          ...
```

- [ ] **Step 4: Verificar tipos**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores

- [ ] **Step 5: Verificar visualmente**

Con `cd frontend && npm run dev` corriendo, abrir `http://localhost:3000`
y confirmar: aparece el ícono de luna (si el navegador está en modo
claro) junto a los pills de Región/Supermercados; al clickear cambia a
sol y el resto de la UI pasa a modo oscuro (aunque la paleta de fondo
oscura recién se aplica de verdad con las variables de Task 1, ya
commiteadas). Recargar la página y confirmar que el tema elegido
persiste.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/design/components.tsx frontend/src/components/layout/ThemeToggle.tsx frontend/src/components/layout/Header.tsx
git commit -m "feat: agregar toggle de modo claro/oscuro al header"
```

---

### Task 3: Migrar colores hardcodeados a tokens (page.tsx, economia, producto, resultados)

**Files:**
- Modify: `frontend/src/app/page.tsx:297,303,307,310,312`
- Modify: `frontend/src/app/economia/page.tsx:176`
- Modify: `frontend/src/app/producto/[id]/page.tsx:113`
- Modify: `frontend/src/app/resultados/ResultadosContent.tsx:468`

**Interfaces:**
- Consumes: `--warn-border`, `--warn-ink`, `--warn`, `--good-border` (Task 1)

- [ ] **Step 1: Banner de inflación acumulada en `page.tsx`**

Reemplazar (línea 297):
```tsx
            <div className="card" style={{ padding: 16, background: "var(--warn-tint)", borderColor: "oklch(0.88 0.05 70)" }}>
```
por:
```tsx
            <div className="card" style={{ padding: 16, background: "var(--warn-tint)", borderColor: "var(--warn-border)" }}>
```

Reemplazar (línea 303):
```tsx
                  <div style={{ fontWeight: 700, fontSize: 13.5, color: "oklch(0.35 0.1 60)" }}>
```
por:
```tsx
                  <div style={{ fontWeight: 700, fontSize: 13.5, color: "var(--warn-ink)" }}>
```

Reemplazar (línea 307):
```tsx
                    <span className="mono" style={{ fontSize: 26, fontWeight: 700, color: "oklch(0.40 0.13 50)" }}>
```
por:
```tsx
                    <span className="mono" style={{ fontSize: 26, fontWeight: 700, color: "var(--warn-ink)" }}>
```

Reemplazar (línea 310):
```tsx
                    <span style={{ fontSize: 11, color: "oklch(0.40 0.05 60)" }}>en lo que va del año</span>
```
por:
```tsx
                    <span style={{ fontSize: 11, color: "var(--warn-ink)" }}>en lo que va del año</span>
```

Reemplazar (línea 312):
```tsx
                  <div style={{ marginTop: 6, fontSize: 11.5, color: "oklch(0.40 0.04 60)", lineHeight: 1.4 }}>
```
por:
```tsx
                  <div style={{ marginTop: 6, fontSize: 11.5, color: "var(--warn-ink)", lineHeight: 1.4 }}>
```

- [ ] **Step 2: Color de la barra de inflación mensual en `economia/page.tsx`**

Reemplazar (línea 176):
```tsx
          <BarChart data={inflationBarData} color="oklch(0.78 0.10 70)" height={260} />
```
por:
```tsx
          <BarChart data={inflationBarData} color="var(--warn)" height={260} />
```

- [ ] **Step 3: Borde de "más barato" en `producto/[id]/page.tsx` y `ResultadosContent.tsx`**

En `frontend/src/app/producto/[id]/page.tsx`, reemplazar (línea 113):
```tsx
                  borderColor: i === 0 ? "oklch(0.85 0.07 150)" : undefined,
```
por:
```tsx
                  borderColor: i === 0 ? "var(--good-border)" : undefined,
```

En `frontend/src/app/resultados/ResultadosContent.tsx`, reemplazar
(línea 468):
```tsx
          borderColor: "oklch(0.85 0.07 150)",
```
por:
```tsx
          borderColor: "var(--good-border)",
```

- [ ] **Step 4: Verificar tipos**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores

- [ ] **Step 5: Confirmar que no queda ningún `oklch(` hardcodeado en estos 4 archivos**

Run:
```bash
grep -n "oklch(" frontend/src/app/page.tsx frontend/src/app/economia/page.tsx "frontend/src/app/producto/[id]/page.tsx" frontend/src/app/resultados/ResultadosContent.tsx
```
Expected: sin resultados (ningún match)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/page.tsx frontend/src/app/economia/page.tsx "frontend/src/app/producto/[id]/page.tsx" frontend/src/app/resultados/ResultadosContent.tsx
git commit -m "fix: migrar colores hardcodeados a tokens de tema"
```

---

### Task 4: Mapa de cobertura — heatmap consciente del tema

**Files:**
- Modify: `frontend/src/app/cobertura/page.tsx`

**Interfaces:**
- Consumes: `useTheme` de `next-themes` (Task 1), `var(--border)`, `var(--border-strong)`, `var(--primary-glow)` (Task 1)
- Produces: función `coverageFill(pct: number, isDark: boolean): string`, usada por `ArgMap`, `CoverageLegend`, y el botón de lista de regiones del componente principal

- [ ] **Step 1: Agregar el import de `useTheme` y la función `coverageFill`**

En `frontend/src/app/cobertura/page.tsx`, agregar el import junto a los
existentes (línea 3-5):

```tsx
import { useTheme } from "next-themes";
```

Agregar, antes de `export default function CoberturaPage()` (línea 34),
la función compartida:

```tsx
function coverageFill(pct: number, isDark: boolean): string {
  return isDark
    ? `oklch(${0.22 + pct * 0.35} 0.06 250)`
    : `oklch(${0.96 - pct * 0.55} 0.06 250)`;
}
```

- [ ] **Step 2: Usar el tema en el componente principal, para el botón de lista de regiones**

Dentro de `export default function CoberturaPage()`, agregar al principio
de la función (junto a los `useState` existentes):

```tsx
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
```

Reemplazar (línea 158, dentro del `.map` de `REGIONS` dentro de este
mismo componente):
```tsx
                    background: isActive ? "var(--primary)" : `oklch(${0.95 - REGION_COV[r.id] * 0.5} 0.05 250)`,
```
por:
```tsx
                    background: isActive ? "var(--primary)" : coverageFill(REGION_COV[r.id], isDark),
```

- [ ] **Step 3: `ArgMap` — mapa SVG**

Cambiar la firma de `ArgMap` (línea 196) para recibir `isDark`:
```tsx
function ArgMap({ active, setActive, isDark }: { active: string; setActive: (id: string) => void; isDark: boolean }) {
  const fillFor = (id: string) => {
    if (id === active) return "var(--primary)";
    const c = REGION_COV[id];
    return coverageFill(c, isDark);
  };
```

Actualizar el único lugar donde se invoca `<ArgMap ... />` (línea 52,
dentro de `CoberturaPage`) para pasarle la prop nueva:
```tsx
          <ArgMap active={active} setActive={setActive} isDark={isDark} />
```

Dentro de `ArgMap`, reemplazar el patrón del ocean (línea 208):
```tsx
            <line x1="0" y1="0" x2="0" y2="6" stroke="oklch(0.95 0.01 220)" strokeWidth="1" />
```
por:
```tsx
            <line x1="0" y1="0" x2="0" y2="6" stroke="var(--border)" strokeWidth="1" />
```

Reemplazar el drop-shadow (línea 227):
```tsx
                  filter: isActive ? "drop-shadow(0 6px 14px oklch(0.30 0.08 250 / 0.3))" : "none",
```
por:
```tsx
                  filter: isActive ? "drop-shadow(0 6px 14px var(--primary-glow))" : "none",
```

Reemplazar el punto decorativo de Tierra del Fuego (línea 251):
```tsx
        <circle cx="230" cy="652" r="6" fill="oklch(0.90 0.02 250)" />
```
por:
```tsx
        <circle cx="230" cy="652" r="6" fill="var(--border-strong)" />
```

- [ ] **Step 4: `CoverageLegend`**

Cambiar la firma (línea 274) para recibir `isDark`:
```tsx
function CoverageLegend({ pct, label, isDark }: { pct: number; label: string; isDark: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ width: 16, height: 16, borderRadius: 4, background: coverageFill(pct, isDark), border: "1px solid var(--border)", flexShrink: 0 }} />
      <span>{label}</span>
    </div>
  );
}
```

Actualizar los 4 usos de `<CoverageLegend .../>` (líneas 65-68, dentro de
`CoberturaPage`) para pasar `isDark={isDark}`:
```tsx
            <CoverageLegend pct={0.95} label="muy alta (>90%)" isDark={isDark} />
            <CoverageLegend pct={0.78} label="alta (75–90%)" isDark={isDark} />
            <CoverageLegend pct={0.65} label="media (60–75%)" isDark={isDark} />
            <CoverageLegend pct={0.5}  label="baja (<60%)" isDark={isDark} />
```

- [ ] **Step 5: Verificar tipos**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores

- [ ] **Step 6: Confirmar que no queda ningún `oklch(` hardcodeado en el archivo**

Run: `grep -n "oklch(" frontend/src/app/cobertura/page.tsx`
Expected: sin resultados

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app/cobertura/page.tsx
git commit -m "fix: mapa de cobertura consciente del tema claro/oscuro"
```

---

### Task 5: Verificación visual completa en ambos temas

**Files:**
- Ninguno (solo verificación)

**Interfaces:**
- Consumes: todo lo anterior

- [ ] **Step 1: Levantar backend y frontend**

```bash
cd backend && source venv/bin/activate && uvicorn app.main:app --port 8000 &
cd frontend && npm run dev &
```

Esperar ~6 segundos y confirmar con curl que ambos responden 200 antes
de seguir (`curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/v1/economic/context`
y lo mismo contra `http://127.0.0.1:3000`).

- [ ] **Step 2: Capturas en modo claro y oscuro de las pantallas principales**

Con Playwright (`colorScheme` del contexto del browser controla
`prefers-color-scheme`, que es lo que `next-themes` usa por defecto
antes de tocar el toggle):

```python
from playwright.sync_api import sync_playwright

PAGES = [
    ("/", "home"),
    ("/resultados?q=aceite", "resultados"),
    ("/producto", "producto_index"),
    ("/economia", "economia"),
    ("/cobertura", "cobertura"),
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for scheme in ["light", "dark"]:
        context = browser.new_context(viewport={"width": 1400, "height": 1000}, color_scheme=scheme)
        page = context.new_page()
        for path, name in PAGES:
            page.goto(f"http://localhost:3000{path}", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1200)
            page.screenshot(path=f"{name}_{scheme}.png", full_page=True)
        context.close()
    browser.close()
```

Expected, revisando las 10 capturas a simple vista: sin texto invisible
(mismo color que su fondo), sin bordes que desaparezcan, la card de
inflación acumulada legible en ambos modos, el mapa de cobertura con el
heatmap invertido correctamente (oscuro→claro en vez de
claro→oscuro), y el toggle mostrando el ícono correcto para cada modo.

- [ ] **Step 3: Verificar persistencia del toggle**

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900}, color_scheme="light")
    page.goto("http://localhost:3000", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1000)
    page.click(".tb-control button[aria-label*='oscuro']")
    page.wait_for_timeout(500)
    theme_after_click = page.evaluate("document.documentElement.getAttribute('data-theme')")
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(1000)
    theme_after_reload = page.evaluate("document.documentElement.getAttribute('data-theme')")
    print("tema tras click:", theme_after_click)
    print("tema tras recargar:", theme_after_reload)
    browser.close()
```

Expected: ambos valores son `"dark"` — confirma que el `localStorage`
de `next-themes` persiste la elección manual entre recargas.

- [ ] **Step 4: Apagar los servidores**

```bash
pkill -f "uvicorn app.main:app --port 8000"
pkill -f "next dev --turbo"
```

- [ ] **Step 5: Reportar hallazgos**

Si algo se ve mal en las capturas del Step 2 (texto ilegible, borde
invisible, etc.), corregirlo en el archivo correspondiente antes de dar
la tarea por terminada — no es necesario un commit separado por cada
ajuste menor, se puede agrupar en uno solo:

```bash
git add -A
git commit -m "fix: ajustes visuales de modo oscuro tras verificación con Playwright"
```

Si todo se ve bien, no hace falta commit en esta tarea (es solo
verificación).

## Self-Review

**Cobertura del spec:**
- `next-themes`, `attribute="data-theme"`, `defaultTheme="system"`,
  `enableSystem` → Task 1 ✓
- Eliminar `forest`/`ink` muertos → Task 1 ✓
- Paleta oscura completa → Task 1 ✓ (con verificación de contraste real,
  no estimada)
- Toggle en el header → Task 2 ✓
- Migrar los ~14 `oklch()` hardcodeados → Task 3 (8 no-cobertura) +
  Task 4 (6 de cobertura) = 14 ✓
- Caso especial de `/cobertura` con fórmula JS dependiente del tema →
  Task 4 ✓
- Verificación visual en ambos temas → Task 5 ✓
