// src/state/modes.tsx
import React, { createContext, useContext, useMemo, useState } from "react";

export type Modes = {
  multimodal: boolean;
  liveAvatar: boolean;
  logicEngine: boolean;
  offlineSmart: boolean;
};

export type ModesCtx = {
  modes: Modes;
  setModes: React.Dispatch<React.SetStateAction<Modes>>;
  toggle: (k: keyof Modes) => void;
  enable: (k: keyof Modes) => void;
  disable: (k: keyof Modes) => void;
};

const ModesContext = createContext<ModesCtx | undefined>(undefined);

export function ModesProvider({ children }: { children: React.ReactNode }) {
  const [modes, setModes] = useState<Modes>({
    multimodal: false,
    liveAvatar: false,
    logicEngine: false,
    offlineSmart: false,
  });

  const value = useMemo<ModesCtx>(() => {
    const toggle = (k: keyof Modes) =>
      setModes((prev) => ({ ...prev, [k]: !prev[k] }));
    const enable = (k: keyof Modes) =>
      setModes((prev) => ({ ...prev, [k]: true }));
    const disable = (k: keyof Modes) =>
      setModes((prev) => ({ ...prev, [k]: false }));
    return { modes, setModes, toggle, enable, disable };
  }, [modes]);

  return (
    <ModesContext.Provider value={value}>{children}</ModesContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useModes(): ModesCtx {
  const ctx = useContext(ModesContext);
  if (!ctx) {
    throw new Error("useModes must be used inside <ModesProvider>");
  }
  return ctx;
}
