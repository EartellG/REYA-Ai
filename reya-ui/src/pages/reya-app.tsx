/* eslint-disable react/react-in-jsx-scope */
import { useState, useEffect, useLayoutEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarImage } from "@/components/ui/avatar";
import Sidebar, { type TabKey } from "@/components/ui/sidebar";
import ProjectsGrid from "@/components/ui/ProjectsGrid";
import ChatPage from "@/tabs/ChatPage";
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
import ToasterMount from "@/components/ui/ToasterMount";

const TAB_KEYS = ["chat","projects","tutor","kb","logic","avatar","settings","roles"] as const;
const isTabKey = (v: unknown): v is TabKey => (TAB_KEYS as readonly string[]).includes(v as string);

export default function REYAApp() {
  // —— theme: make sure glass tokens are active on <html> —— 
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", "glass-aurora-purple");
  }, []);

  const [activeTab, setActiveTab] = useState<TabKey>(() => {
    const saved = localStorage.getItem("reya-active-tab");
    return isTabKey(saved) ? saved : "projects";
  });
  useEffect(() => { localStorage.setItem("reya-active-tab", activeTab); }, [activeTab]);

  const { modes, toggle } = useModes();
  const [navOpen, setNavOpen] = useState(false);

  const addUser = useChatStore((s) => s.addUser);
  const addAssistant = useChatStore((s) => s.addAssistant);

  // cross-page navigation events
  useEffect(() => {
    const handler = async (e: Event) => {
      const d = (e as CustomEvent).detail || {};
      if (d.tab) setActiveTab(d.tab as TabKey);
      if (d.openThreadId) {
        const mod = await import("@/state/projectDiscussions");
        mod.useProjectDiscussions.getState().openThread(d.openThreadId as string);
      }
    };
    window.addEventListener("reya:navigate", handler as EventListener);
    return () => window.removeEventListener("reya:navigate", handler as EventListener);
  }, []);

  // close drawer if we cross to desktop
  useEffect(() => {
    const mql = window.matchMedia("(min-width: 1024px)");
    const h = () => mql.matches && setNavOpen(false);
    mql.addEventListener?.("change", h);
    return () => mql.removeEventListener?.("change", h);
  }, []);

  // —— topbar height measure —— 
  const topbarRef = useRef<HTMLDivElement | null>(null);
  const [topbarH, setTopbarH] = useState(0);
  useLayoutEffect(() => {
    const measure = () => {
      const h = topbarRef.current?.getBoundingClientRect().height ?? 0;
      setTopbarH(h);
      document.documentElement.style.setProperty("--topbar-h", `${h}px`);
    };
    measure();
    const ro = new ResizeObserver(measure);
    if (topbarRef.current) ro.observe(topbarRef.current);
    window.addEventListener("resize", measure);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, []);

  return (
    <ToasterMount>
      <div className="min-h-[100dvh] text-white ga-aurora">
        {/* TOPBAR */}
        <div ref={topbarRef} className="top-0 z-50 px-3 py-1.5 md:px-4">
          <div className="ga-panel ga-outline rounded-2xl px-3 py-1.5 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="lg:hidden">
                <button
                  className="inline-flex h-9 w-9 items-center justify-center rounded-xl ga-btn"
                  onClick={() => setNavOpen(v => !v)}
                  aria-label="Toggle navigation"
                >
                  ☰
                </button>
              </div>
              <div className="flex items-center gap-2">
                <Avatar className="h-8 w-8">
                  <AvatarImage src="/ReyaAva.png" alt="REYA" />
                </Avatar>
                <h1 className="text-lg font-semibold">REYA</h1>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-1.5">
              <VoiceController
                onTranscript={async (t) => {
                  addUser(t);
                  const reply = "Got it! Opening the right tab.";
                  addAssistant(reply);
                }}
                onNavigate={(tab) => setActiveTab(tab as TabKey)}
                lang="en-US"
                className="ga-btn"
              />
              <Button className="ga-btn" variant={modes.multimodal ? "default" : "outline"} onClick={() => toggle("multimodal")}>🧠 Multimodal</Button>
              <Button className="ga-btn" variant={modes.liveAvatar ? "default" : "outline"} onClick={() => toggle("liveAvatar")}>🧍 Live Avatar</Button>
              <Button className="ga-btn" variant={modes.logicEngine ? "default" : "outline"} onClick={() => toggle("logicEngine")}>🧮 Logic</Button>
              <Button className="ga-btn" variant={modes.offlineSmart ? "default" : "outline"} onClick={() => toggle("offlineSmart")}>🌐 Offline</Button>
            </div>
          </div>
        </div>

        {/* spacer to avoid flash */}
        <div style={{ paddingTop: topbarH ? 8 : 0 }} />

        <div
          className="grid grid-cols-1 lg:grid-cols-12 gap-0 px-3 pb-6 md:px-4"
          style={{ marginTop: `calc(var(--topbar-h, 0px) - ${topbarH ? 8 : 0}px)` }}
        >
          {/* SIDEBAR */}
          <aside className="lg:col-span-2">
            <Sidebar
              current={activeTab}
              onChange={(k) => { setActiveTab(k); setNavOpen(false); }}
              mobileOpen={navOpen}
              onClose={() => setNavOpen(false)}
            />
          </aside>

          {/* CONTENT */}
          <main className="lg:col-span-10">
            <ErrorBoundary
              fallback={
                <div className="p-10 text-center text-red-400 ga-panel ga-outline rounded-xl">
                  <h2 className="text-2xl font-bold mb-4">💥 REYA Crashed</h2>
                  <p>Something went wrong. Please reload or switch tabs.</p>
                </div>
              }
            >
              <div className="ga-panel ga-outline rounded-2xl p-3 sm:p-4">
                {activeTab === "projects" && <ProjectsGrid />}
                {activeTab === "chat" && <ChatPage />}
                {activeTab === "avatar" && <LiveAvatarTab />}
                {activeTab === "logic" && <LogicEngineTab />}
                {activeTab === "tutor" && <LanguageTutorPanel />}
                {activeTab === "kb" && <KnowledgeBaseTab />}
                {activeTab === "roles" && <RolesPage />}
                {activeTab === "settings" && <SettingsTab />}
              </div>
            </ErrorBoundary>
          </main>
        </div>
      </div>
    </ToasterMount>
  );
}
