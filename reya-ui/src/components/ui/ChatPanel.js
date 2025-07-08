import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
export default function ChatPanel({ modes }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const sendMessage = async () => {
        if (!input.trim())
            return;
        const userMsg = { sender: "user", text: input };
        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        setIsLoading(true);
        const response = await fetch("http://127.0.0.1:8000/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: input }),
        });
        const reader = response.body?.getReader();
        const decoder = new TextDecoder("utf-8");
        let reyaMsg = "";
        setMessages((prev) => [...prev, { sender: "reya", text: "" }]);
        if (reader) {
            while (true) {
                const { done, value } = await reader.read();
                if (done)
                    break;
                const chunk = decoder.decode(value, { stream: true });
                reyaMsg += chunk;
                setMessages((prev) => prev.map((msg, i) => i === prev.length - 1 ? { ...msg, text: reyaMsg } : msg));
            }
        }
        setIsLoading(false);
    };
    return (_jsxs("div", { className: "flex flex-col h-full", children: [_jsxs(ScrollArea, { className: "flex-1 p-6 space-y-3 overflow-y-auto", children: [messages.map((msg, idx) => (_jsx(Card, { className: "bg-gray-800", children: _jsx(CardContent, { children: _jsxs("p", { children: [_jsx("strong", { children: msg.sender === "user" ? "You" : "REYA" }), ":", " ", msg.text] }) }) }, idx))), isLoading && (_jsx(Card, { className: "bg-gray-800", children: _jsx(CardContent, { children: _jsxs("p", { children: [_jsx("strong", { children: "REYA" }), ": ", _jsx("span", { className: "animate-pulse", children: "..." })] }) }) }))] }), _jsxs("div", { className: "p-4 border-t border-gray-800 flex gap-2", children: [_jsx(Input, { value: input, onChange: (e) => setInput(e.target.value), onKeyDown: (e) => e.key === "Enter" && sendMessage(), placeholder: "Type your message to REYA...", className: "flex-1" }), _jsx(Button, { onClick: sendMessage, children: "Send" })] })] }));
}
