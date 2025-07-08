import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarImage } from "@/components/ui/avatar";
import { Sidebar } from "@/components/ui/sidebar";
import ProjectsGrid from "@/components/ui/ProjectsGrid";
import ChatPanel from "@/components/ui/ChatPanel";
import LogicEngineTab from "@/components/ui/LogicEngineTab";
import LiveAvatarTab from "@/components/ui/LiveAvatarTab";
import ErrorBoundary from "@/components/ui/ErrorBoundary"; // ✅ remove curly braces

export default function REYAApp() {
  // Persistent tab selection
  const [activeTab, setActiveTab] = useState(() => {
    return localStorage.getItem("reya-active-tab") || "Projects";
  });

  useEffect(() => {
    localStorage.setItem("reya-active-tab", activeTab);
  }, [activeTab]);

  // Mode toggles
  const [modes, setModes] = useState({
    multimodal: false,
    liveAvatar: false,
    logicEngine: false,
    offlineSmart: false,
  });

  const toggleMode = (key: keyof typeof modes) => {
    setModes((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="grid grid-cols-12 min-h-screen bg-gray-950 text-white">
      {/* Sidebar */}
      <div className="col-span-2 bg-gray-900 p-4">
        <Sidebar
          items={["Chat", "Projects", "Avatar", "Logic", "Settings"]}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
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
            {activeTab === "Projects" && <ProjectsGrid />}
            {activeTab === "Chat" && <ChatPanel modes={modes} key="chat-panel" />}
            {activeTab === "Avatar" && <LiveAvatarTab />}
            {activeTab === "Logic" && <LogicEngineTab />}
            {activeTab === "Settings" && (
              <div className="p-6">
                <h2 className="text-2xl font-bold mb-2">Settings</h2>
                <p>Coming soon: preferences, themes, and data export.</p>
                <p style={{ color: "red" }}>Build: TESTING FRONTEND CACHE FIX</p>

              </div>
            )}
          </div>
        </ErrorBoundary>
      </div>
    </div>
  );
}
