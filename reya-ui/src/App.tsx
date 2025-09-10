// src/App.tsx
import { useState } from "react";
import { ModesProvider } from "@/state/modes";
import Sidebar, { TabKey } from "@/components/ui/sidebar";
import TopModeBar from "@/components/TopModeBar";
import ChatPanel from "@/components/ui/ChatPanel";
import Projects from "@/components/ui/ProjectsGrid";
import LanguageTutorTab from "@/tabs/LanguageTutorTab";
import KnowledgeBaseTab from "@/tabs/KnowledgeBaseTab";

export default function App() {
  const [tab, setTab] = useState<TabKey>("projects");

  return (
    <ModesProvider>
      <div className="h-screen w-screen bg-zinc-950 text-zinc-100 flex">
        <Sidebar current={tab} onChange={setTab} />
        <main className="flex-1 flex flex-col">
          <TopModeBar />
          <div className="flex-1 overflow-auto">
            {tab === "chat" && <ChatPanel modes={{
              multimodal: false,
              liveAvatar: false,
              logicEngine: false,
              offlineSmart: false
            }} />}
            {tab === "projects" && <Projects />}
            {tab === "tutor" && <LanguageTutorTab />}
            {tab === "kb" && <KnowledgeBaseTab />}
            {tab === "settings" && <div className="p-6">Settings…</div>}
          </div>
        </main>
      </div>
    </ModesProvider>
  );
}
