// src/pages/reya-app.tsx
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarImage } from "@/components/ui/avatar";
import Sidebar, { type TabKey } from "@/components/ui/sidebar"; // ⬅️ import TabKey type
import ProjectsGrid from "@/components/ui/ProjectsGrid";
import ChatPanel from "@/components/ui/ChatPanel";
import LogicEngineTab from "@/components/ui/LogicEngineTab";
import LiveAvatarTab from "@/components/ui/LiveAvatarTab";
import ErrorBoundary from "@/components/ui/ErrorBoundary";

const TAB_KEYS = ["chat", "projects", "avatar", "logic", "settings"] as const;
const isTabKey = (v: unknown): v is TabKey => (TAB_KEYS as readonly string[]).includes(v as string);

export default function REYAApp() {
  // ✅ constrain to TabKey & sanitize localStorage
  const [activeTab, setActiveTab] = useState<TabKey>(() => {
    const saved = localStorage.getItem("reya-active-tab");
    return isTabKey(saved) ? saved : "projects";
  });

  useEffect(() => {
    localStorage.setItem("reya-active-tab", activeTab);
  }, [activeTab]);

  // Mode toggles
  type Modes = {
    multimodal: boolean;
    liveAvatar: boolean;
    logicEngine: boolean;
    offlineSmart: boolean;
  };

  const [modes, setModes] = useState<Modes>({
    multimodal: false,
    liveAvatar: false,
    logicEngine: false,
    offlineSmart: false,
  });

  const toggleMode = (key: keyof Modes) => {
    setModes((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="grid grid-cols-12 min-h-screen bg-gray-950 text-white">
      {/* Sidebar */}
      <div className="col-span-2 bg-gray-900 p-4">
        <Sidebar current={activeTab} onChange={setActiveTab} />
      </div>

      {/* Main App Content wrapped in ErrorBoundary */}
      <div className="col-span-10 flex flex-col">
        <ErrorBoundary
          fallback={
            <div className="p-10 text-center text-red-500">
              <h2 className="text-2xl font-bold mb-4">💥 REYA Crashed</h2>
              <p>Something went wrong. Please reload or switch tabs.</p>
            </div>
          }
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-800">
            <div className="flex items-center gap-4">
              <Avatar>
                <AvatarImage src="/ReyaAva.png" alt="REYA" />
              </Avatar>
              <h1 className="text-xl font-semibold">REYA</h1>
            </div>
            <div className="flex gap-2">
              <Button
                variant={modes.multimodal ? "default" : "outline"}
                onClick={() => toggleMode("multimodal")}
              >
                🧠 Multimodal Mode
              </Button>
              <Button
                variant={modes.liveAvatar ? "default" : "outline"}
                onClick={() => toggleMode("liveAvatar")}
              >
                🧍 Live Avatar Mode
              </Button>
              <Button
                variant={modes.logicEngine ? "default" : "outline"}
                onClick={() => toggleMode("logicEngine")}
              >
                🧮 Logic Engine
              </Button>
              <Button
                variant={modes.offlineSmart ? "default" : "outline"}
                onClick={() => toggleMode("offlineSmart")}
              >
                🌐 Offline Smart Mode
              </Button>
            </div>
          </div>

          {/* Dynamic Tab Area */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === "projects" && <ProjectsGrid />}
            {activeTab === "chat" && <ChatPanel modes={modes} key="chat-panel" />}
            {activeTab === "avatar" && <LiveAvatarTab />}
            {activeTab === "logic" && <LogicEngineTab />}
            {activeTab === "settings" && (
              <div className="p-6">
                <h2 className="text-2xl font-bold mb-2">Settings</h2>
                <p>Coming soon: preferences, themes, and data export.</p>
              </div>
            )}
          </div>
        </ErrorBoundary>
      </div>
    </div>
  );
}
