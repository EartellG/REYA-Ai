// src/components/ui/ProjectsGrid.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";
import FileDropzone from "@/components/ui/FileDropzone";
import QuickFixPR from "@/components/ui/QuickFixPR";
import WireframesPanel from "@/features/wireframes/WireframesPanel";
import { useProjectDiscussions } from "@/state/projectDiscussions";

import {
  planProject,
  scaffoldProject,
  getStatus,
  getDownloadUrl,
  generateBatch,
  uploadFiles,
  reviewUpload,
  type PlanResponse,
  type StatusResponse,
  type BatchFile,
} from "@/lib/projectClient";

type Target = "web" | "mobile" | "desktop";

export default function ProjectsGrid() {
  const { toast } = useToast();

  // ----- Planner / Scaffold -----
  const [idea, setIdea] = useState("");
  const [target, setTarget] = useState<Target>("web");

  const [planning, setPlanning] = useState(false);
  const [plan, setPlan] = useState<PlanResponse | null>(null);

  const [scaffolding, setScaffolding] = useState(false);
  const [projectId, setProjectId] = useState<string | null>(null);

  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [polling, setPolling] = useState(false);
  const pollRef = useRef<number | null>(null);

  // Optional: jump to Chat → Project Discussions after Plan
  const [openDiscussAfterPlan, setOpenDiscussAfterPlan] = useState(true);
  const createThread = useProjectDiscussions(s => s.createThread);

  const canDownload = useMemo(
    () => status?.phase === "done" && !!projectId,
    [status?.phase, projectId]
  );

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  const startPolling = (pid: string) => {
    if (pollRef.current) window.clearInterval(pollRef.current);
    setPolling(true);
    pollRef.current = window.setInterval(async () => {
      try {
        const s = await getStatus(pid);
        setStatus(s);
        if (s.phase === "done" || s.phase === "error") {
          setPolling(false);
          if (pollRef.current) {
            window.clearInterval(pollRef.current);
            pollRef.current = null;
          }
        }
      } catch (e) {
        console.error(e);
        setPolling(false);
        if (pollRef.current) {
          window.clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }
    }, 1200);
  };

  const handlePlan = async () => {
    if (!idea.trim()) return;
    setPlan(null);
    setPlanning(true);
    try {
      const p = await planProject(idea.trim(), target);
      setPlan(p);
      toast({
        title: "Plan created",
        description: "Architect produced a spec and task list.",
        variant: "success",
      });

      // ⬇️ Optional hookup: open Project Discussions thread automatically
      if (openDiscussAfterPlan) {
        const seed =
          `I want to build: ${idea.trim()} (target: ${target}).\n\n` +
          `Here’s the first draft plan from Architect:\n\n` +
          `SPEC:\n${p.spec}\n\nTASKS:\n${p.tasks.map((t, i) => `${i + 1}. ${t}`).join("\n")}\n\n` +
          `Can we brainstorm scope, UX, and monetization?`;

        const threadId = createThread(idea.trim(), seed);

        window.dispatchEvent(
          new CustomEvent("reya:navigate", {
            detail: { tab: "chat", chatSub: "discuss", openThreadId: threadId },
          })
        );
      }
    } catch (e) {
      console.error(e);
      toast({
        title: "Planning failed",
        description: "Check backend logs.",
        variant: "destructive",
      });
    } finally {
      setPlanning(false);
    }
  };

  const handleScaffold = async () => {
    if (!plan?.spec) return;
    setScaffolding(true);
    try {
      const s = await scaffoldProject(plan.spec);
      setProjectId(s.project_id);
      setStatus({
        project_id: s.project_id,
        phase: "scaffolding",
        progress: 5,
        log: [{ ts: new Date().toISOString(), line: s.message }],
      });
      startPolling(s.project_id);
      toast({
        title: "Scaffold started",
        description: `Workspace: ${s.project_id}`,
      });
    } catch (e) {
      console.error(e);
      toast({
        title: "Scaffold failed",
        description: "Check backend logs.",
        variant: "destructive",
      });
    } finally {
      setScaffolding(false);
    }
  };

  const download = () => {
    if (!projectId) return;
    const url = getDownloadUrl(projectId);
    window.open(url, "_blank");
  };

  // ----- Code Review upload -----
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [review, setReview] = useState<string>("");

  async function handleUpload(files: File[]) {
    setReview("");
    try {
      const info = await uploadFiles(files); // -> { upload_id, saved, files }
      setUploadId(info.upload_id);
      toast({
        title: "Upload received",
        description: `${info.saved} file(s) staged for review.`,
        variant: "success",
      });
    } catch (e) {
      console.error(e);
      toast({
        title: "Upload failed",
        description: "Please try again.",
        variant: "destructive",
      });
    }
  }

  async function handleReview() {
    if (!uploadId) return;
    try {
      const r = await reviewUpload(uploadId);
      setReview(r.report);
      toast({
        title: "Review ready",
        description: "See the summary below.",
      });
    } catch (e) {
      console.error(e);
      toast({
        title: "Review failed",
        description: "Check backend logs.",
        variant: "destructive",
      });
    }
  }

  return (
    <div className="p-6 space-y-4">
      <WireframesPanel />

      <h2 className="text-2xl font-bold">📁 Projects</h2>
      <p className="text-zinc-400">
        Turn an idea into a runnable scaffold, watch build logs, then download a zip.
      </p>

      {/* ---- Plan Card ---- */}
      <Card className="bg-gray-900 border-gray-800">
        <CardContent className="p-4 space-y-3">
          <div className="flex flex-col sm:flex-row gap-2">
            <Input
              value={idea}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setIdea(e.target.value)}
              placeholder="Describe your app idea (e.g., 'AI Pomodoro with calendar sync')"
              className="flex-1"
            />
            <select
              value={target}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                setTarget(e.target.value as Target)
              }
              className="bg-gray-800 border border-gray-700 rounded px-2 h-10"
            >
              <option value="web">Web</option>
              <option value="mobile">Mobile</option>
              <option value="desktop">Desktop</option>
            </select>
            <Button onClick={handlePlan} disabled={planning}>
              {planning ? "Planning…" : "Plan"}
            </Button>
          </div>

          {/* Optional toggle */}
          <label className="flex items-center gap-2 text-sm opacity-80">
            <input
              type="checkbox"
              checked={openDiscussAfterPlan}
              onChange={(e) => setOpenDiscussAfterPlan(e.target.checked)}
            />
            Open a Project Discussion after planning
          </label>

          {plan && (
            <div className="grid md:grid-cols-2 gap-3">
              <div className="bg-gray-800 rounded p-3">
                <h3 className="font-semibold mb-2">Spec</h3>
                <pre className="whitespace-pre-wrap text-sm text-zinc-200">{plan.spec}</pre>
              </div>
              <div className="bg-gray-800 rounded p-3">
                <h3 className="font-semibold mb-2">Tasks</h3>
                <ol className="list-decimal ml-5 space-y-1 text-sm">
                  {plan.tasks.map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
                </ol>
              </div>
            </div>
          )}

          {plan && (
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={handleScaffold} disabled={scaffolding}>
                {scaffolding ? "Scaffolding…" : "Generate Scaffold"}
              </Button>

              {projectId && (
                <Button
                  variant="outline"
                  onClick={async () => {
                    try {
                      const files: BatchFile[] = [
                        {
                          path: "README.md",
                          content: `# ${projectId}\n\nGenerated by REYA.`,
                        },
                        {
                          path: "src/App.tsx",
                          content: `export default function App(){
  return <div className="p-6">Hello from REYA 🚀</div>
}`,
                        },
                        {
                          path: "src/main.tsx",
                          content: `import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
ReactDOM.createRoot(document.getElementById('root')!).render(<App />);`,
                        },
                      ];
                      await generateBatch(projectId, files, "Seed starter files");
                      toast({
                        title: "Files generated",
                        description: "Starter files added to the workspace.",
                        variant: "success",
                      });
                    } catch (e) {
                      console.error(e);
                      toast({
                        title: "Generation failed",
                        description: "Check backend logs.",
                        variant: "destructive",
                      });
                    }
                  }}
                >
                  🧩 Generate Files
                </Button>
              )}

              {canDownload && (
                <Button variant="outline" onClick={download}>
                  ⬇ Download ZIP
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ---- Build Status ---- */}
      {status && (
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Build Status</h3>
                <p className="text-sm text-zinc-400">
                  Project: {status.project_id} • Phase: {status.phase} • {status.progress}%
                </p>
              </div>
              {canDownload && (
                <Button variant="outline" onClick={download}>
                  ⬇ Download ZIP
                </Button>
              )}
            </div>

            <div className="h-2 w-full bg-gray-800 rounded">
              <div
                className="h-2 bg-emerald-500 rounded"
                style={{ width: `${Math.max(0, Math.min(100, status.progress))}%` }}
              />
            </div>

            <div className="bg-gray-800 rounded p-3 h-64 overflow-auto text-sm space-y-1">
              {status.log.map((l, i) => (
                <div key={i}>
                  <span className="text-zinc-500 mr-2">
                    {new Date(l.ts).toLocaleTimeString()}
                  </span>
                  <span className="text-zinc-200">{l.line}</span>
                </div>
              ))}
              {polling && <div className="opacity-70">…streaming logs</div>}
              {status.error && <div className="text-red-400">Error: {status.error}</div>}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ---- Code Review ---- */}
      <Card className="bg-gray-900 border-gray-800">
        <CardContent className="p-4 space-y-3">
          <h3 className="text-xl font-semibold">🧪 Code Review</h3>
          <p className="text-zinc-400">
            Drop a ZIP or multiple files. REYA will summarize issues and suggest fixes.
          </p>

          <FileDropzone onFiles={handleUpload} accept=".zip,.ts,.tsx,.js,.py,.json,.md" />

          <div className="flex items-center gap-2">
            <Button onClick={handleReview} disabled={!uploadId}>
              Run Review
            </Button>
            {uploadId && (
              <span className="text-xs text-zinc-500">Upload ID: {uploadId}</span>
            )}
          </div>

          {review && (
            <div className="bg-gray-800 rounded p-3 whitespace-pre-wrap text-sm">
              {review}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ---- Quick Fix / PR ---- */}
      <Card className="bg-gray-900 border-gray-800">
        <CardContent className="p-4 space-y-3">
          <h3 className="text-xl font-semibold">🛠️ Quick Fix & Create PR</h3>
          <p className="text-zinc-400">
            Drop the files you changed (or a folder). REYA will bundle a simulated PR you can
            download or attach to your repo.
          </p>
          <QuickFixPR />
        </CardContent>
      </Card>
    </div>
  );
}
