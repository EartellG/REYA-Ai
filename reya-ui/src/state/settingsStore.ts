import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Settings = {
  multimodal: boolean;
  liveAvatar: boolean;
  logicEngine: boolean;
  offlineSmart: boolean;
};

type State = {
  settings: Settings;
  syncing: boolean;
  lastSyncedAt?: number;
  set: (key: keyof Settings, value: boolean) => void;
  setAll: (s: Partial<Settings>) => void;
  syncFromServer: () => Promise<void>;
  pushToServer: () => Promise<void>;
};

const DEFAULTS: Settings = {
  multimodal: false,
  liveAvatar: false,
  logicEngine: false,
  offlineSmart: false,
};

export const useSettingsStore = create<State>()(
  persist(
    (set, get) => ({
      settings: DEFAULTS,
      syncing: false,
      set: (key, value) => set({ settings: { ...get().settings, [key]: value } }),
      setAll: (s) => set({ settings: { ...get().settings, ...s } }),
      syncFromServer: async () => {
        set({ syncing: true });
        try {
          const r = await fetch("/settings");
          if (r.ok) {
            const data = await r.json();
            set({ settings: { ...DEFAULTS, ...data }, lastSyncedAt: Date.now() });
          }
        } finally {
          set({ syncing: false });
        }
      },
      pushToServer: async () => {
        const payload = get().settings;
        set({ syncing: true });
        try {
          await fetch("/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          set({ lastSyncedAt: Date.now() });
        } finally {
          set({ syncing: false });
        }
      },
    }),
    { name: "reya-settings" }
  )
);
