import type { Metadata } from "next";
import "./globals.css";
import "@/components/design/styles.css";
import QueryProvider from "@/components/layout/QueryProvider";
import Header from "@/components/layout/Header";
import { RegionProvider } from "@/lib/regionContext";
import { ThemeProvider } from "@/lib/themeContext";

export const metadata: Metadata = {
  title: "¿A Cuánto Está? — Comparador de precios en supermercados argentinos",
  description:
    "Comparamos precios de más de 3.000 productos en 9 supermercados argentinos con contexto económico en tiempo real.",
};

const THEME_BOOT_SCRIPT = `
(function () {
  try {
    var stored = window.localStorage.getItem("theme");
    var theme = stored === "light" || stored === "dark"
      ? stored
      : (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.dataset.theme = theme;
  } catch (e) {}
})();
`;

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
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT_SCRIPT }} />
      </head>
      <body className="app">
        <ThemeProvider>
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
