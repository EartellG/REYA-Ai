import React, { useState } from "react";

interface SpecInput {
  title: string;
  goal: string;
  background?: string;
  constraints?: string;
  non_goals?: string;
  include_qa: boolean;
  estimate_units: "pts" | "hrs";
}

interface UserStory { role: string; need: string; why: string }
interface Ticket { id: string; title: string; type: "Backend"|"Frontend"|"QA"; estimate: number; acceptance_criteria: string[]; tags: string[] }
interface TicketizeResponse { epic: string; user_stories: UserStory[]; tickets: Ticket[] }

export default function TicketizerPanel() {
  const [form, setForm] = useState<SpecInput>({
    title: "Settings tab wiring",
    goal: "Wire four toggles with persistence and backend sync",
    background: "Current toggles exist visually but are not persisted or sent to backend.",
    constraints: "No breaking changes; SSR-safe; debounce writes.",
    non_goals: "Redesign visuals.",
    include_qa: true,
    estimate_units: "pts",
  });
  const [result, setResult] = useState<TicketizeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch("/roles/pm/ticketize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(await res.text());
      const data: TicketizeResponse = await res.json();
      setResult(data);
    } catch (e: any) {
      setError(e.message || "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const toMarkdown = (r: TicketizeResponse) => {
    const lines: string[] = [];
    lines.push(`# Epic\n${r.epic}\n`);
    lines.push(`## User Stories`);
    r.user_stories.forEach((s, i) => lines.push(`- As a **${s.role}**, I need **${s.need}**, so that **${s.why}**.`));
    lines.push(`\n## Tickets`);
    r.tickets.forEach(t => {
      lines.push(`- [${t.type}] **${t.title}** — _${t.estimate} ${form.estimate_units}_`);
      t.acceptance_criteria.forEach(ac => lines.push(`  - [ ] ${ac}`));
    });
    return lines.join("\n");
  };

  const copyMarkdown = async () => {
    if (!result) return;
    const md = toMarkdown(result);
    await navigator.clipboard.writeText(md);
    alert("Copied PRD/Tickets to clipboard as Markdown.");
  };

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-semibold">PM / Ticketizer</h2>
      <div className="grid gap-2">
        {(["title","goal","background","constraints","non_goals"] as const).map((k) => (
          <label key={k} className="grid gap-1">
            <span className="text-sm font-medium capitalize">{k}</span>
            <textarea
              className="border rounded p-2 min-h-[48px]"
              value={(form as any)[k] || ""}
              onChange={(e) => setForm({ ...form, [k]: e.target.value })}
            />
          </label>
        ))}
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.include_qa}
                   onChange={(e)=>setForm({ ...form, include_qa: e.target.checked })} />
            <span>Include QA ticket</span>
          </label>
          <label className="flex items-center gap-2">
            <span>Estimates in</span>
            <select value={form.estimate_units} onChange={(e)=>setForm({ ...form, estimate_units: e.target.value as any })} className="border rounded p-1">
              <option value="pts">story points</option>
              <option value="hrs">hours</option>
            </select>
          </label>
        </div>
        <button onClick={submit} disabled={loading} className="px-3 py-2 rounded bg-black text-white">
          {loading ? "Generating…" : "Generate tickets"}
        </button>
        {error && <div className="text-red-600 text-sm">{error}</div>}
      </div>

      {result && (
        <div className="space-y-3">
          <h3 className="text-lg font-semibold">Epic</h3>
          <div className="p-3 border rounded bg-white">{result.epic}</div>

          <h3 className="text-lg font-semibold">User Stories</h3>
          <ul className="list-disc pl-6">
            {result.user_stories.map((s,i)=> (
              <li key={i}>As a <b>{s.role}</b>, I need <b>{s.need}</b>, so that <b>{s.why}</b>.</li>
            ))}
          </ul>

          <h3 className="text-lg font-semibold">Tickets</h3>
          <div className="grid md:grid-cols-2 gap-3">
            {result.tickets.map(t => (
              <div key={t.id} className="border rounded p-3">
                <div className="text-sm uppercase opacity-70">{t.type}</div>
                <div className="font-medium">{t.title}</div>
                <div className="text-xs opacity-70">Estimate: {t.estimate} {form.estimate_units}</div>
                <ul className="list-disc pl-6 mt-2 text-sm">
                  {t.acceptance_criteria.map((ac, i) => (<li key={i}>{ac}</li>))}
                </ul>
                {t.tags?.length ? (
                  <div className="mt-2 text-xs">Tags: {t.tags.join(", ")}</div>
                ) : null}
              </div>
            ))}
          </div>

          <div className="flex gap-2">
            <button onClick={copyMarkdown} className="px-3 py-2 rounded border">Copy Markdown</button>
          </div>
        </div>
      )}
    </div>
  );
}