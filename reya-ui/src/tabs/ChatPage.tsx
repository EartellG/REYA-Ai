// src/tabs/ChatPage.tsx
import { useState, useMemo, useEffect } from "react";
import ChatPanel from "@/components/ui/ChatPanel";
import { Card, CardContent } from "@/components/ui/card";
import ProjectDiscussionsTab from "@/tabs/ProjectDiscussionsTab";

type SubTab = "direct" | "discuss";

export default function ChatPage() {
  const [sub, setSub] = useState<SubTab>(() => {
    const saved = localStorage.getItem("reya-chat-sub");
    return saved === "discuss" ? "discuss" : "direct";
  });
  useMemo(() => localStorage.setItem("reya-chat-sub", sub), [sub]);

  // Allow global navigation events to flip sub-tab (used by Projects → Plan)
  useEffect(() => {
    const onNav = (e: any) => {
      const d = e?.detail || {};
      if (d.chatSub === "discuss") setSub("discuss");
      if (d.chatSub === "direct") setSub("direct");
    };
    window.addEventListener("reya:navigate" as any, onNav);
    return () => window.removeEventListener("reya:navigate" as any, onNav);
  }, []);

  return (
    <div className="space-y-3">
      <Card className="ga-panel ga-outline">
        <CardContent className="p-2">
          <div className="flex gap-2">
            <button
              className={`px-3 py-1 rounded-lg ${sub === "direct" ? "bg-white/10" : "hover:bg-white/5"}`}
              onClick={() => setSub("direct")}
            >
              Direct Chat
            </button>
            <button
              className={`px-3 py-1 rounded-lg ${sub === "discuss" ? "bg-white/10" : "hover:bg-white/5"}`}
              onClick={() => setSub("discuss")}
            >
              Project Discussions
            </button>
          </div>
        </CardContent>
      </Card>

      {sub === "direct" ? <ChatPanel /> : <ProjectDiscussionsTab />}
    </div>
  );
}
