"use client";

import { createContext, useContext, useEffect, useState } from "react";

type Theme = "light" | "dark";

type ThemeContextType = {
  theme: Theme;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextType>({
  theme: "light",
  toggleTheme: () => {},
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // Always starts as "light" on both server and the client's first render,
  // matching the server-rendered HTML exactly — this avoids a hydration
  // mismatch. The boot script in layout.tsx has already set the *visual*
  // theme (the `data-theme` attribute on <html>, which drives every color
  // via CSS) before hydration even runs; this effect just mirrors that
  // attribute into React state after mount, so theme-aware React output
  // (the toggle button's icon) catches up a moment later.
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    if (document.documentElement.dataset.theme === "dark") {
      setTheme("dark");
    }
  }, []);

  const toggleTheme = () => {
    setTheme((current) => {
      const next: Theme = current === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      window.localStorage.setItem("theme", next);
      return next;
    });
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
