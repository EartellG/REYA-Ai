// src/pages/reya-app.tsx
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarImage } from "@/components/ui/avatar";
import Sidebar, { type TabKey } from "@/components/ui/sidebar";
import ProjectsGrid from "@/components/ui/ProjectsGrid";
import ChatPanel from "@/components/ui/ChatPanel";
import LogicEngineTab from "@/components/ui/LogicEngineTab";
import LiveAvatarTab from "@/components/ui/LiveAvatarTab";
import ErrorBoundary from "@/components/ui/ErrorBoundary";
import { useModes } from "@/state/modes";
import LanguageTutorPanel from "@/components/ui/LanguageTutorPanel";
import KnowledgeBasePanel from "@/components/ui/KnowledgeBasePanel"; // ← correct path/name

// Include ALL keys your Sidebar emits
const TAB_KEYS = ["chat", "projects", "avatar", "logic", "tutor", "kb", "settings"] as const;
const isTabKey = (v: unknown): v is TabKey =>
  (TAB_KEYS as readonly string[]).includes(v as string);

export default function REYAApp() {
  const [activeTab, setActiveTab] = useState<TabKey>(() => {
    const saved = localStorage.getItem("reya-active-tab");
    return isTabKey(saved) ? saved : "projects";
  });

  useEffect(() => {
    localStorage.setItem("reya-active-tab", activeTab);
  }, [activeTab]);

  const { modes, toggle } = useModes();

  return (
    <div className="grid grid-cols-12 min-h-screen bg-gray-950 text-white">
      {/* Sidebar */}
      <div className="col-span-2 bg-gray-900 p-4">
        <Sidebar current={activeTab} onChange={setActiveTab} />
      </div>

      {/* Main */}
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
                onClick={() => toggle("multimodal")}
              >
                🧠 Multimodal
              </Button>
              <Button
                variant={modes.liveAvatar ? "default" : "outline"}
                onClick={() => toggle("liveAvatar")}
              >
                🧍 Live Avatar
              </Button>
              <Button
                variant={modes.logicEngine ? "default" : "outline"}
                onClick={() => toggle("logicEngine")}
              >
                🧮 Logic
              </Button>
              <Button
                variant={modes.offlineSmart ? "default" : "outline"}
                onClick={() => toggle("offlineSmart")}
              >
                🌐 Offline
              </Button>
            </div>
          </div>

          {/* Dynamic Tab Area */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === "projects" && <ProjectsGrid />}

            {activeTab === "chat" && <ChatPanel />}

            {activeTab === "avatar" && <LiveAvatarTab />}

            {activeTab === "logic" && <LogicEngineTab />}

            {activeTab === "tutor" && <LanguageTutorPanel />}

            {activeTab === "kb" && <KnowledgeBasePanel />}

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
