// src/components/ui/TypingIndicator.tsx
import { memo } from "react";

export default memo(function TypingIndicator({
  avatarSrc = "/ReyaAva.png",
  label = "REYA is typing",
}: { avatarSrc?: string; label?: string }) {
  return (
    <div className="flex items-start gap-2 px-2 py-1.5">
      {/* Avatar head */}
      <img
        src={avatarSrc}
        alt="REYA"
        className="h-7 w-7 rounded-full ring-1 ring-white/10 shadow"
      />

      {/* Bubble with shimmer + dots */}
      <div
        className="rounded-2xl border border-white/10 bg-zinc-800/40 shadow-inner px-3 py-2 reya-shimmer"
        aria-label={label}
      >
        <div className="flex items-center gap-1">
          <span className="typing-dot" style={{ animationDelay: "0ms" }} />
          <span className="typing-dot" style={{ animationDelay: "150ms" }} />
          <span className="typing-dot" style={{ animationDelay: "300ms" }} />
        </div>
      </div>
    </div>
  );
});
