import { useState, useEffect, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import SystemStatusModal from "@/components/SystemStatusModal";

interface ChatPanelProps {
  modes: {
    multimodal: boolean;
    liveAvatar: boolean;
    logicEngine: boolean;
    offlineSmart: boolean;
  };
}

type Message = { sender: "user" | "reya"; text: string };

const API_BASE = "http://127.0.0.1:8000";

export default function ChatPanel({ modes }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [speakEnabled, setSpeakEnabled] = useState(true);
  const [lastAudioUrl, setLastAudioUrl] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const assistantIndexRef = useRef<number | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const streamText = async (userText: string) => {
    setMessages((prev) => [...prev, { sender: "user", text: userText }]);
    setMessages((prev) => {
      const idx = prev.length;
      assistantIndexRef.current = idx;
      return [...prev, { sender: "reya", text: "" }];
    });

    const controller = new AbortController();
    abortRef.current = controller;

    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userText }),
      signal: controller.signal,
    });

    if (!response.ok || !response.body) throw new Error("Stream failed");

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let accumulated = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      accumulated += chunk;

      const idx = assistantIndexRef.current;
      if (idx !== null) {
        setMessages((prev) => prev.map((m, i) => (i === idx ? { ...m, text: accumulated } : m)));
      }
    }
  };

  const fetchTTS = async (userText: string) => {
    const res = await fetch(`${API_BASE}/chat?speak=true`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userText }),
    });

    if (!res.ok) throw new Error("TTS fetch failed");
    const data: { text: string; audio_url?: string | null } = await res.json();

    if (data.audio_url) {
      const url = `${API_BASE}${data.audio_url}`;
      setLastAudioUrl(url);
      try {
        const audio = new Audio(url);
        await audio.play();
      } catch {}
    }
  };

  const sendMessage = async () => {
    const userText = input.trim();
    if (!userText) return;

    setInput("");
    setIsLoading(true);

    try {
      await streamText(userText);
      if (speakEnabled) await fetchTTS(userText);
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => [...prev, { sender: "reya", text: "⚠️ Something went wrong." }]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Top toolbar with Voice toggle and System Status modal trigger */}
      <div className="px-4 pt-4 flex items-center gap-2">
        <Button
          variant={speakEnabled ? "default" : "secondary"}
          onClick={() => setSpeakEnabled((v) => !v)}
          title="Toggle voice playback"
        >
          {speakEnabled ? "🔊 Voice: On" : "🔇 Voice: Off"}
        </Button>
        {lastAudioUrl && (
          <Button
            variant="secondary"
            onClick={async () => {
              try {
                const audio = new Audio(lastAudioUrl);
                await audio.play();
              } catch {}
            }}
            title="Play last reply audio"
          >
            ▶ Play reply
          </Button>
        )}
        {/* System Status modal trigger */}
        <SystemStatusModal />
      </div>

      <ScrollArea className="flex-1 p-6 space-y-3 overflow-y-auto">
        {messages.map((msg, idx) => (
          <Card key={idx} className="bg-gray-800">
            <CardContent>
              <p>
                <strong>{msg.sender === "user" ? "You" : "REYA"}</strong>: {msg.text}
              </p>
            </CardContent>
          </Card>
        ))}
        {isLoading && (
          <Card className="bg-gray-800">
            <CardContent>
              <p>
                <strong>REYA</strong>: <span className="animate-pulse">...</span>
              </p>
            </CardContent>
          </Card>
        )}
        <div ref={endRef} />
      </ScrollArea>

      <div className="p-4 border-t border-gray-800 flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Type your message to REYA..."
          className="flex-1"
        />
        <Button onClick={sendMessage} disabled={isLoading}>
          {isLoading ? "Sending..." : "Send"}
        </Button>
      </div>
    </div>
  );
}
