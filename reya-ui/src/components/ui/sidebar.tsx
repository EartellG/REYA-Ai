import { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type TabKey = "chat" | "projects" | "tutor" | "kb" | "settings";

type Item = { key: TabKey; icon: ReactNode; label: string };

const items: Item[] = [
  { key: "chat",     icon: "💬", label: "Chat" },
  { key: "projects", icon: "📁", label: "Projects" },
  { key: "tutor",    icon: "🈺", label: "Language Tutor" },
  { key: "kb",       icon: "📚", label: "Knowledge Base" },
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
      {/* overlay for mobile */}
      <div
        className={cn(
          "fixed inset-0 bg-black/40 z-40 lg:hidden transition-opacity",
          mobileOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
      />

      <aside
        className={cn(
          "fixed z-50 top-0 left-0 h-full w-64 bg-zinc-900/90 text-zinc-200 p-3 transform transition-transform",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
          "lg:static lg:translate-x-0 lg:w-56"
        )}
      >
        <div className="text-xl font-semibold px-2 pb-3">REYA</div>
        <nav className="space-y-1">
          {items.map((it) => (
            <button
              key={it.key}
              onClick={() => { onChange(it.key); onClose?.(); }}
              className={cn(
                "w-full text-left px-3 py-2 rounded-lg hover:bg-zinc-800",
                current === it.key && "bg-zinc-800 border border-zinc-700"
              )}
            >
              <span className="mr-2">{it.icon}</span>
              {it.label}
            </button>
          ))}
        </nav>
      </aside>
    </>
  );
}
