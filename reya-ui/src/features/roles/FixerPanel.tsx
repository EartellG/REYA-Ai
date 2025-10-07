import React, { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

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
  files: FileBlob[]; // updated files after apply
};

export default function FixerPanel() {
  const [status, setStatus] = useState<string>("");
  const [filesJSON, setFilesJSON] = useState<string>(
    '[\n  {\n    "path": "reya-ui/src/components/Old.tsx",\n    "contents": "// TODO: fix issue\\nconsole.log(\\"debug\\")\\n"\n  }\n]'
  );
  const [issuesJSON, setIssuesJSON] = useState<string>("[]"); // or findings JSON
  const [strategy, setStrategy] = useState<"safe" | "aggressive">("safe");

  const [patches, setPatches] = useState<Patch[] | null>(null);
  const [suggestSummary, setSuggestSummary] = useState<string>("");
  const [applyResult, setApplyResult] = useState<ApplyResp | null>(null);

  // new: save results
  const [saveSummary, setSaveSummary] = useState<string>("");
  const [filesWritten, setFilesWritten] = useState<string[]>([]);
  const [saveErrors, setSaveErrors] = useState<string[]>([]);

  const [loadingSuggest, setLoadingSuggest] = useState(false);
  const [loadingApply, setLoadingApply] = useState(false);
  const [loadingSave, setLoadingSave] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Prefill: backend first, then localStorage fallback (from Reviewer)
  useEffect(() => {
    let cancelled = false;

    async function loadPrefill() {
      setStatus("Checking for Reviewer → Fixer handoff…");
      // 1) Try backend prefill
      try {
        const res = await fetch(`${API}/roles/fixer/prefill`);
        if (res.ok) {
          const data = await res.json();
          if (!cancelled && data?.prefill) {
            const p = data.prefill as {
              ticket?: any;
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
      } catch {
        // ignore; try localStorage
      }

      // 2) Fallback: localStorage
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
      } catch {
        // ignore
      }

      if (!cancelled) setStatus("No incoming handoff found.");
    }

    loadPrefill();
    return () => {
      cancelled = true;
    };
  }, []);

  function parseJSON<T>(label: string, src: string): T | null {
    try {
      return JSON.parse(src) as T;
    } catch (e: any) {
      setError(`${label} JSON parse error: ${e.message || e}`);
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
    setLoadingSuggest(true);
    setStatus("Suggesting patches…");

    const files = parseJSON<FileBlob[]>("Files", filesJSON);
    if (!files || !Array.isArray(files) || files.length === 0) {
      setLoadingSuggest(false);
      setStatus("Please provide at least one file.");
      return;
    }

    // Try as issues first; if array items look like legacy findings, backend accepts that too.
    const maybeIssues = parseJSON<any[]>("Issues/Findings", issuesJSON) || [];

    const body: SuggestReq = { files, strategy };

    // Heuristic: decide issues vs findings
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
    } catch (e: any) {
      setError(e.message || "Suggest failed");
      setStatus("Suggest failed");
    } finally {
      setLoadingSuggest(false);
    }
  }

  async function applyPatches() {
    if (!patches?.length) {
      setError("No patches to apply. Run Suggest first.");
      return;
    }
    setError(null);
    setLoadingApply(true);
    setStatus("Applying patches…");

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
      setFilesJSON(JSON.stringify(data.files, null, 2)); // reflect updates
      setStatus("Applied in memory ✅");
    } catch (e: any) {
      setError(e.message || "Apply failed");
      setStatus("Apply failed");
    } finally {
      setLoadingApply(false);
    }
  }

  async function applyAndSave() {
    if (!patches?.length) {
      setError("No patches to save. Run Suggest first.");
      return;
    }
    setError(null);
    setLoadingSave(true);
    setStatus("Applying + writing files…");
    setSaveSummary("");
    setFilesWritten([]);
    setSaveErrors([]);

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
      setFilesJSON(JSON.stringify(data.files, null, 2)); // reflect written contents
      setStatus("Applied & saved ✅");
    } catch (e: any) {
      setError(e.message || "Apply & Save failed");
      setStatus("Apply & Save failed");
    } finally {
      setLoadingSave(false);
    }
  }

  return (
    <Card className="ga-panel ga-outline">
      <CardContent className="space-y-4 p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">Fixer 🔧</h2>
        </div>

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
        <div className="grid gap-3 sm:grid-cols-3 items-end">
          <label className="grid gap-1">
            <span className="text-sm font-medium">Strategy</span>
            <Input
              value={strategy}
              onChange={(e) =>
                setStrategy(
                  (e.target.value === "aggressive" ? "aggressive" : "safe") as "safe" | "aggressive"
                )
              }
              list="fixer-strategies"
            />
            <datalist id="fixer-strategies">
              <option value="safe" />
              <option value="aggressive" />
            </datalist>
          </label>

          <div className="flex gap-2 sm:col-span-2">
            <Button className="ga-btn" disabled={loadingSuggest} onClick={suggestPatches}>
              {loadingSuggest ? "Suggesting…" : "Suggest patches"}
            </Button>
            <Button variant="outline" disabled={loadingApply || !patches?.length} onClick={applyPatches}>
              {loadingApply ? "Applying…" : "Apply (in memory)"}
            </Button>
            <Button
              variant="secondary"
              disabled={loadingSave || !patches?.length}
              onClick={applyAndSave}
              title="Apply then write files to disk"
            >
              {loadingSave ? "Saving…" : "Apply & Save"}
            </Button>
          </div>
        </div>

        {/* Summary */}
        {suggestSummary && (
          <div className="text-sm bg-zinc-100 text-zinc-800 rounded p-2">{suggestSummary}</div>
        )}

        {/* Patches view */}
        {patches?.length ? (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Patches</h3>
            <div className="grid gap-3">
              {patches.map((p, i) => (
                <div key={i} className="border rounded overflow-hidden">
                  <div className="px-3 py-2 text-xs bg-zinc-100 text-zinc-700">{p.path}</div>
                  <pre className="p-3 text-xs overflow-auto">
                    <code>{p.diff}</code>
                  </pre>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {/* Result of apply (in memory) */}
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

        {/* Result of apply & save */}
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
