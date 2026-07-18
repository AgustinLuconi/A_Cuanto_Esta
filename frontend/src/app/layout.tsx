import type { Metadata } from "next";
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
    <html lang="es">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="app">
        <QueryProvider>
          <RegionProvider>
            <Header />
            {children}
          </RegionProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
