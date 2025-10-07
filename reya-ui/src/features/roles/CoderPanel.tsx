import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const API = "http://127.0.0.1:8000";

/** Types (mirror backend models) */
type TicketType = "Backend" | "Frontend" | "QA";
type PrefillTicket = {
  id: string;
  title: string;
  type?: TicketType;
  estimate?: number;
  acceptance_criteria?: string[];
  tags?: string[];
  summary?: string;
  context?: string;
  description?: string;
};
type PrefillPayload = {
  ticket: PrefillTicket;
  language?: string;   // kept for future
  framework?: string;  // kept for future
  target_dir?: string; // kept for future
};

type CodeFile = { path: string; contents: string };

type GenAndSaveResp = {
  ok: boolean;
  summary: string;
  generated: number;
  written: number;
  skipped: number;
  errors: string[];
  files_written: string[];
};

export default function CoderPanel() {
  const [prefill, setPrefill] = useState<PrefillPayload | null>(null);
  const ticket = useMemo(() => prefill?.ticket || null, [prefill]);

  // UI state
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [overwrite, setOverwrite] = useState(false);

  // Last result (and files to send to Reviewer)
  const [saveResult, setSaveResult] = useState<GenAndSaveResp | null>(null);
  const [generatedFiles, setGeneratedFiles] = useState<CodeFile[] | null>(null);

  // Manual mode (if no handoff exists)
  const [manualId, setManualId] = useState("TCK-001");
  const [manualTitle, setManualTitle] = useState("Implement chat composer");
  const [manualDesc, setManualDesc] = useState("Add chat input & streaming");

  /** Load prefill from backend then localStorage */
  useEffect(() => {
    let cancelled = false;

    async function loadPrefill() {
      setStatus("Checking for Ticketizer handoff…");

      // 1) Backend one-shot
      try {
        const r = await fetch(`${API}/roles/coder/prefill`);
        if (r.ok) {
          const data = await r.json();
          if (!cancelled && data?.prefill?.ticket) {
            setPrefill(data.prefill);
            setStatus("Loaded handoff from backend ✅");
            return;
          }
        }
      } catch {/* ignore */}

      // 2) LocalStorage fallback
      try {
        const raw = localStorage.getItem("coder:prefill");
        if (raw) {
          const parsed: PrefillPayload = JSON.parse(raw);
          if (!cancelled && parsed?.ticket) {
            setPrefill(parsed);
            setStatus("Loaded handoff from localStorage ✅");
            localStorage.removeItem("coder:prefill");
            return;
          }
        }
      } catch {/* ignore */}

      if (!cancelled) setStatus("No incoming handoff found.");
    }

    loadPrefill();
    return () => { cancelled = true; };
  }, []);

  /** Generate + save in one call */
  async function generateAndSave() {
    if (!ticket) {
      setError("No ticket loaded. Use Ticketizer → Send to Coder or enter one manually.");
      return;
    }
    setError(null);
    setSaveResult(null);
    setGeneratedFiles(null);
    setLoading(true);
    setStatus("Generating and saving…");

    // Tech stack is chosen server-side in this prototype; keep “fullstack” for now.
    const body = {
      tech_stack: "fullstack",
      ticket: {
        id: ticket.id,
        title: ticket.title,
        description: ticket.description || "",
        files: [],
        acceptance: ticket.acceptance_criteria || [],
        tags: ticket.tags || [],
      },
      guidance: null,
      overwrite,
    };

    try {
      const res = await fetch(`${API}/roles/coder/generate_and_save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data: GenAndSaveResp = await res.json();
      if (!res.ok) throw new Error(data?.summary || "Generation failed");

      // For handoff to Reviewer, we also want the actual file contents (not just paths).
      // Since generate_and_save only returns paths, we also hit /roles/coder/generate (in-memory) to fetch contents.
      // This keeps disk writes single-pass but still lets Reviewer see exact content.
      const regen = await fetch(`${API}/roles/coder/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tech_stack: "fullstack",
          ticket: body.ticket,
          guidance: null,
        }),
      });
      const regenJson = await regen.json();
      const files: CodeFile[] = regenJson?.files || [];

      setGeneratedFiles(files);
      setSaveResult(data);
      setStatus(data.ok ? "Generated & saved ✅" : data.summary || "Finished with issues");
    } catch (e: any) {
      setError(e.message || "Generation failed");
      setStatus("Generation failed");
    } finally {
      setLoading(false);
    }
  }

  /** Send to Reviewer (localStorage handoff) */
  function sendToReviewer() {
    if (!ticket) {
      setError("No ticket loaded.");
      return;
    }
    if (!generatedFiles?.length) {
      setError("Nothing to send: generate first.");
      return;
    }
    const payload = {
      source: "coder",
      ticket,
      files: generatedFiles, // [{ path, contents }]
      notes: saveResult?.summary || "Generated by Coder",
    };
    localStorage.setItem("reviewer:prefill", JSON.stringify(payload));
    window.location.hash = "#/roles?tab=reviewer";
  }

  /** Manual ticket adoption (when no handoff) */
  function adoptManualAsTicket() {
    const t: PrefillTicket = {
      id: manualId,
      title: manualTitle,
      description: manualDesc,
      type: "Frontend",
      acceptance_criteria: [],
      tags: [],
    };
    setPrefill({ ticket: t });
    setStatus("Manual ticket loaded into Coder ✅");
  }

  return (
    <Card className="ga-panel ga-outline">
      <CardContent className="space-y-4 p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">Coder 👩‍💻</h2>
        </div>

        {status && <div className="text-sm ga-subtle">{status}</div>}

        {ticket ? (
          <>
            {/* Ticket summary */}
            <div className="border rounded p-3 bg-white text-black">
              <div className="text-xs uppercase opacity-70">{ticket.type || "Ticket"}</div>
              <div className="font-semibold">{ticket.title}</div>
              <div className="text-xs opacity-70">
                ID: {ticket.id}
                {typeof ticket.estimate === "number" ? ` • Estimate: ${ticket.estimate}` : ""}
              </div>

              {ticket.tags?.length ? (
                <div className="text-xs mt-1">Tags: {ticket.tags.join(", ")}</div>
              ) : null}

              {ticket.summary && (
                <div className="mt-2 text-sm whitespace-pre-wrap">
                  <span className="font-medium">Summary: </span>
                  {ticket.summary}
                </div>
              )}

              {ticket.context && (
                <div className="mt-2 text-sm whitespace-pre-wrap">
                  <span className="font-medium">Context: </span>
                  {ticket.context}
                </div>
              )}

              {ticket.description && (
                <div className="mt-2 text-sm whitespace-pre-wrap">
                  <span className="font-medium">Description: </span>
                  {ticket.description}
                </div>
              )}

              {!!ticket.acceptance_criteria?.length && (
                <div className="mt-3">
                  <div className="text-sm font-medium">Acceptance Criteria</div>
                  <ul className="list-disc pl-6 text-sm">
                    {ticket.acceptance_criteria.map((ac, i) => (
                      <li key={i}>{ac}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Options */}
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={overwrite}
                  onChange={(e) => setOverwrite(e.target.checked)}
                />
                Overwrite existing files
              </label>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap gap-2">
              <Button className="ga-btn" disabled={loading} onClick={generateAndSave}>
                {loading ? "Generating…" : "Generate & Save"}
              </Button>
              <Button variant="outline" onClick={sendToReviewer} disabled={!generatedFiles?.length}>
                Send to Reviewer
              </Button>
              {error && <div className="text-red-600 text-sm self-center">{error}</div>}
            </div>

            {/* Results */}
            {saveResult && (
              <div className="space-y-2">
                <div className="text-sm">{saveResult.summary}</div>
                {!!saveResult.files_written?.length && (
                  <div className="text-xs">
                    <div className="font-medium mb-1">Files written:</div>
                    <ul className="list-disc pl-5">
                      {saveResult.files_written.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {!!saveResult.errors?.length && (
                  <div className="text-xs text-amber-700">
                    <div className="font-medium mb-1">Warnings/Errors:</div>
                    <ul className="list-disc pl-5">
                      {saveResult.errors.map((e, i) => (
                        <li key={i}>{e}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Show generated contents for quick review */}
                {generatedFiles?.length ? (
                  <div className="mt-2 grid gap-3">
                    {generatedFiles.map((f, i) => (
                      <div key={i} className="border rounded">
                        <div className="px-3 py-2 text-xs bg-zinc-100 text-zinc-700">{f.path}</div>
                        <pre className="p-3 text-sm overflow-auto">
                          <code>{f.contents}</code>
                        </pre>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            )}
          </>
        ) : (
          <>
            {/* Manual ticket entry */}
            <p className="text-sm ga-subtle">
              No ticket loaded. Use <b>Ticketizer → Send to Coder</b>, or enter one manually:
            </p>

            <div className="grid gap-2 sm:grid-cols-3">
              <Input
                placeholder="Ticket ID"
                value={manualId}
                onChange={(e) => setManualId(e.target.value)}
              />
              <Input
                placeholder="Title"
                value={manualTitle}
                onChange={(e) => setManualTitle(e.target.value)}
              />
            </div>
            <Textarea
              placeholder="Description"
              value={manualDesc}
              onChange={(e) => setManualDesc(e.target.value)}
            />

            <div className="flex gap-2">
              <Button className="ga-btn" onClick={adoptManualAsTicket}>
                Load this ticket
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
