import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  planProject,
  scaffoldProject,
  getStatus,
  getDownloadUrl,
  type PlanResponse,
  type StatusResponse,
} from "@/lib/projectClient";

type Target = "web" | "mobile" | "desktop";

export default function ProjectsGrid() {
  const [idea, setIdea] = useState("");
  const [target, setTarget] = useState<Target>("web");

  const [planning, setPlanning] = useState(false);
  const [plan, setPlan] = useState<PlanResponse | null>(null);

  const [scaffolding, setScaffolding] = useState(false);
  const [projectId, setProjectId] = useState<string | null>(null);

  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [polling, setPolling] = useState(false);
  const pollRef = useRef<number | null>(null);

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
    } catch (e) {
      console.error(e);
      alert("Planning failed. Check backend logs.");
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
    } catch (e) {
      console.error(e);
      alert("Scaffold failed. Check backend logs.");
    } finally {
      setScaffolding(false);
    }
  };

  const download = () => {
    if (!projectId) return;
    const url = getDownloadUrl(projectId);
    window.open(url, "_blank");
  };

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-2xl font-bold">📁 Projects</h2>
      <p className="text-zinc-400">
        Turn an idea into a runnable scaffold, watch build logs, then download a zip.
      </p>

      <Card className="bg-gray-900 border-gray-800">
        <CardContent className="p-4 space-y-3">
          <div className="flex gap-2">
            <Input
              value={idea}
              onChange={(e) => setIdea(e.target.value)}
              placeholder="Describe your app idea (e.g., 'AI Pomodoro with calendar sync')"
              className="flex-1"
            />
            <select
              value={target}
              onChange={(e) => setTarget(e.target.value as Target)}
              className="bg-gray-800 border border-gray-700 rounded px-2"
            >
              <option value="web">Web</option>
              <option value="mobile">Mobile</option>
              <option value="desktop">Desktop</option>
            </select>
            <Button onClick={handlePlan} disabled={planning}>
              {planning ? "Planning…" : "Plan"}
            </Button>
          </div>

          {plan && (
            <div className="grid md:grid-cols-2 gap-3">
              <div className="bg-gray-800 rounded p-3">
                <h3 className="font-semibold mb-2">Spec</h3>
                <pre className="whitespace-pre-wrap text-sm text-zinc-200">
                  {plan.spec}
                </pre>
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
            <div className="flex items-center gap-2">
              <Button onClick={handleScaffold} disabled={scaffolding}>
                {scaffolding ? "Scaffolding…" : "Generate Scaffold"}
              </Button>
              {canDownload && (
                <Button variant="secondary" onClick={download}>
                  ⬇ Download ZIP
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

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
                <Button variant="secondary" onClick={download}>
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
                  <span className="text-zinc-500 mr-2">{new Date(l.ts).toLocaleTimeString()}</span>
                  <span className="text-zinc-200">{l.line}</span>
                </div>
              ))}
              {polling && <div className="opacity-70">…streaming logs</div>}
              {status.error && <div className="text-red-400">Error: {status.error}</div>}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
