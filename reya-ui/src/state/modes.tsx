// src/state/modes.tsx
import { createContext, useContext, useState, ReactNode } from "react";

type Modes = {
  multimodal: boolean;
  liveAvatar: boolean;
  logicEngine: boolean;
  offlineSmart: boolean;
  setModes: (m: Partial<Modes>) => void;
};

const ModesCtx = createContext<Modes | null>(null);

export function ModesProvider({ children }: { children: ReactNode }) {
  const [modes, set] = useState({
    multimodal: true,
    liveAvatar: false,
    logicEngine: true,
    offlineSmart: false,
  });
  const setModes = (m: Partial<typeof modes>) => set((prev) => ({ ...prev, ...m }));
  return (
    <ModesCtx.Provider value={{ ...modes, setModes }}>{children}</ModesCtx.Provider>
  );
}

export const useModes = () => {
  const ctx = useContext(ModesCtx);
  if (!ctx) throw new Error("useModes must be used inside ModesProvider");
  return ctx;
};
