// reya-ui/src/components/ui/textarea.tsx
import * as React from "react";

/** Tiny class joiner so we don't rely on any external 'cn' utility */
function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Optional accent for role-specific styling */
  variant?: "default" | "coder" | "reviewer" | "fixer";
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, variant = "default", ...props }, ref) => {
    const variantRing =
      variant === "coder"
        ? "border-blue-500/40 focus-visible:ring-blue-400"
        : variant === "reviewer"
        ? "border-amber-500/40 focus-visible:ring-amber-400"
        : variant === "fixer"
        ? "border-emerald-500/40 focus-visible:ring-emerald-400"
        : "border-zinc-600 focus-visible:ring-cyan-400";

    return (
      <textarea
        ref={ref}
        className={cx(
          // Base look: darker background, clearer placeholder, visible ring
          "flex min-h-[80px] w-full rounded-md border bg-zinc-900/50",
          "px-3 py-2 text-sm text-zinc-100 shadow-sm placeholder:text-zinc-400",
          // Focus treatment
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950",
          // Disabled state
          "disabled:cursor-not-allowed disabled:opacity-50",
          // Variant accent (role color)
          variantRing,
          className
        )}
        {...props}
      />
    );
  }
);

Textarea.displayName = "Textarea";

// Keep default export too, so both `import Textarea` and `import { Textarea }` work.
export default Textarea;
