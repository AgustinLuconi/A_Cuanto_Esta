# Design Specification: Dark Mode

**Date**: 2026-08-29
**Project**: A Cuánto Está? (`AgustinLuconi/A_Cuanto_Esta`)
**Status**: Approved

---

## 1. Overview & Goals

Add a dark mode to the Next.js frontend: a manual toggle in the header that persists the user's choice and, on first visit, defaults to the OS-level `prefers-color-scheme`.

The codebase already has two parallel color systems:
1. **CSS custom properties** in `frontend/src/components/design/styles.css` (`--bg`, `--surface`, `--fg`, `--primary`, `--good`, `--bad`, `--warn`, `--sm-1..9`, shadows), which drive the app chrome (topbar, buttons, chips, badges, cards, tables) and the hand-rolled charts on `/economia` and `/cobertura` (which already reference `var(--fg-3)`, `var(--bad)`, etc. directly instead of hardcoded hex).
2. **Tailwind theme colors** in `frontend/tailwind.config.ts` (`background`, `primary`, `surface`, `up`, `down`, `neutral`, `border`), hardcoded as static hex, used by newer components in `results/`, part of `home/`, and `layout/`.

The design leans entirely on system 1 (CSS variables) as the source of truth, and rewires system 2 to read from it, so a single attribute flip themes the whole app with no per-component changes.

Decorative category illustrations in `design/icons.tsx` use hand-picked hex fills and are explicitly out of scope — they stay as-is on a dark background.

---

## 2. Architecture

### 2.1 Theme attribute

Reuse the existing (currently unused by any component) `[data-theme="..."]` convention already present in `styles.css` for the dormant `forest`/`ink` accent variants. Add a new block:

```css
[data-theme="dark"] {
  --bg: oklch(...);
  --bg-2: oklch(...);
  --surface: oklch(...);
  --surface-2: oklch(...);
  --border: oklch(...);
  --border-strong: oklch(...);
  --fg: oklch(...);
  --fg-2: oklch(...);
  --fg-3: oklch(...);
  --fg-4: oklch(...);
  --primary: oklch(...);
  --primary-hover: oklch(...);
  --primary-tint: oklch(...);
  --good / --good-tint, --bad / --bad-tint, --warn / --warn-tint: adjusted for dark contrast
  --sm-1..9: adjusted lightness so supermarket swatches keep enough contrast on a dark surface
  --shadow-1 / --shadow-2 / --shadow-pop: adjusted opacity for dark backgrounds
}
```

`data-theme` is set on `<html>` (not `<body>`) so it's available before Tailwind/CSS-var-consuming components paint.

### 2.2 Tailwind config unification

`tailwind.config.ts` colors change from static hex to `var(...)` references:

```ts
colors: {
  background: "var(--bg)",
  primary: "var(--primary)",
  surface: "var(--surface)",
  up: "var(--bad)",
  down: "var(--good)",
  neutral: "var(--fg-3)",
  border: "var(--border)",
}
```

No component using `bg-background`, `text-primary`, `border-border`, etc. needs to change — they inherit dark mode automatically once the CSS variables flip.

### 2.3 Theme provider & persistence

New `frontend/src/lib/themeContext.tsx`, modeled after the existing `regionContext.tsx`:
- `ThemeProvider` wraps the app (alongside `QueryProvider`/`RegionProvider` in `layout.tsx`).
- Exposes `theme: "light" | "dark"` and `toggleTheme()`.
- On mount, reads `localStorage["theme"]`; if absent, falls back to `window.matchMedia("(prefers-color-scheme: dark)")`.
- Every change writes to `localStorage["theme"]` and sets `document.documentElement.dataset.theme`.

### 2.4 Avoiding flash of incorrect theme (FOUC)

A small inline `<script>` in `app/layout.tsx`'s `<head>`, running before hydration, that reads `localStorage["theme"]` (or the media query if unset) and sets `data-theme` on `<html>` synchronously. This mirrors what the `ThemeProvider` does on mount, so there's no flash and no hydration mismatch (the attribute is set outside React's render tree).

### 2.5 Toggle UI

A sun/moon icon button added to `Header.tsx`'s existing controls row (next to the region/supermarket pickers), calling `toggleTheme()` from the context.

---

## 3. Testing

- Manual verification in the browser: toggle dark mode, navigate across all pages (`/`, `/resultados`, `/producto`, `/economia`, `/cobertura`), confirm no unstyled/low-contrast elements.
- Confirm persistence across a hard refresh and across navigation.
- Confirm no FOUC (no visible flash of the wrong theme) on initial load with dark mode previously selected.
- Confirm OS-preference fallback: with no stored preference, matches the OS setting.
