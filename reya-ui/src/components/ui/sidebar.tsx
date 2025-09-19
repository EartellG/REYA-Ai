import { ReactNode, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { useLockBodyScroll } from "@/hooks/useLockBodyScroll";

export type TabKey = "chat" | "projects" | "tutor" | "kb" | "settings" | "roles";

type Item = { key: TabKey; icon: ReactNode; label: string };

const items: Item[] = [
  { key: "chat",     icon: "💬", label: "Chat" },
  { key: "projects", icon: "📁", label: "Projects" },
  { key: "tutor",    icon: "🈺", label: "Language Tutor" },
  { key: "kb",       icon: "📚", label: "Knowledge Base" },
  { key: "roles",    icon: "📝", label: "Roles" },
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
  // lock scroll when open on mobile
  useLockBodyScroll(mobileOpen);

  // close on ESC
  useEffect(() => {
    if (!mobileOpen) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose?.();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [mobileOpen, onClose]);

  const firstBtnRef = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    if (mobileOpen) firstBtnRef.current?.focus();
  }, [mobileOpen]);

  return (
    <>
      {/* overlay for mobile */}
      <div
        className={cn(
          "fixed inset-0 bg-black/50 backdrop-blur-[1px] z-40 lg:hidden transition-opacity",
          mobileOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
        aria-hidden
      />

      {/* Drawer: narrower on very small phones */}
      <aside
         className={cn(
      "drawer", // <-- add this
      "fixed z-50 top-0 left-0 h-[100dvh] text-zinc-200 p-3 transform transition-transform",
      "bg-zinc-900/95 border-r border-zinc-800",
      mobileOpen ? "translate-x-0" : "-translate-x-full",
      "w-[85vw] max-w-[280px] sm:max-w-[320px]",
      "lg:static lg:translate-x-0 lg:w-56"
        )}
        role="dialog"
        aria-modal={mobileOpen ? "true" : "false"}
        aria-label="Navigation"
      >
        <div className="text-xl font-semibold px-2 pb-3 pt-[max(env(safe-area-inset-top),0px)]">
          REYA
        </div>
        <nav className="space-y-1">
          {items.map((it, idx) => (
            <button
              key={it.key}
              ref={idx === 0 ? firstBtnRef : undefined}
              onClick={() => { onChange(it.key); onClose?.(); }}
              className={cn(
                "w-full text-left px-3 py-2 rounded-lg hover:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-600",
                current === it.key && "bg-zinc-800 border border-zinc-700"
              )}
            >
              <span className="mr-2 inline-block w-5 text-center">{it.icon}</span>
              <span className="align-middle">{it.label}</span>
            </button>
          ))}
        </nav>
      </aside>
    </>
  );
}
