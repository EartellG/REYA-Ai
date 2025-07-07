import { useState, useEffect, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

interface ChatPanelProps {
  modes: {
    multimodal: boolean;
    liveAvatar: boolean;
    logicEngine: boolean;
    offlineSmart: boolean;
  };
}

type Message = { sender: "user" | "reya"; text: string };

export default function ChatPanel({ modes }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg: Message = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    const newMsgIndex = messages.length + 1;
    setMessages((prev) => [...prev, { sender: "reya", text: "" }]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
        signal: controller.signal,
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      let accumulated = "";

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          accumulated += chunk;

          // Update last message
          setMessages((prev) =>
            prev.map((msg, i) =>
              i === newMsgIndex ? { ...msg, text: accumulated } : msg
            )
          );
        }
      } else {
        throw new Error("No response body to read from.");
      }
    } catch (error) {
      console.error("Stream error:", error);
      setMessages((prev) => [
        ...prev,
        { sender: "reya", text: "⚠️ Something went wrong." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  return (
    <div className="flex flex-col h-full">
      <ScrollArea className="flex-1 p-6 space-y-3 overflow-y-auto">
        {messages.map((msg, idx) => (
          <Card key={idx} className="bg-gray-800">
            <CardContent>
              <p>
                <strong>{msg.sender === "user" ? "You" : "REYA"}</strong>:{" "}
                {msg.text}
              </p>
            </CardContent>
          </Card>
        ))}
        {isLoading && (
          <Card className="bg-gray-800">
            <CardContent>
              <p>
                <strong>REYA</strong>:{" "}
                <span className="animate-pulse">...</span>
              </p>
            </CardContent>
          </Card>
        )}
      </ScrollArea>

      <div className="p-4 border-t border-gray-800 flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Type your message to REYA..."
          className="flex-1"
        />
        <Button onClick={sendMessage}>Send</Button>
      </div>
    </div>
  );
}
