import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import "@/components/design/styles.css";
import QueryProvider from "@/components/layout/QueryProvider";
import Header from "@/components/layout/Header";
import { ThemeProvider } from "@/lib/themeContext";
import { ShoppingListProvider } from "@/lib/shoppingListContext";
import { env } from "@/lib/env";

const SITE_TITLE = "¿A Cuánto Está? — Comparador de precios en supermercados argentinos";
const SITE_DESCRIPTION =
  "Comparamos precios de miles de productos en 9 supermercados argentinos con contexto económico en tiempo real (inflación, dólar).";

export const metadata: Metadata = {
  metadataBase: new URL(env.NEXT_PUBLIC_SITE_URL),
  title: { default: SITE_TITLE, template: "%s | ¿A Cuánto Está?" },
  description: SITE_DESCRIPTION,
  keywords: [
    "comparador de precios", "supermercados argentina", "precios supermercados",
    "inflación argentina", "coto", "carrefour", "jumbo", "dia", "vea", "disco",
  ],
  openGraph: {
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    type: "website",
    locale: "es_AR",
    siteName: "¿A Cuánto Está?",
  },
  twitter: {
    card: "summary",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
  },
  robots: { index: true, follow: true },
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
            <ShoppingListProvider>
              <Suspense fallback={null}>
                <Header />
              </Suspense>
              {children}
            </ShoppingListProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
