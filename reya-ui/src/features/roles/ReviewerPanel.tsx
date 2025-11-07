// src/features/roles/ReviewerPanel.tsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";

declare const __API__: string | undefined;
const API = typeof __API__ !== "undefined" ? __API__! : "http://127.0.0.1:8000";

type FileBlob = { path: string; contents: string };
type Finding = { path: string; notes: string[] };
type ReviewReply = { summary: string; findings: Finding[] };

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
type LintReply = { summary: string; issues: ReviewIssue[] };

type FileDiff = { path: string; diff: string };
type DiffReply = { diffs: FileDiff[] };

type FileStatus = "clean" | "modified" | "sent";

function Badge({ className, children }: { className?: string; children: React.ReactNode }) {
  return <span className={`px-2 py-0.5 text-xs rounded-full border ${className}`}>{children}</span>;
}

function SevBadge({ sev }: { sev?: "error" | "warning" | "info" }) {
  const label = sev ?? "info";
  const map =
    label === "error"
      ? "bg-red-500/15 text-red-800 border-red-500/40"
      : label === "warning"
      ? "bg-amber-500/15 text-amber-800 border-amber-500/40"
      : "bg-sky-500/15 text-sky-800 border-sky-500/40";
  return <Badge className={map}>{label}</Badge>;
}

function LintHealthBadge({ apiBase }: { apiBase: string }) {
  const [label, setLabel] = useState<string>("Lint: …");
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const r = await fetch(`${apiBase}/roles/reviewer/lint/health`);
        const data = await r.json();
        if (!alive) return;
        const hasEslint = !!data?.tools?.eslint || !!data?.tools?.npx;
        const hasRuff = !!data?.tools?.ruff || !!data?.tools?.python;
        setOk(hasEslint || hasRuff);
        setLabel(`Lint: ${hasEslint ? "ESLint" : "—"} | ${hasRuff ? "Ruff" : "—"}`);
      } catch {
        if (alive) {
          setOk(false);
          setLabel("Lint: unknown");
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, [apiBase]);
  const cls =
    ok === null
      ? "bg-zinc-500/10 text-zinc-700 border-zinc-500/30"
      : ok
      ? "bg-emerald-500/15 text-emerald-800 border-emerald-500/40"
      : "bg-rose-500/15 text-rose-800 border-rose-500/40";
  return <Badge className={cls}>{label}</Badge>;
}

export default function ReviewerPanel() {
  const { toast } = useToast();

  // input state
  const [path, setPath] = useState("reya-ui/src/components/Old.tsx");
  const [contents, setContents] = useState("// TODO: fix issue\nconsole.log('debug')");
  const [filesJSON, setFilesJSON] = useState<string>("");

  // status
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // review + lint
  const [findings, setFindings] = useState<Finding[]>([]);
  const [summary, setSummary] = useState<string>("");

  const [lintIssues, setLintIssues] = useState<ReviewIssue[]>([]);
  const [lintStatus, setLintStatus] = useState<string>("");

  const [loadingReview, setLoadingReview] = useState(false);
  const [loadingLint, setLoadingLint] = useState(false);
  const [loadingDiff, setLoadingDiff] = useState(false);
  const [clearing, setClearing] = useState(false);

  // filters
  const [severityFilter, setSeverityFilter] = useState<"all" | "error" | "warning" | "info">("all");
  const [sourceFilter, setSourceFilter] = useState<"all" | "eslint" | "ruff" | "inline">("all");

  // diffs + file badges (v3.4)
  const [diffs, setDiffs] = useState<FileDiff[] | null>(null);
  const [fileStatus, setFileStatus] = useState<Record<string, FileStatus>>({});

  const lintAbortRef = useRef<AbortController | null>(null);

  // Prefill (server, then local)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setStatus("Checking for Coder → Reviewer handoff…");
      try {
        const r = await fetch(`${API}/roles/reviewer/prefill`);
        if (r.ok) {
          const data = await r.json();
          if (!cancelled && data?.prefill?.files?.length) {
            const files = data.prefill.files as FileBlob[];
            setFilesJSON(JSON.stringify(files, null, 2));
            setPath(files[0].path);
            setContents(files[0].contents);
            setStatus("Loaded Coder → Reviewer handoff (server) ✅");
            return;
          }
        }
      } catch {}
      try {
        const raw = localStorage.getItem("reviewer:prefill");
        if (raw) {
          const parsed = JSON.parse(raw);
          const files: FileBlob[] = parsed?.files || [];
          if (!cancelled && files.length) {
            setFilesJSON(JSON.stringify(files, null, 2));
            setPath(files[0].path);
            setContents(files[0].contents);
            setStatus("Loaded Coder → Reviewer handoff (local) ✅");
            return;
          }
        }
      } catch {}
      if (!cancelled) setStatus("No incoming handoff detected.");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // In-page handoff
  useEffect(() => {
    const onHandoff = (e: Event) => {
      const d = (e as CustomEvent).detail;
      if (!d || d.target !== "reviewer") return;
      const files: FileBlob[] = d.payload?.files || [];
      if (files.length) {
        setFilesJSON(JSON.stringify(files, null, 2));
        setPath(files[0].path);
        setContents(files[0].contents);
        setStatus("Loaded handoff (in-page) ✅");
        toast({ variant: "success", title: "Received from Coder", description: `${files.length} file(s)` });
      }
    };
    window.addEventListener("reya:handoff", onHandoff as EventListener);
    return () => window.removeEventListener("reya:handoff", onHandoff as EventListener);
  }, [toast]);

  function parseFiles(): FileBlob[] | null {
    if (filesJSON.trim()) {
      try {
        const arr = JSON.parse(filesJSON) as FileBlob[];
        if (!Array.isArray(arr) || !arr.length) {
          setError("Files JSON must be a non-empty array.");
          return null;
        }
        const ok = arr.every((f) => typeof f?.path === "string" && typeof f?.contents === "string");
        if (!ok) {
          setError("Each file must have { path: string, contents: string }.");
          return null;
        }
        return arr;
      } catch (e: any) {
        setError(`Files JSON parse error: ${e.message || e}`);
        return null;
      }
    }
    if (!path.trim()) {
      setError("Provide a file path or Files JSON.");
      return null;
    }
    return [{ path, contents }];
  }

  async function runReview() {
    setError(null);
    setLoadingReview(true);
    setFindings([]);
    setSummary("");
    setStatus("Reviewing…");
    const files = parseFiles();
    if (!files) {
      setLoadingReview(false);
      setStatus("Fix input errors and retry.");
      return;
    }
    try {
      const res = await fetch(`${API}/roles/reviewer/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ files }),
      });
      const data: ReviewReply = await res.json();
      if (!res.ok) throw new Error((data as any)?.detail || "request failed");
      setFindings(data.findings || []);
      setSummary(data.summary || "");
      setStatus("Review complete ✅");
      toast({ title: "Review complete", description: `${data.findings?.length ?? 0} finding(s)` });
    } catch (e: any) {
      setError(e.message || "Review failed");
      setStatus("Review failed");
      toast({ variant: "destructive", title: "Review failed", description: String(e?.message ?? e) });
    } finally {
      setLoadingReview(false);
    }
  }

  async function runLint() {
    setLintIssues([]);
    setLintStatus("Running lint…");
    setLoadingLint(true);
    lintAbortRef.current?.abort();
    lintAbortRef.current = new AbortController();
    const files = parseFiles();
    if (!files) {
      setLoadingLint(false);
      setLintStatus("Fix input errors and retry.");
      toast({ variant: "destructive", title: "Invalid input", description: "Fix inputs and retry." });
      return;
    }
    try {
      const res = await fetch(`${API}/roles/reviewer/lint`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: lintAbortRef.current.signal,
        body: JSON.stringify({ files }),
      });
      const data: LintReply | { detail?: string } = await res.json();
      if (!res.ok) throw new Error((data as any)?.detail || "lint failed");
      const issues = (data as LintReply).issues || [];
      setLintIssues(issues);
      setLintStatus((data as LintReply).summary || "Lint completed");
      toast({ title: "Lint complete", description: `${issues.length} issue(s) found` });
    } catch (e: any) {
      if (e?.name === "AbortError") {
        setLintStatus("Lint cancelled");
      } else {
        setLintStatus(e.message || "Lint failed");
        toast({ variant: "destructive", title: "Lint failed", description: String(e?.message ?? e) });
      }
    } finally {
      setLoadingLint(false);
    }
  }

  function cancelLint() {
    lintAbortRef.current?.abort();
  }

  async function previewDiff() {
    setLoadingDiff(true);
    setDiffs(null);
    setStatus("Generating diff preview…");
    const files = parseFiles();
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
      // update per-file status by diff content
      const next: Record<string, FileStatus> = { ...fileStatus };
      (data.diffs || []).forEach((d) => {
        const modified = !!(d.diff && d.diff.trim());
        next[d.path] = modified ? "modified" : "clean";
      });
      setFileStatus(next);
      setStatus("Diff preview ready ✅");
      toast({ title: "Diff ready", description: `${data.diffs?.length ?? 0} file(s)` });
    } catch (e: any) {
      setStatus("Diff failed");
      toast({ variant: "destructive", title: "Diff failed", description: String(e?.message ?? e) });
    } finally {
      setLoadingDiff(false);
    }
  }

  function navTo(tab: "roles") {
    window.dispatchEvent(new CustomEvent("reya:navigate", { detail: { tab } }));
  }

  async function sendToFixer() {
    const files = parseFiles();
    if (!files) {
      setError("Nothing to send: provide files first.");
      toast({ variant: "destructive", title: "Nothing to send", description: "Add files first." });
      return;
    }
    const payload = {
      files,
      issues: lintIssues.length ? lintIssues : undefined,
      findings: !lintIssues.length && findings.length ? findings : undefined,
      notes: (lintIssues.length ? lintStatus : summary) || "Findings from Reviewer",
    };
    localStorage.setItem("reviewer:prefill", JSON.stringify(payload));
    try {
      await fetch(`${API}/roles/fixer/prefill`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch {}
    // mark all files as 'sent'
    const next: Record<string, FileStatus> = { ...fileStatus };
    (files || []).forEach((f) => (next[f.path] = "sent"));
    setFileStatus(next);

    window.dispatchEvent(new CustomEvent("reya:handoff", { detail: { target: "fixer", payload } }));
    setStatus("Sent to Fixer ✅");
    toast({ variant: "success", title: "Handoff sent", description: "Reviewer → Fixer" });
    window.dispatchEvent(new CustomEvent("reya:roles-focus", { detail: { panel: "fixer" } }));
    navTo("roles");
  }

  async function clearServerPrefill() {
    try {
      setClearing(true);
      await fetch(`${API}/roles/reviewer/prefill`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      setStatus("Server prefill cleared.");
      toast({ title: "Cleared", description: "Server prefill buffer cleared." });
    } catch {
      setStatus("Failed to clear server prefill (network?).");
      toast({ variant: "destructive", title: "Clear failed", description: "Network or server error." });
    } finally {
      setClearing(false);
    }
  }

  const filteredIssues = useMemo(() => {
    return lintIssues.filter((it) => {
      const sevOk = severityFilter === "all" || it.severity === severityFilter;
      const srcOk = sourceFilter === "all" || it.source === sourceFilter;
      return sevOk && srcOk;
    });
  }, [lintIssues, severityFilter, sourceFilter]);

  const canSend = useMemo(() => {
    const haveFiles =
      (filesJSON.trim() &&
        (() => {
          try {
            return Array.isArray(JSON.parse(filesJSON));
          } catch {
            return false;
          }
        })()) ||
      !!path.trim();
    return haveFiles && (lintIssues.length > 0 || findings.length > 0 || !!summary);
  }, [filesJSON, path, lintIssues.length, findings.length, summary]);

  const statusBadge = (st?: FileStatus) => {
    switch (st) {
      case "modified":
        return <Badge className="bg-amber-500/15 text-amber-800 border-amber-500/40">modified</Badge>;
      case "sent":
        return <Badge className="bg-indigo-500/15 text-indigo-800 border-indigo-500/40">sent</Badge>;
      default:
        return <Badge className="bg-zinc-500/10 text-zinc-700 border-zinc-500/30">clean</Badge>;
    }
  };

  return (
    <Card className="ga-panel ga-outline">
      <CardContent className="space-y-3 p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">Reviewer</h2>
          <div className="flex items-center gap-2">
            <LintHealthBadge apiBase={API} />
            {loadingLint ? (
              <Button variant="destructive" size="sm" onClick={cancelLint}>Cancel lint</Button>
            ) : null}
            <Button variant="outline" size="sm" onClick={clearServerPrefill} disabled={clearing} title="Dev: wipe server handoff buffer">
              {clearing ? "Clearing…" : "Clear server prefill"}
            </Button>
          </div>
        </div>

        {status && <div className="text-sm ga-subtle">{status}</div>}
        {error && <div className="text-sm text-red-600">{error}</div>}

        {/* Files JSON */}
        <label className="grid gap-1">
          <span className="text-sm font-medium">Files (JSON) – optional</span>
          <Textarea
            className="min-h-32 font-mono text-sm"
            spellCheck={false}
            value={filesJSON}
            onChange={(e) => setFilesJSON(e.target.value)}
            placeholder='[{"path":"file.tsx","contents":"..."}]'
          />
        </label>
        <div className="text-xs ga-subtle">If JSON above is provided, it overrides the single-file inputs below.</div>

        {/* Single-file editor */}
        <div className="flex items-center gap-2">
          <Input value={path} onChange={(e) => setPath(e.target.value)} placeholder="File path" />
          <div>{statusBadge(fileStatus[path])}</div>
        </div>
        <Textarea
          className="min-h-40 font-mono text-sm"
          spellCheck={false}
          value={contents}
          onChange={(e) => setContents(e.target.value)}
          placeholder="// paste code here"
        />

        <div className="flex gap-2 flex-wrap">
          <Button className="ga-btn" disabled={loadingReview} onClick={runReview}>
            {loadingReview ? "Reviewing…" : "Run review"}
          </Button>
          <Button variant="outline" disabled={loadingLint} onClick={runLint}>
            {loadingLint ? "Linting…" : "Run lint (ESLint + Ruff)"}
          </Button>
          <Button variant="outline" disabled={loadingDiff} onClick={previewDiff}>
            {loadingDiff ? "Diffing…" : "Preview diff"}
          </Button>
          <Button variant="outline" disabled={!canSend} onClick={sendToFixer}>
            Send to Fixer
          </Button>
        </div>

        {/* Filters */}
        <div className="flex gap-2 items-end">
          <label className="grid text-sm">
            <span className="text-xs ga-subtle">Severity</span>
            <select
              className="border rounded px-2 py-1 text-sm"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value as any)}
            >
              <option value="all">All</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </label>
          <label className="grid text-sm">
            <span className="text-xs ga-subtle">Source</span>
            <select
              className="border rounded px-2 py-1 text-sm"
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value as any)}
            >
              <option value="all">All</option>
              <option value="eslint">ESLint</option>
              <option value="ruff">Ruff</option>
              <option value="inline">Inline</option>
            </select>
          </label>
        </div>

        {/* Static review summary */}
        {summary && <div className="text-sm bg-zinc-100 text-zinc-800 rounded p-2">{summary}</div>}

        {!!findings.length && (
          <div className="space-y-2">
            <h3 className="text-lg font-semibold">Findings</h3>
            <div className="grid gap-2">
              {findings.map((f, i) => (
                <div key={i} className="border rounded p-2">
                  <div className="text-xs font-mono bg-zinc-100 text-zinc-700 px-2 py-1 rounded flex items-center gap-2">
                    <span>{f.path}</span>
                    {statusBadge(fileStatus[f.path])}
                  </div>
                  <ul className="list-disc pl-6 text-sm mt-1">
                    {f.notes.map((n, j) => (
                      <li key={j}>{n}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Diff Preview */}
        {diffs?.length ? (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Diff Preview (Workspace vs Proposed)</h3>
            <div className="grid gap-3">
              {diffs.map((d, i) => (
                <div key={i} className="border rounded overflow-hidden">
                  <div className="px-3 py-2 text-xs bg-zinc-100 text-zinc-700 flex items-center gap-2">
                    <span>{d.path}</span>
                    {statusBadge(fileStatus[d.path])}
                  </div>
                  <pre className="p-3 text-xs overflow-auto">
                    <code>{d.diff || "No changes."}</code>
                  </pre>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {/* Lint issues */}
        {!!filteredIssues.length && (
          <div className="space-y-2">
            <h3 className="text-lg font-semibold">Lint Issues</h3>
            <div className="overflow-auto rounded border">
              <table className="w-full text-sm">
                <thead className="bg-zinc-100 text-zinc-700">
                  <tr>
                    <th className="text-left p-2">File</th>
                    <th className="text-left p-2">Line</th>
                    <th className="text-left p-2">Col</th>
                    <th className="text-left p-2">Severity</th>
                    <th className="text-left p-2">Rule</th>
                    <th className="text-left p-2">Message</th>
                    <th className="text-left p-2">Source</th>
                    <th className="text-left p-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredIssues.map((it, i) => (
                    <tr key={i} className="border-t">
                      <td className="p-2 font-mono">{it.file}</td>
                      <td className="p-2">{it.line ?? "-"}</td>
                      <td className="p-2">{it.col ?? "-"}</td>
                      <td className="p-2"><SevBadge sev={it.severity} /></td>
                      <td className="p-2 font-mono">{it.rule || "-"}</td>
                      <td className="p-2">{it.message}</td>
                      <td className="p-2">{it.source || "-"}</td>
                      <td className="p-2">{statusBadge(fileStatus[it.file || ""])}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {lintStatus && <div className="text-xs ga-subtle">{lintStatus}</div>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
