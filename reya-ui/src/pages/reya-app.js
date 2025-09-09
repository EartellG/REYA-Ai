import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarImage } from "@/components/ui/avatar";
import { Sidebar } from "@/components/ui/sidebar";
import ProjectsGrid from "@/components/ui/ProjectsGrid";
import ChatPanel from "@/components/ui/ChatPanel";
import LogicEngineTab from "@/components/ui/LogicEngineTab";
import LiveAvatarTab from "@/components/ui/LiveAvatarTab";
export default function REYAApp() {
    const [activeTab, setActiveTab] = useState("Projects");
    const [modes, setModes] = useState({
        multimodal: false,
        liveAvatar: false,
        logicEngine: false,
        offlineSmart: false,
    });
    const toggleMode = (key) => {
        setModes((prev) => ({ ...prev, [key]: !prev[key] }));
    };
    return (_jsxs("div", { className: "grid grid-cols-12 min-h-screen bg-gray-950 text-white", children: [_jsx("div", { className: "col-span-2 bg-gray-900 p-4", children: _jsx(Sidebar, { items: ["Chat", "Projects", "Avatar", "Logic", "Settings"], activeTab: activeTab, onTabChange: setActiveTab }) }), _jsxs("div", { className: "col-span-10 flex flex-col", children: [_jsxs("div", { className: "flex items-center justify-between p-4 border-b border-gray-800", children: [_jsxs("div", { className: "flex items-center gap-4", children: [_jsx(Avatar, { children: _jsx(AvatarImage, { src: "/ReyaAva.png", alt: "REYA" }) }), _jsx("h1", { className: "text-xl font-semibold", children: "REYA" })] }), _jsxs("div", { className: "flex gap-2", children: [_jsx(Button, { variant: modes.multimodal ? "default" : "outline", onClick: () => toggleMode("multimodal"), children: "\uD83E\uDDE0 Multimodal Mode" }), _jsx(Button, { variant: modes.liveAvatar ? "default" : "outline", onClick: () => toggleMode("liveAvatar"), children: "\uD83E\uDDCD Live Avatar Mode" }), _jsx(Button, { variant: modes.logicEngine ? "default" : "outline", onClick: () => toggleMode("logicEngine"), children: "\uD83E\uDDEE Logic Engine" }), _jsx(Button, { variant: modes.offlineSmart ? "default" : "outline", onClick: () => toggleMode("offlineSmart"), children: "\uD83C\uDF10 Offline Smart Mode" })] })] }), _jsxs("div", { className: "flex-1 overflow-y-auto", children: [activeTab === "Projects" && _jsx(ProjectsGrid, {}), activeTab === "Chat" && _jsx(ChatPanel, { modes: modes }), activeTab === "Avatar" && _jsx(LiveAvatarTab, {}), activeTab === "Logic" && _jsx(LogicEngineTab, {}), activeTab === "Settings" && (_jsxs("div", { className: "p-6", children: [_jsx("h2", { className: "text-2xl font-bold mb-2", children: "Settings" }), _jsx("p", { children: "Coming soon: preferences, themes, and data export options." })] }))] })] })] }));
}
