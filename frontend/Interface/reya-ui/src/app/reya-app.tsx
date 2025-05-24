import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Sidebar } from "@/components/ui/sidebar";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarImage } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";

export default function REYAApp() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  const sendMessage = () => {
    if (!input.trim()) return;
    setMessages([...messages, { sender: "user", text: input }]);
    setInput("");
    // Hook to REYA backend comes here
  };

  return (
    <div className="grid grid-cols-12 min-h-screen bg-gray-950 text-white">
      {/* Sidebar */}
      <div className="col-span-2 bg-gray-900 p-4">
        <Sidebar items={["Chat", "Projects", "Avatar", "Settings"]} />
      </div>

      {/* Main Content */}
      <div className="col-span-10 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <div className="flex items-center gap-4">
            <Avatar>
              <AvatarImage src="/reya-avatar.png" alt="REYA" />
            </Avatar>
            <h1 className="text-xl font-semibold">REYA</h1>
          </div>
          <div className="flex gap-2">
            <Button variant="outline">Multimodal Mode</Button>
            <Button variant="outline">Live Avatar</Button>
            <Button variant="outline">Logic Engine</Button>
            <Button variant="outline">Offline Smart</Button>
          </div>
        </div>

        {/* Chat Area */}
        <ScrollArea className="flex-1 p-6 space-y-3">
          {messages.map((msg, idx) => (
            <Card key={idx} className="bg-gray-800">
              <CardContent>
                <p><strong>{msg.sender === "user" ? "You" : "REYA"}</strong>: {msg.text}</p>
              </CardContent>
            </Card>
          ))}
        </ScrollArea>

        {/* Input */}
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
    </div>
  );
}
