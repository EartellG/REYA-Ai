// src/features/roles/ReviewerPanel.tsx
import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";

const API = "http://127.0.0.1:8000";

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
  source?: "eslint" | "ruff";
};

export default function ReviewerPanel() {
  const { toast } = useToast();

  // quick single-file mode
  const [path, setPath] = useState("reya-ui/src/components/Old.tsx");
  const [contents, setContents] = useState("// TODO: fix issue\nconsole.log('debug')");

  // optional multi-file JSON
  const [filesJSON, setFilesJSON] = useState<string>("");

  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // Static review
  const [findings, setFindings] = useState<Finding[]>([]);
  const [summary, setSummary] = useState<string>("");

  // Lint results
  const [lintIssues, setLintIssues] = useState<ReviewIssue[]>([]);
  const [lintStatus, setLintStatus] = useState<string>("");

  const [loadingReview, setLoadingReview] = useState(false);
  const [loadingLint, setLoadingLint] = useState(false);
  const [clearing, setClearing] = useState(false);

  // Prefill from Coder (server, then localStorage)
  useEffect(() => {
    let cancelled = false;

    async function loadPrefill() {
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
      } catch { /* ignore */ }

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
      } catch { /* ignore */ }

      if (!cancelled) setStatus("No incoming handoff detected.");
    }

    loadPrefill();
    return () => { cancelled = true; };
  }, []);

  // In-page handoff from Coder
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
      toast({ variant: "destructive", title: "Invalid input", description: "Fix inputs and retry." });
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
        body: JSON.stringify({ files }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "lint failed");
      setLintIssues(data.issues || []);
      setLintStatus(data.summary || "Lint completed");
      toast({ title: "Lint complete", description: `${data.issues?.length ?? 0} issue(s) found` });
    } catch (e: any) {
      setLintStatus(e.message || "Lint failed");
      toast({ variant: "destructive", title: "Lint failed", description: String(e?.message ?? e) });
    } finally {
      setLoadingLint(false);
    }
  }

  function navTo(tab: "roles") {
    window.dispatchEvent(new CustomEvent("reya:navigate", { detail: { tab } }));
  }

  function sendToFixer() {
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

    window.dispatchEvent(new CustomEvent("reya:handoff", { detail: { target: "fixer", payload } }));
    setStatus("Sent to Fixer ✅");
    toast({ variant: "success", title: "Handoff sent", description: "Reviewer → Fixer" });

    window.dispatchEvent(new CustomEvent("reya:roles-focus", { detail: { panel: "fixer" } }));
    navTo("roles");
  }

  // --- Dev helper: clear server prefill buffer ---
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

  return (
    <Card className="ga-panel ga-outline">
      <CardContent className="space-y-3 p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">Reviewer</h2>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={clearServerPrefill} disabled={clearing} title="Dev: wipe server handoff buffer">
              {clearing ? "Clearing…" : "Clear server prefill"}
            </Button>
          </div>
        </div>

        {status && <div className="text-sm ga-subtle">{status}</div>}
        {error && <div className="text-sm text-red-600">{error}</div>}

        {/* Optional multi-file mode */}
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

        {/* Single-file quick editor */}
        <Input value={path} onChange={(e) => setPath(e.target.value)} placeholder="File path" />
        <Textarea
          className="min-h-40 font-mono text-sm"
          spellCheck={false}
          value={contents}
          onChange={(e) => setContents(e.target.value)}
          placeholder="// paste code here"
        />

        <div className="flex gap-2">
          <Button className="ga-btn" disabled={loadingReview} onClick={runReview}>
            {loadingReview ? "Reviewing…" : "Run review"}
          </Button>
          <Button variant="outline" disabled={loadingLint} onClick={runLint}>
            {loadingLint ? "Linting…" : "Run lint (ESLint + Ruff)"}
          </Button>
          <Button variant="outline" disabled={!canSend} onClick={sendToFixer}>
            Send to Fixer
          </Button>
        </div>

        {/* Static review summary */}
        {summary && <div className="text-sm bg-zinc-100 text-zinc-800 rounded p-2">{summary}</div>}

        {!!findings.length && (
          <div className="space-y-2">
            <h3 className="text-lg font-semibold">Findings</h3>
            <div className="grid gap-2">
              {findings.map((f, i) => (
                <div key={i} className="border rounded p-2">
                  <div className="text-xs font-mono bg-zinc-100 text-zinc-700 px-2 py-1 rounded">{f.path}</div>
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

        {/* Lint issues table */}
        {!!lintIssues.length && (
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
                  </tr>
                </thead>
                <tbody>
                  {lintIssues.map((it, i) => (
                    <tr key={i} className="border-t">
                      <td className="p-2 font-mono">{it.file}</td>
                      <td className="p-2">{it.line ?? "-"}</td>
                      <td className="p-2">{it.col ?? "-"}</td>
                      <td className="p-2">{it.severity}</td>
                      <td className="p-2 font-mono">{it.rule || "-"}</td>
                      <td className="p-2">{it.message}</td>
                      <td className="p-2">{it.source || "-"}</td>
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
