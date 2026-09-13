// src/components/ui/ChatPanel.tsx
import { useEffect, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import SystemStatusModal from "@/components/SystemStatusModal";
import { playReyaTTS } from "@/lib/reyaTts";
import { useModes } from "@/state/modes";
import { useChatStore } from "@/state/chatStore";
import TypingIndicator from "@/components/ui/TypingIndicator";

const API_BASE = "http://127.0.0.1:8000";

export default function ChatPanel() {
  const { modes } = useModes();
  const { multimodal, liveAvatar, logicEngine, offlineSmart } = modes;

  // global chat history (from store)
  const msgs = useChatStore((s) => s.messages);
  const addUser = useChatStore((s) => s.addUser);
  const addAssistant = useChatStore((s) => s.addAssistant);

  // local UI state
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);

  // streaming state
  const [streamingText, setStreamingText] = useState("");
  const endRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, streamingText, isLoading]);

  // Stream assistant text to a local bubble; return final string
  const streamText = async (userText: string): Promise<string> => {
    addUser(userText);

    const controller = new AbortController();
    abortRef.current = controller;

    const payload = {
      message: userText,
      modes: { multimodal, liveAvatar, logicEngine, offlineSmart },
    };

    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    if (!response.ok || !response.body) throw new Error("Stream failed");

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let accumulated = "";
    setStreamingText(""); // start fresh bubble

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      accumulated += chunk;
      setStreamingText(accumulated);
    }

    setStreamingText("");
    return accumulated.trim();
  };

  const sendMessage = async () => {
    const userText = input.trim();
    if (!userText) return;

    setInput("");
    setIsLoading(true);

    try {
      const finalText = await streamText(userText);

      if (finalText) {
        addAssistant(finalText);
      }

    } catch (err) {
      console.error("Chat error:", err);
      addAssistant("⚠️ Something went wrong.");
    } finally {
      setIsLoading(false);
    }
  };

  const speakMessage = async (messageId: string, text: string) => {
    if (speakingMessageId) return;

    setSpeakingMessageId(messageId);
    try {
      await playReyaTTS(text);
    } catch (err) {
      console.error("TTS error:", err);
    } finally {
      setSpeakingMessageId(null);
    }
  };

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  return (
    <div className="flex h-full flex-col">
      {/* Top tools */}
      <div className="px-4 pt-4 flex items-center gap-2">
        <SystemStatusModal />
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4 sm:p-6 space-y-3 overflow-y-auto">
        {msgs.map((m) =>
          m.role === "assistant" ? (
            <div key={m.id} className="flex items-start gap-2 px-1">
              <img
                src="/ReyaAva.png"
                alt="REYA"
                className="mt-0.5 h-7 w-7 rounded-full ring-1 ring-white/10"
              />
              <div className="max-w-[78%] rounded-2xl bg-zinc-800/60 border border-white/10 px-3 py-2 text-zinc-100">
                {m.text}
                <button
                  type="button"
                  onClick={() => speakMessage(m.id, m.text)}
                  disabled={speakingMessageId !== null}
                  className="ml-2 rounded px-1 text-sm text-zinc-400 hover:bg-zinc-700 hover:text-zinc-100 disabled:cursor-wait disabled:opacity-50"
                  title={speakingMessageId === m.id ? "Reading response aloud…" : "Read response aloud"}
                  aria-label={speakingMessageId === m.id ? "Reading response aloud" : "Read response aloud"}
                >
                  {speakingMessageId === m.id ? "🔊…" : "🔊"}
                </button>
              </div>
            </div>
          ) : (
            <div key={m.id} className="flex justify-end px-1">
              <div className="max-w-[78%] rounded-2xl bg-violet-600/20 border border-violet-500/30 px-3 py-2 text-violet-100">
                {m.text}
              </div>
            </div>
          )
        )}

        {/* Streaming / typing state */}
        {isLoading && !streamingText && <TypingIndicator />}

        {streamingText && (
          <div className="flex items-start gap-2 px-1">
            <img
              src="/ReyaAva.png"
              alt="REYA"
              className="mt-0.5 h-7 w-7 rounded-full ring-1 ring-white/10"
            />
            <div className="max-w-[78%] rounded-2xl bg-zinc-800/60 border border-white/10 px-3 py-2 reya-shimmer text-zinc-100">
              {streamingText}
            </div>
          </div>
        )}

        <div ref={endRef} />
      </ScrollArea>

      {/* Input */}
      <div className="p-3 sm:p-4 border-t border-zinc-800 flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Type your message to REYA…"
          className="flex-1"
        />
        <Button onClick={sendMessage} disabled={isLoading}>
          {isLoading ? "Sending…" : "Send"}
        </Button>
      </div>
    </div>
  );
}
