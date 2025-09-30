import { useEffect, useRef, useState } from "react";
import { useProjectDiscussions } from "@/state/projectDiscussions";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
// Removed unused Input import
import { Textarea } from "@/components/ui/textarea";
import { useChatStore } from "@/state/chatStore"; // reuse TTS/etc if you want

const API = "http://127.0.0.1:8000";

export default function ProjectDiscussionsTab() {
  const { threads, openThreadId, openThread, addMessage, archiveThread, deleteThread } = useProjectDiscussions();
  const active = threads.find(t => t.id === openThreadId) || threads.find(t => !t.archived) || threads[0] || null;
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement|null>(null);
  const addAssistantGlobal = useChatStore(s => s.addAssistant); // optional: mirror last reply into global history

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [active?.messages.length]);

  const send = async () => {
    if (!active || !draft.trim()) return;
    const userText = draft.trim();
    setDraft("");
    addMessage(active.id, "user", userText);

    // Call your existing /chat to get Reya's brainstorming reply
    try {
      const r = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: `PROJECT DISCUSSION: ${active.title}\n\n${userText}` }),
      });
      const text = await r.text(); // your /chat streams; for simplicity read body
      addMessage(active.id, "assistant", text);
      addAssistantGlobal?.(text);
    } catch (e) {
      addMessage(active.id, "assistant", "⚠️ Brainstorming failed.");
    }
  };

  const sendToTicketizer = async () => {
    if (!active) return;
    // Minimal: prime localStorage for Ticketizer initial spec + switch tabs
    localStorage.setItem("ticketizer:seed", JSON.stringify({
      idea: active.title,
      notes: active.messages.map(m => `${m.role === "user" ? "You" : "Reya"}: ${m.text}`).join("\n"),
    }));
    // Navigate to Projects -> Ticketizer panel: we’ll flip main tab and remember sub-tab in your existing UI
    window.dispatchEvent(new CustomEvent("reya:navigate", { detail: { tab: "projects", ticketizer: true }}));
  };

  return (
    <div className="grid grid-cols-12 gap-3">
      {/* Threads list */}
      <Card className="ga-panel ga-outline col-span-12 md:col-span-4">
        <CardContent className="p-3 space-y-2">
          <div className="text-sm opacity-70">Discussions</div>
          <div className="space-y-1">
            {threads.length === 0 && <div className="text-sm opacity-60">No discussions yet. Start from Projects → Plan.</div>}
            {threads.map(t => (
              <button
                key={t.id}
                onClick={() => openThread(t.id)}
                className={`w-full text-left px-3 py-2 rounded-lg hover:bg-white/5 ${t.id === active?.id ? "bg-white/10" : ""}`}
              >
                <div className="font-medium">{t.title}{t.archived ? " (archived)" : ""}</div>
                <div className="text-xs opacity-60">{t.messages.length} messages</div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Active thread */}
      <Card className="ga-panel ga-outline col-span-12 md:col-span-8">
        <CardContent className="p-3 space-y-3">
          {active ? (
            <>
              <div className="flex items-center justify-between">
                <div className="font-semibold">{active.title}</div>
                <div className="flex gap-2">
                  <Button className="ga-btn" variant="outline" onClick={sendToTicketizer}>Send to Ticketizer</Button>
                  <Button className="ga-btn" variant="secondary" onClick={() => archiveThread(active.id)}>Archive</Button>
                  <Button className="ga-btn" variant="destructive" onClick={() => deleteThread(active.id)}>Delete</Button>
                </div>
              </div>

              <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-1">
                {active.messages.map(m => (
                  <div key={m.id} className={`rounded-lg px-3 py-2 ${m.role === "user" ? "bg-white/10" : "bg-white/5"}`}>
                    <div className="text-xs opacity-60 mb-0.5">{m.role === "user" ? "You" : "Reya"}</div>
                    <div className="whitespace-pre-wrap">{m.text}</div>
                  </div>
                ))}
                <div ref={endRef} />
              </div>

              <div className="flex gap-2">
                <Textarea
                  value={draft}
                  onChange={e => setDraft(e.target.value)}
                  placeholder="Share an idea or ask Reya to explore a direction…"
                  className="min-h-[48px]"
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                />
                <Button className="ga-btn" onClick={send}>Send</Button>
              </div>
            </>
          ) : (
            <div className="text-sm opacity-70">Select a discussion on the left.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
