import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Sidebar } from "@/components/ui/sidebar";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarImage } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
export default function REYAApp() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const sendMessage = () => {
        if (!input.trim())
            return;
        setMessages([...messages, { sender: "user", text: input }]);
        setInput("");
        // Hook to REYA backend comes here
    };
    return (_jsxs("div", { className: "grid grid-cols-12 min-h-screen bg-gray-950 text-white", children: [_jsx("div", { className: "col-span-2 bg-gray-900 p-4", children: _jsx(Sidebar, { items: ["Chat", "Projects", "Avatar", "Settings"] }) }), _jsxs("div", { className: "col-span-10 flex flex-col", children: [_jsxs("div", { className: "flex items-center justify-between p-4 border-b border-gray-800", children: [_jsxs("div", { className: "flex items-center gap-4", children: [_jsx(Avatar, { children: _jsx(AvatarImage, { src: "/ReyaAva.png", alt: "REYA" }) }), _jsx("h1", { className: "text-xl font-semibold", children: "REYA" })] }), _jsxs("div", { className: "flex gap-2", children: [_jsx(Button, { variant: "outline", children: "Multimodal Mode" }), _jsx(Button, { variant: "outline", children: "Live Avatar" }), _jsx(Button, { variant: "outline", children: "Logic Engine" }), _jsx(Button, { variant: "outline", children: "Offline Smart" })] })] }), _jsx(ScrollArea, { className: "flex-1 p-6 space-y-3", children: messages.map((msg, idx) => (_jsx(Card, { className: "bg-gray-800", children: _jsx(CardContent, { children: _jsxs("p", { children: [_jsx("strong", { children: msg.sender === "user" ? "You" : "REYA" }), ": ", msg.text] }) }) }, idx))) }), _jsxs("div", { className: "p-4 border-t border-gray-800 flex gap-2", children: [_jsx(Input, { value: input, onChange: (e) => setInput(e.target.value), onKeyDown: (e) => e.key === "Enter" && sendMessage(), placeholder: "Type your message to REYA...", className: "flex-1" }), _jsx(Button, { onClick: sendMessage, children: "Send" })] })] })] }));
}
