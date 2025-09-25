// src/components/ui/sidebar.tsx
import { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type TabKey = "chat" | "projects" | "tutor" | "kb" | "roles" | "settings";

type Item = { key: TabKey; icon: ReactNode; label: string };

const items: Item[] = [
  { key: "chat",     icon: "💬", label: "Chat" },
  { key: "projects", icon: "📁", label: "Projects" },
  { key: "tutor",    icon: "🈺", label: "Language Tutor" },
  { key: "kb",       icon: "📚", label: "Knowledge Base" },
  { key: "roles",    icon: "🧩", label: "Roles" },
  { key: "settings", icon: "⚙️", label: "Settings" },
];

export default function Sidebar({
  current,
  onChange,
  mobileOpen = false,
  onClose,
}: {
  current: TabKey;
  onChange: (k: TabKey) => void;
  mobileOpen?: boolean;
  onClose?: () => void;
}) {
  return (
    <>
      <div
        className={cn(
          "fixed inset-0 z-40 lg:hidden transition-opacity bg-black/50",
          mobileOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
      />

      <aside
        className={cn(
          "fixed z-50 top-0 left-0 h-full w-68 p-3 transform transition-transform",
          "lg:static lg:translate-x-0 lg:w-56",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
          "ga-panel ga-outline text-zinc-100"
        )}
      >
        <div className="text-xl font-semibold px-2 pb-3"></div>
        <nav className="space-y-2">
          {items.map((it) => {
            const active = current === it.key;
            return (
              <button
                key={it.key}
                onClick={() => { onChange(it.key); onClose?.(); }}
                className={cn(
                  "w-full text-left px-3 py-2 rounded-xl transition",
                  "ga-btn",
                  active && "ga-outline bg-white/10"
                )}
              >
                <span className="mr-2">{it.icon}</span>
                {it.label}
              </button>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
