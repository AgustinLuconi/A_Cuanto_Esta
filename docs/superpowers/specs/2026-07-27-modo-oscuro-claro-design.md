# Modo claro/oscuro

## Contexto

El sistema de diseño del frontend (`src/components/design/styles.css`) ya
está construido sobre variables CSS (`--bg`, `--fg`, `--primary`,
`--surface`, etc.), usadas de forma consistente en casi toda la UI —
tanto en las clases custom (`.card`, `.btn`, `.tab`, `.badge`, etc.) como
en la gran mayoría de los estilos inline de los componentes. Esto significa
que redefinir esos tokens para un tema oscuro re-tematiza la mayor parte
de la app automáticamente, sin tocar componente por componente.

Hallazgos relevantes al explorar:

- Ya existe el mecanismo `[data-theme="..."]` en el CSS (variantes
  `"forest"` e `"ink"` que solo cambian `--primary`), pero **nunca se
  aplica en ningún componente React** — es CSS muerto. Se reutiliza el
  mismo atributo `data-theme` para claro/oscuro y se elimina el CSS
  muerto de forest/ink.
- No hay ninguna librería de manejo de temas instalada (`next-themes` u
  otra), ni uso de `prefers-color-scheme`, ni de `localStorage` para esto
  en ningún lado del código.
- Hay ~14 usos de `oklch(...)` hardcodeados directamente en estilos
  inline de componentes (no como variable), calibrados a mano para fondo
  claro. La mayoría son variantes cercanas a tokens `--warn`/`--good` ya
  existentes. El caso aparte es `/cobertura`, que calcula luminosidad
  dinámicamente en JS para un mapa de calor, con una fórmula que asume
  fondo claro.
- Los colores de swatch por supermercado (`--sm-1`..`--sm-9`) y los
  colores de los íconos de categoría (hex fijos en `CatIcon`) son
  ilustrativos/decorativos — no necesitan variante por tema.

## Decisiones

- **Comportamiento**: sigue `prefers-color-scheme` del sistema operativo
  por defecto, con un toggle manual en el header que lo puede forzar; la
  elección manual se persiste (localStorage, vía la librería).
- **Mecanismo**: se usa `next-themes` en vez de implementarlo a mano. Es
  el estándar de facto para Next.js, ~1KB sin dependencias propias, y
  resuelve correctamente el punto más delicado (evitar el flash de tema
  incorrecto al cargar, antes de que React hidrate) sin reinventar algo
  ya resuelto.
- **Atributo**: `attribute="data-theme"`, reutilizando el mecanismo que
  ya existe en el CSS. Se eliminan las variantes muertas `forest`/`ink`.
- **Paleta oscura**: se define invirtiendo la escala de luminosidad
  (`L` en OKLCH) de cada token existente, manteniendo el mismo matiz
  (`H`) — mismo "sabor" de marca, no un tema oscuro genérico.
- **Los oklch() hardcodeados**: los que ya son equivalentes a un token
  existente (`--warn`, `--good`) se reemplazan por ese token (limpieza,
  no solo fix de tema). El mapa de calor de `/cobertura` recibe una rama
  condicional según el tema activo (`useTheme()`), porque su fórmula es
  JS, no CSS — un simple swap de variable no alcanza ahí.
- Los colores de swatch por supermercado y los íconos de categoría
  quedan sin cambios en ambos temas (decorativos, no de superficie).

## Paleta oscura — tokens nuevos bajo `[data-theme="dark"]`

Mismo criterio que la paleta clara: `--bg`/`--fg` invertidos en L pero
con el hue original de cada uno (90 para neutros cálidos de fondo, 250
para los fríos de texto/marca), y los tokens de estado (`--good`,
`--bad`, `--warn`) aclarados para mantener legibilidad sobre fondo
oscuro. `--primary` pasa a ser una versión clara del azul de marca (para
contraste sobre fondo oscuro), por lo que `--primary-ink` (el color de
texto sobre botones primarios) pasa de blanco a oscuro en este tema.
Las sombras (`--shadow-*`) se recalibran porque una sombra oscura sobre
fondo ya oscuro no se percibe — se ajustan opacidad/color.

Valores exactos a definir en la implementación, verificados con checks
de contraste WCAG AA (≥4.5:1 texto normal, ≥3:1 texto grande/UI) para los
pares `--fg`/`--bg`, `--fg-2`/`--bg`, `--primary-ink`/`--primary`.

## Componentes

### `frontend/package.json`
Agregar dependencia `next-themes`.

### `frontend/src/app/layout.tsx`
Envolver el árbol en `<ThemeProvider attribute="data-theme" defaultTheme="system" enableSystem>`.

### `frontend/src/components/design/styles.css`
- Eliminar `[data-theme="forest"]` y `[data-theme="ink"]` (muertos)
- Agregar bloque `[data-theme="dark"]` con la paleta oscura completa
- Reemplazar los `oklch(...)` hardcodeados que coinciden con un token
  existente por ese token, en los archivos donde aparecen (no es un
  cambio de este archivo, es en los `.tsx` que los usan)

### `frontend/src/components/layout/ThemeToggle.tsx` (nuevo)
Botón sol/luna usando `useTheme()` de `next-themes`. Se monta en
`Header.tsx`, junto a los pills de Región/Supermercados.

### `frontend/src/app/cobertura/page.tsx`
La fórmula de luminosidad del mapa de calor pasa a depender de
`resolvedTheme` (de `useTheme()`): en oscuro, el rango se invierte
(empieza oscuro, se aclara hacia el primary en vez de al revés).

## Manejo de errores / edge cases

- **Flash de tema incorrecto**: resuelto por `next-themes` (script
  bloqueante inline antes de hidratar) — no requiere código propio.
- **Mismatch de hidratación SSR**: el toggle debe evitar renderizar un
  ícono dependiente del tema hasta que el componente esté montado en
  cliente (patrón estándar de `next-themes`: chequear `mounted` antes de
  leer `resolvedTheme`), para no generar un warning de hidratación.
- **Usuario sin preferencia de SO detectable**: `next-themes` cae a
  `"light"` por defecto en ese caso, comportamiento ya incluido en la
  librería.

## Testing / validación

- Contraste WCAG AA verificado a mano (o con una herramienta de línea de
  comandos) para los pares de color crítico de la paleta oscura antes de
  darla por buena
- Capturas con Playwright de home, resultados, producto (detalle), 
  economía y cobertura en modo claro y en modo oscuro, para revisión
  visual de que no haya texto ilegible ni bordes invisibles
- Verificar que el toggle persiste la elección al recargar la página
  (localStorage) y que cambiar `prefers-color-scheme` del SO actualiza
  la app en vivo si el usuario no forzó una elección manual
- `tsc --noEmit` limpio

## Fuera de alcance

- No se agregan más variantes de tema que claro/oscuro (se elimina
  forest/ink en vez de mantenerlos)
- No se cambian los colores de swatch por supermercado ni los íconos de
  categoría
- No se agrega un selector de "tema personalizado" ni configuración más
  allá de claro/oscuro/sistema
