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
  const streamingTextRef = useRef("");
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg: Message = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      streamingTextRef.current = "";

      setMessages((prev) => [...prev, { sender: "reya", text: "" }]);

      if (reader) {
        let doneReading = false;

        const updateMessage = () => {
          if (!isMounted.current) return;
          setMessages((prev) =>
            prev.map((msg, i) =>
              i === prev.length - 1
                ? { ...msg, text: streamingTextRef.current }
                : msg
            )
          );
        };

        const readerLoop = async () => {
          try {
            while (!doneReading) {
              const { done, value } = await reader.read();
              if (done) {
                doneReading = true;
                break;
              }

              const chunk = decoder.decode(value, { stream: true });
              streamingTextRef.current += chunk;

              // Optional cap
              if (streamingTextRef.current.length > 10000) {
                streamingTextRef.current =
                  streamingTextRef.current.slice(0, 10000) + "\n[...truncated]";
                break;
              }

              updateMessage();
              await new Promise((r) => setTimeout(r, 200));
            }
          } catch (err) {
            console.error("Reader loop error:", err);
          } finally {
            updateMessage();
            if (isMounted.current) setIsLoading(false);
          }
        };

        await readerLoop(); // <-- ✅ Await the loop
      } else {
        console.error("No response body to read from.");
        setIsLoading(false);
      }
    } catch (error) {
      console.error("Fetch error:", error);
      if (isMounted.current) setIsLoading(false);
    }
  };

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
