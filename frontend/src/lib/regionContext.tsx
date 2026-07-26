"use client";

import { createContext, useContext, useState } from "react";

type RegionContextType = {
  region: string;
  setRegion: (r: string) => void;
};

const RegionContext = createContext<RegionContextType>({
  region: "Todas las regiones",
  setRegion: () => {},
});

export function RegionProvider({ children }: { children: React.ReactNode }) {
  const [region, setRegion] = useState("Todas las regiones");
  return (
    <RegionContext.Provider value={{ region, setRegion }}>
      {children}
    </RegionContext.Provider>
  );
}

export const useRegion = () => useContext(RegionContext);
