// src/components/ui/use-toast.tsx
import * as React from "react";
import { createPortal } from "react-dom";

/* ---------- Types ---------- */
type Toast = {
  id: string;
  title?: string;
  description?: string;
  variant?: "default" | "success" | "destructive";
  duration?: number; // ms
};

type ToastContextType = {
  toast: (t: Omit<Toast, "id">) => void;
  dismiss: (id: string) => void;
  toasts: Toast[];
};

/* ---------- Context ---------- */
const ToastContext = React.createContext<ToastContextType | null>(null);

export function useToast(): ToastContextType {
  const ctx = React.useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within <ToastProvider>");
  return ctx;
}

/* ---------- Provider ---------- */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const dismiss = React.useCallback((id: string) => {
    setToasts((ts) => ts.filter((t) => t.id !== id));
  }, []);

  const toast = React.useCallback(
    (t: Omit<Toast, "id">) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const duration = t.duration ?? 3500;
      setToasts((ts) => [...ts, { id, ...t }]);
      if (duration > 0) window.setTimeout(() => dismiss(id), duration);
    },
    [dismiss]
  );

  return (
    <ToastContext.Provider value={{ toast, dismiss, toasts }}>
      {children}
      {/* render a portalized toaster automatically */}
      <Toaster />
    </ToastContext.Provider>
  );
}

/* ---------- Public, no-props Toaster ---------- */
export function Toaster() {
  // reads from context; no props required
  const { toasts, dismiss } = useToast();
  if (typeof document === "undefined") return null;

  return createPortal(
    <div className="fixed inset-x-0 top-3 z-[100] flex flex-col items-center gap-2 px-3">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={[
            "w-full max-w-md rounded-lg border px-4 py-3 shadow-lg backdrop-blur",
            "bg-gray-900/90 border-gray-700 text-white",
            t.variant === "success" && "border-emerald-600/60",
            t.variant === "destructive" && "border-red-600/60",
          ].join(" ")}
          role="status"
        >
          <div className="flex items-start gap-3">
            <div className="flex-1">
              {t.title && <div className="font-semibold">{t.title}</div>}
              {t.description && (
                <div className="text-sm text-zinc-300">{t.description}</div>
              )}
            </div>
            <button
              aria-label="Dismiss toast"
              className="rounded p-1 text-zinc-400 hover:text-white hover:bg-white/10"
              onClick={() => dismiss(t.id)}
            >
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>,
    document.body
  );
}
