import { useEffect, useMemo } from "react";
import { useSettingsStore } from "@/state/settingsStore";

type Row = { key: keyof ReturnType<typeof useSettingsStore>["settings"]; label: string; hint?: string };

const rows: Row[] = [
  { key: "multimodal",   label: "Multimodal",   hint: "Enable tools/media context where available" },
  { key: "liveAvatar",   label: "Live Avatar",  hint: "Animate avatar + mouth while TTS plays" },
  { key: "logicEngine",  label: "Logic Engine", hint: "Route math/logic to symbolic engine" },
  { key: "offlineSmart", label: "Offline Smart", hint: "Fallback to local LLM (Ollama) when remote fails" },
];

export default function SettingsTab() {
  const { settings, set, syncFromServer, pushToServer, syncing, lastSyncedAt } = useSettingsStore();
  const date = useMemo(() => (lastSyncedAt ? new Date(lastSyncedAt).toLocaleTimeString() : "—"), [lastSyncedAt]);

  // initial server sync (merge server defaults into local)
  useEffect(() => { void syncFromServer(); }, [syncFromServer]);

  // push on any local change (debounced via microqueue here is fine; for heavy use add an explicit debounce)
  useEffect(() => { void pushToServer(); }, [settings, pushToServer]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-1">Settings</h2>
        <p className="text-sm text-zinc-400">
          These toggles persist locally and sync with the backend.
          {syncing ? " Syncing…" : lastSyncedAt ? ` Last synced at ${date}.` : null}
        </p>
      </div>

      <div className="divide-y divide-zinc-800 rounded-lg border border-zinc-800 overflow-hidden">
        {rows.map((r) => (
          <label key={r.key} className="flex items-center justify-between gap-4 p-3 hover:bg-zinc-900">
            <div>
              <div className="font-medium">{r.label}</div>
              {r.hint && <div className="text-xs text-zinc-400">{r.hint}</div>}
            </div>
            <input
              type="checkbox"
              className="h-5 w-5 accent-white"
              checked={settings[r.key]}
              onChange={(e) => set(r.key, e.target.checked)}
            />
          </label>
        ))}
      </div>
    </div>
  );
}
