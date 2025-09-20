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
import RolesPage from "./RolesPage";
import SettingsTab from "@/tabs/SettingsTab";
import VoiceController from "@/components/ui/VoiceController";
import { useChatStore } from "@/state/chatStore";

const TAB_KEYS = ["chat", "projects", "tutor", "kb", "logic", "avatar", "settings", "roles"] as const;
const isTabKey = (v: unknown): v is TabKey => (TAB_KEYS as readonly string[]).includes(v as string);

export default function REYAApp() {
  const [activeTab, setActiveTab] = useState<TabKey>(() => {
    const saved = localStorage.getItem("reya-active-tab");
    return isTabKey(saved) ? saved : "projects";
  });
  useEffect(() => { localStorage.setItem("reya-active-tab", activeTab); }, [activeTab]);

  const { modes, toggle } = useModes();
  const [navOpen, setNavOpen] = useState(false);

  // chat store hooks
  const addUser = useChatStore((s) => s.addUser);
  const addAssistant = useChatStore((s) => s.addAssistant);

  // Auto-close drawer on desktop
  useEffect(() => {
    const mql = window.matchMedia("(min-width: 1024px)");
    const handler = () => mql.matches && setNavOpen(false);
    mql.addEventListener?.("change", handler);
    return () => mql.removeEventListener?.("change", handler);
  }, []);

  return (
    <div data-theme="glass-aurora-purple" className="min-h-[100dvh] text-white ga-aurora safe-b">
      {/* Topbar — glass with neon pills */}
      <header className="sticky top-0 z-40 ga-panel backdrop-blur border border-white/10 rounded-2xl mx-2 mt-2 px-3 py-2 md:mx-3 md:px-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              className="md:hidden inline-flex h-10 w-10 items-center justify-center ga-btn"
              onClick={() => setNavOpen(v => !v)}
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

          <div className="flex flex-wrap items-center gap-1 sm:gap-2">
            <VoiceController
              onTranscript={async (t) => {
                addUser(t);
                const reply = "Got it! Opening the right tab.";
                addAssistant(reply);
                try {
                  const r = await fetch("http://127.0.0.1:8000/tts", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ text: reply }),
                  });
                  const data = await r.json();
                  if (r.ok && data.url) new Audio(data.url).play();
                } catch {}
              }}
              onNavigate={(tab) => setActiveTab(tab as TabKey)}
              lang="en-US"
            />

            <Button className="ga-btn" onClick={() => toggle("multimodal")}>
              🧠 <span className="hidden sm:inline ml-1">Multimodal</span>
            </Button>
            <Button className="ga-btn" onClick={() => toggle("liveAvatar")}>
              🧍 <span className="hidden sm:inline ml-1">Live Avatar</span>
            </Button>
            <Button className="ga-btn" onClick={() => toggle("logicEngine")}>
              🧮 <span className="hidden sm:inline ml-1">Logic</span>
            </Button>
            <Button className="ga-btn" onClick={() => toggle("offlineSmart")}>
              🌐 <span className="hidden sm:inline ml-1">Offline</span>
            </Button>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-12">
        {/* Sidebar — apply glass directly on aside; remove inner wrapper to avoid double panel */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-72 transform md:static md:col-span-2 md:w-auto md:translate-x-0 transition-transform duration-200 ${
            navOpen ? "translate-x-0" : "-translate-x-full"
          } ga-panel m-2 md:m-0 p-2`}
          aria-hidden={!navOpen}
        >
          <Sidebar
            current={activeTab}
            onChange={(k) => { setActiveTab(k); setNavOpen(false); }}
            mobileOpen={navOpen}
            onClose={() => setNavOpen(false)}
          />
        </aside>

        {/* Content */}
        <main className="md:col-span-10">
          <ErrorBoundary
            fallback={
              <div className="p-10 text-center text-pink-400">
                <h2 className="text-2xl font-bold mb-4">💥 REYA Crashed</h2>
                <p>Something went wrong. Please reload or switch tabs.</p>
              </div>
            }
          >
            <div className="p-3 sm:p-4">
              <div className="ga-panel p-3 sm:p-4">
                <div className="space-y-3 sm:space-y-4">
                  {activeTab === "projects" && <div className="ga-card p-4"><ProjectsGrid /></div>}
                  {activeTab === "chat" &&     <div className="ga-card p-4"><ChatPanel /></div>}
                  {activeTab === "avatar" &&   <div className="ga-card p-4"><LiveAvatarTab /></div>}
                  {activeTab === "logic" &&    <div className="ga-card p-4"><LogicEngineTab /></div>}
                  {activeTab === "tutor" &&    <div className="ga-card p-4"><LanguageTutorPanel /></div>}
                  {activeTab === "kb" &&       <div className="ga-card p-4"><KnowledgeBaseTab /></div>}
                  {activeTab === "roles" &&    <div className="ga-card p-4"><RolesPage /></div>}
                  {activeTab === "settings" && <div className="ga-card p-4"><SettingsTab /></div>}
                </div>
              </div>
            </div>
          </ErrorBoundary>
        </main>
      </div>

      {/* Mobile backdrop */}
      {navOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 md:hidden" onClick={() => setNavOpen(false)} />
      )}
    </div>
  );
}
