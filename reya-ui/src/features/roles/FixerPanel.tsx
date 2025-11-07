// src/features/roles/FixerPanel.tsx
import React, { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";

const API = "http://127.0.0.1:8000";

/** Types that mirror backend */
type FileBlob = { path: string; contents: string };
type Finding = { path: string; notes: string[] }; // legacy
type ReviewIssue = {
  id?: string;
  file?: string;
  line?: number;
  col?: number;
  severity?: "error" | "warning" | "info";
  message: string;
  suggestion?: string;
  rule?: string;
  source?: "eslint" | "ruff" | "inline";
};

type SuggestReq = {
  files: FileBlob[];
  findings?: Finding[];
  issues?: ReviewIssue[];
  strategy?: "safe" | "aggressive";
  only_paths?: string[];
};

type Patch = { path: string; diff: string };
type SuggestResp = {
  ok: boolean;
  summary: string;
  patches: Patch[];
  stats?: Record<string, number>;
};

type ApplyReq = { files: FileBlob[]; patches: Patch[] };
type ApplyResp = { ok: boolean; summary: string; files: FileBlob[] };

type ApplyAndSaveResp = {
  ok: boolean;
  summary: string;
  written: number;
  files_written: string[];
  errors: string[];
  files: FileBlob[];
};

/** Workspace diff API types */
type FileDiff = { path: string; diff: string };
type DiffReply = { diffs: FileDiff[] };

export default function FixerPanel() {
  const { toast } = useToast();

  const [status, setStatus] = useState<string>("");
  const [filesJSON, setFilesJSON] = useState<string>(
    '[\n  {\n    "path": "reya-ui/src/components/Old.tsx",\n    "contents": "// TODO: fix issue\\nconsole.log(\\"debug\\")\\n"\n  }\n]'
  );
  const [issuesJSON, setIssuesJSON] = useState<string>("[]");
  const [strategy, setStrategy] = useState<"safe" | "aggressive">("safe");

  const [patches, setPatches] = useState<Patch[] | null>(null);
  const [suggestSummary, setSuggestSummary] = useState<string>("");
  const [applyResult, setApplyResult] = useState<ApplyResp | null>(null);

  const [saveSummary, setSaveSummary] = useState<string>("");
  const [filesWritten, setFilesWritten] = useState<string[]>([]);
  const [saveErrors, setSaveErrors] = useState<string[]>([]);
  const [savedPaths, setSavedPaths] = useState<Set<string>>(new Set());

  const [loadingSuggest, setLoadingSuggest] = useState(false);
  const [loadingApply, setLoadingApply] = useState(false);
  const [loadingSave, setLoadingSave] = useState(false);
  const [loadingDiff, setLoadingDiff] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** Diff preview state */
  const [diffs, setDiffs] = useState<FileDiff[] | null>(null);

  // Prefill: backend first, then localStorage fallback (from Reviewer)
  useEffect(() => {
    let cancelled = false;

    async function loadPrefill() {
      setStatus("Checking for Reviewer → Fixer handoff…");
      try {
        const res = await fetch(`${API}/roles/fixer/prefill`);
        if (res.ok) {
          const data = await res.json();
          if (!cancelled && data?.prefill) {
            const p = data.prefill as {
              files?: FileBlob[];
              issues?: ReviewIssue[];
              findings?: Finding[];
            };
            if (p.files?.length) setFilesJSON(JSON.stringify(p.files, null, 2));
            if (p.issues) setIssuesJSON(JSON.stringify(p.issues, null, 2));
            else if (p.findings) setIssuesJSON(JSON.stringify(p.findings, null, 2));
            setStatus("Loaded handoff from backend ✅");
            return;
          }
        }
      } catch {}

      try {
        const raw = localStorage.getItem("reviewer:prefill");
        if (raw) {
          const parsed = JSON.parse(raw);
          if (!cancelled) {
            if (parsed.files) setFilesJSON(JSON.stringify(parsed.files, null, 2));
            if (parsed.issues) setIssuesJSON(JSON.stringify(parsed.issues, null, 2));
            else if (parsed.findings) setIssuesJSON(JSON.stringify(parsed.findings, null, 2));
            setStatus("Loaded handoff from localStorage ✅");
            localStorage.removeItem("reviewer:prefill");
            return;
          }
        }
      } catch {}

      if (!cancelled) setStatus("No incoming handoff found.");
    }

    loadPrefill();
    return () => {
      cancelled = true;
    };
  }, []);

  // In-page handoff from Reviewer
  useEffect(() => {
    const onHandoff = (e: Event) => {
      const d = (e as CustomEvent).detail;
      if (!d || d.target !== "fixer") return;

      const files = d.payload?.files;
      const issues = d.payload?.issues ?? d.payload?.findings;
      if (files) setFilesJSON(JSON.stringify(files, null, 2));
      if (issues) setIssuesJSON(JSON.stringify(issues, null, 2));
      setStatus("Loaded Reviewer → Fixer (in-page) ✅");
      toast({ variant: "success", title: "Received from Reviewer", description: "Handoff loaded" });
    };
    window.addEventListener("reya:handoff", onHandoff as EventListener);
    return () => window.removeEventListener("reya:handoff", onHandoff as EventListener);
  }, [toast]);

  function parseJSON<T>(label: string, src: string): T | null {
    try {
      return JSON.parse(src) as T;
    } catch (e: any) {
      setError(`${label} JSON parse error: ${e.message || e}`);
      toast({ variant: "destructive", title: "JSON parse error", description: `${label}: ${e.message || e}` });
      return null;
    }
  }

  async function suggestPatches() {
    setError(null);
    setPatches(null);
    setApplyResult(null);
    setSaveSummary("");
    setFilesWritten([]);
    setSaveErrors([]);
    setDiffs(null);
    setLoadingSuggest(true);
    setStatus("Suggesting patches…");

    const files = parseJSON<FileBlob[]>("Files", filesJSON);
    if (!files || !Array.isArray(files) || files.length === 0) {
      setLoadingSuggest(false);
      setStatus("Please provide at least one file.");
      toast({ variant: "destructive", title: "Provide files", description: "Add at least one file to continue." });
      return;
    }

    const maybeIssues = parseJSON<any[]>("Issues/Findings", issuesJSON) || [];
    const body: SuggestReq = { files, strategy };

    if (maybeIssues.some((x) => typeof x?.message === "string" || x?.file)) {
      body.issues = maybeIssues as ReviewIssue[];
    } else if (maybeIssues.some((x) => Array.isArray(x?.notes) && x?.path)) {
      body.findings = maybeIssues as Finding[];
    }

    try {
      const res = await fetch(`${API}/roles/fixer/suggest_patches`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data: SuggestResp = await res.json();
      if (!res.ok) throw new Error((data as any)?.detail || "request failed");

      setPatches(data.patches || []);
      setSuggestSummary(data.summary || "");
      setStatus("Patches ready ✅");
      toast({ title: "Patches generated", description: `${data.patches?.length ?? 0} patch(es)` });
    } catch (e: any) {
      setError(e.message || "Suggest failed");
      setStatus("Suggest failed");
      toast({ variant: "destructive", title: "Suggest failed", description: String(e?.message ?? e) });
    } finally {
      setLoadingSuggest(false);
    }
  }

  async function applyPatches() {
    if (!patches?.length) {
      setError("No patches to apply. Run Suggest first.");
      toast({ variant: "destructive", title: "No patches", description: "Run Suggest first." });
      return;
    }
    setError(null);
    setLoadingApply(true);
    setStatus("Applying patches…");
    setDiffs(null); // clear old diff

    const files = parseJSON<FileBlob[]>("Files", filesJSON);
    if (!files) {
      setLoadingApply(false);
      return;
    }

    const body: ApplyReq = { files, patches };

    try {
      const res = await fetch(`${API}/roles/fixer/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data: ApplyResp = await res.json();
      if (!res.ok) throw new Error((data as any)?.detail || "request failed");

      setApplyResult(data);
      setFilesJSON(JSON.stringify(data.files, null, 2));
      setStatus("Applied in memory ✅");
      toast({ title: "Applied (in-memory)", description: data.summary });
    } catch (e: any) {
      setError(e.message || "Apply failed");
      setStatus("Apply failed");
      toast({ variant: "destructive", title: "Apply failed", description: String(e?.message ?? e) });
    } finally {
      setLoadingApply(false);
    }
  }

  async function previewDiff() {
    setLoadingDiff(true);
    setDiffs(null);
    setStatus("Generating diff preview…");

    const files = parseJSON<FileBlob[]>("Files", filesJSON);
    if (!files || !Array.isArray(files) || files.length === 0) {
      setLoadingDiff(false);
      setStatus("Provide files to diff.");
      toast({ variant: "destructive", title: "No files", description: "Provide files to preview diff." });
      return;
    }

    try {
      const res = await fetch(`${API}/workspace/diff`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ files }),
      });
      const data: DiffReply = await res.json();
      if (!res.ok) throw new Error((data as any)?.detail || "diff failed");
      setDiffs(data.diffs || []);
      setStatus("Diff preview ready ✅");
      toast({ title: "Diff ready", description: `${data.diffs?.length ?? 0} file(s)` });
    } catch (e: any) {
      setStatus("Diff failed");
      toast({ variant: "destructive", title: "Diff failed", description: String(e?.message ?? e) });
    } finally {
      setLoadingDiff(false);
    }
  }

  async function applyAndSave() {
    if (!patches?.length) {
      setError("No patches to save. Run Suggest first.");
      toast({ variant: "destructive", title: "No patches", description: "Run Suggest first." });
      return;
    }
    setError(null);
    setLoadingSave(true);
    setStatus("Applying + writing files…");
    setSaveSummary("");
    setFilesWritten([]);
    setSaveErrors([]);
    setDiffs(null); // clear preview after save attempt

    const files = parseJSON<FileBlob[]>("Files", filesJSON);
    if (!files) {
      setLoadingSave(false);
      return;
    }

    try {
      const res = await fetch(`${API}/roles/fixer/apply_and_save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ files, patches }),
      });
      const data: ApplyAndSaveResp = await res.json();
      if (!res.ok) throw new Error((data as any)?.detail || "request failed");

      setSaveSummary(data.summary);
      setFilesWritten(data.files_written || []);
      setSaveErrors(data.errors || []);
      setFilesJSON(JSON.stringify(data.files, null, 2));
      setStatus("Applied & saved ✅");

      const s = new Set(savedPaths);
      (data.files_written || []).forEach((p) => s.add(p));
      setSavedPaths(s);

      toast({
        variant: data.ok ? "success" : "destructive",
        title: data.ok ? "Saved to workspace" : "Save had issues",
        description: data.summary,
      });
    } catch (e: any) {
      setError(e.message || "Apply & Save failed");
      setStatus("Apply & Save failed");
      toast({ variant: "destructive", title: "Save failed", description: String(e?.message ?? e) });
    } finally {
      setLoadingSave(false);
    }
  }

  return (
    <Card className="ga-panel ga-outline">
      <CardContent className="space-y-4 p-4">
        {status && <div className="text-sm ga-subtle">{status}</div>}
        {error && <div className="text-sm text-red-600">{error}</div>}

        {/* Files JSON */}
        <label className="grid gap-1">
          <span className="text-sm font-medium">Files (JSON)</span>
          <Textarea
            className="min-h-40 font-mono text-sm"
            spellCheck={false}
            value={filesJSON}
            onChange={(e) => setFilesJSON(e.target.value)}
            placeholder='[{"path":"file.ts","contents":"..."}]'
          />
        </label>

        {/* Issues/Findings JSON */}
        <label className="grid gap-1">
          <span className="text-sm font-medium">Issues / Findings (JSON)</span>
          <Textarea
            className="min-h-28 font-mono text-sm"
            spellCheck={false}
            value={issuesJSON}
            onChange={(e) => setIssuesJSON(e.target.value)}
            placeholder='[{"file":"file.ts","message":"Avoid console.log","severity":"warning"}]'
          />
        </label>

        {/* Strategy + Actions */}
        <div className="grid gap-3 sm:grid-cols-4 items-end">
          <label className="grid gap-1 sm:col-span-1">
            <span className="text-sm font-medium">Strategy</span>
            <Input
              value={strategy}
              onChange={(e) =>
                setStrategy((e.target.value === "aggressive" ? "aggressive" : "safe") as "safe" | "aggressive")
              }
              list="fixer-strategies"
            />
            <datalist id="fixer-strategies">
              <option value="safe" />
              <option value="aggressive" />
            </datalist>
          </label>

          <div className="flex gap-2 sm:col-span-3 flex-wrap">
            <Button className="ga-btn" disabled={loadingSuggest} onClick={suggestPatches}>
              {loadingSuggest ? "Suggesting…" : "Suggest patches"}
            </Button>
            <Button variant="outline" disabled={loadingApply || !patches?.length} onClick={applyPatches}>
              {loadingApply ? "Applying…" : "Apply (in memory)"}
            </Button>
            <Button variant="outline" disabled={loadingDiff} onClick={previewDiff}>
              {loadingDiff ? "Diffing…" : "Preview diff"}
            </Button>
            <Button
              variant={patches?.length ? "secondary" : "outline"}
              disabled={loadingSave || !patches?.length}
              onClick={applyAndSave}
            >
              {loadingSave ? "Saving…" : "Apply & Save"}
            </Button>
          </div>
        </div>

        {suggestSummary && (
          <div className="text-sm bg-zinc-100 text-zinc-800 rounded p-2">{suggestSummary}</div>
        )}

        {patches?.length ? (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Patches</h3>
            <div className="grid gap-3">
              {patches.map((p, i) => {
                const saved = savedPaths.has(p.path);
                return (
                  <div key={i} className="border rounded overflow-hidden">
                    <div className="px-3 py-2 text-xs bg-zinc-100 text-zinc-700 flex items-center gap-2">
                      <span>{p.path}</span>
                      {saved && (
                        <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-500/15 border border-emerald-500/40">
                          ✅ saved
                        </span>
                      )}
                    </div>
                    <pre className="p-3 text-xs overflow-auto">
                      <code>{p.diff}</code>
                    </pre>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}

        {diffs?.length ? (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Diff Preview (Workspace vs Proposed)</h3>
            <div className="grid gap-3">
              {diffs.map((d, i) => (
                <div key={i} className="border rounded overflow-hidden">
                  <div className="px-3 py-2 text-xs bg-zinc-100 text-zinc-700">{d.path}</div>
                  <pre className="p-3 text-xs overflow-auto">
                    <code>{d.diff || "No changes."}</code>
                  </pre>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {applyResult && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Applied Files (in memory)</h3>
            <div className="text-sm ga-subtle">{applyResult.summary}</div>
            <div className="grid gap-3">
              {applyResult.files.map((f, i) => (
                <div key={i} className="border rounded overflow-hidden">
                  <div className="px-3 py-2 text-xs bg-zinc-100 text-zinc-700">{f.path}</div>
                  <pre className="p-3 text-sm overflow-auto">
                    <code>{f.contents}</code>
                  </pre>
                </div>
              ))}
            </div>
          </div>
        )}

        {saveSummary && (
          <div className="space-y-2">
            <h3 className="text-lg font-semibold">Apply & Save</h3>
            <div className="text-sm">{saveSummary}</div>
            {!!filesWritten.length && (
              <div className="text-xs">
                <div className="font-medium mb-1">Files written:</div>
                <ul className="list-disc pl-5">
                  {filesWritten.map((p, i) => (
                    <li key={i}>{p}</li>
                  ))}
                </ul>
              </div>
            )}
            {!!saveErrors.length && (
              <div className="text-xs text-amber-700">
                <div className="font-medium mb-1">Errors:</div>
                <ul className="list-disc pl-5">
                  {saveErrors.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
