// src/components/Sidebar.tsx
import { ReactNode } from "react";
import { cn } from "@/lib/utils";

type Item = {
  key: TabKey;
  icon: ReactNode;
  label: string;
};

export type TabKey = "chat" | "projects" | "tutor" | "kb" | "settings";

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
}: {
  current: TabKey;
  onChange: (k: TabKey) => void;
}) {
  return (
    <aside className="w-56 bg-zinc-900/80 text-zinc-200 p-3">
      <div className="text-xl font-semibold px-2 pb-3">REYA</div>
      <nav className="space-y-1">
        {items.map((it) => (
          <button
            key={it.key}
            onClick={() => onChange(it.key)}
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
  );
}
