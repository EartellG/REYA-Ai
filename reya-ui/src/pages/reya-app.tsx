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
import KnowledgeBaseTab from "@/tabs/KnowledgeBaseTab";

const TAB_KEYS = ["chat", "projects", "tutor", "kb", "logic", "avatar", "settings"] as const;
const isTabKey = (v: unknown): v is TabKey => (TAB_KEYS as readonly string[]).includes(v as string);

export default function REYAApp() {
  const [activeTab, setActiveTab] = useState<TabKey>(() => {
    const saved = localStorage.getItem("reya-active-tab");
    return isTabKey(saved) ? saved : "projects";
  });
  useEffect(() => { localStorage.setItem("reya-active-tab", activeTab); }, [activeTab]);

  const { modes, toggle } = useModes();
  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Topbar */}
      <div className="sticky top-0 z-40 flex items-center justify-between gap-3 px-3 py-2 border-b border-gray-800 bg-gray-950/95 backdrop-blur md:px-4">
        <div className="flex items-center gap-3">
          <button
            className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-lg border border-gray-800"
            onClick={() => setNavOpen((v) => !v)}
            aria-label="Toggle navigation"
          >
            ☰
          </button>
        <div className="flex items-center gap-2">
            <Avatar className="h-8 w-8">
              <AvatarImage src="/ReyaAva.png" alt="REYA" />
            </Avatar>
            <h1 className="text-lg font-semibold">REYA</h1>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button variant={modes.multimodal ? "default" : "outline"} onClick={() => toggle("multimodal")}>🧠 Multimodal</Button>
          <Button variant={modes.liveAvatar ? "default" : "outline"} onClick={() => toggle("liveAvatar")}>🧍 Live Avatar</Button>
          <Button variant={modes.logicEngine ? "default" : "outline"} onClick={() => toggle("logicEngine")}>🧮 Logic</Button>
          <Button variant={modes.offlineSmart ? "default" : "outline"} onClick={() => toggle("offlineSmart")}>🌐 Offline</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12">
        {/* Sidebar (drawer on mobile) */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-72 transform bg-gray-900/80 transition-transform duration-200 md:static md:col-span-2 md:w-auto md:translate-x-0 ${navOpen ? "translate-x-0" : "-translate-x-full"}`}
        >
          <div className="h-full p-3">
            <Sidebar
              current={activeTab}
              onChange={(k) => { setActiveTab(k); setNavOpen(false); }}
            />
          </div>
        </aside>

        {/* Content */}
        <main className="md:col-span-10">
          <ErrorBoundary
            fallback={
              <div className="p-10 text-center text-red-500">
                <h2 className="text-2xl font-bold mb-4">💥 REYA Crashed</h2>
                <p>Something went wrong. Please reload or switch tabs.</p>
              </div>
            }
          >
            <div className="p-4">
              {activeTab === "projects" && <ProjectsGrid />}
              {activeTab === "chat" && <ChatPanel />}
              {activeTab === "avatar" && <LiveAvatarTab />}
              {activeTab === "logic" && <LogicEngineTab />}
              {activeTab === "tutor" && <LanguageTutorPanel />}
              {activeTab === "kb" && <KnowledgeBaseTab />}
              {activeTab === "settings" && (
                <div className="p-2">
                  <h2 className="text-2xl font-bold mb-2">Settings</h2>
                  <p>Coming soon: preferences, themes, and data export.</p>
                </div>
              )}
            </div>
          </ErrorBoundary>
        </main>
      </div>

      {/* Backdrop for the mobile drawer */}
      {navOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setNavOpen(false)}
        />
      )}
    </div>
  );
}
