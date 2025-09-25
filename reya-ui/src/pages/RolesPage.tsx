// src/pages/RolesPage.tsx
import { useState } from "react";
import TicketizerPanel from "@/features/roles/TicketizerPanel";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import CoderPanel from "@/features/roles/CoderPanel";
import ReviewerPanel from "@/features/roles/ReviewerPanel";
import FixerPanel from "@/features/roles/FixerPanel";
import MonetizerPanel from "@/features/roles/MonetizerPanel";

const API = "http://127.0.0.1:8000";

type FilePatch = { path: string; contents: string; };
type Finding = { path: string; notes: string[]; };

export default function RolesPage() {
  const [idea, setIdea] = useState("");
  const [audience, setAudience] = useState("Indie devs");
  const [ticketId, setTicketId] = useState("TCK-001");
  const [ticketTitle, setTicketTitle] = useState("Implement chat composer");
  const [ticketDesc, setTicketDesc] = useState("Add chat input & send logic with streaming");
  const [result, setResult] = useState<any>(null);
  const [files, setFiles] = useState<FilePatch[]>([
    { path: "reya-ui/src/components/Old.tsx", contents: "// TODO: fix issue\nconsole.log('debug')" }
  ]);
  const [findings, setFindings] = useState<Finding[]>([]);

  async function call(path: string, body: any) {
    const res = await fetch(`${API}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.detail || "request failed");
    return data;
  }

  return (
    <div className="container mx-auto max-w-5xl space-y-6">
      <h1 className="text-2xl font-bold">REYA Roles</h1>

      {/* Architect + Ticketizer (existing) */}
      <Card className="ga-panel ga-outline">
        <CardContent className="p-4">
          <h2 className="font-semibold mb-2">Ticketizer 🎟️</h2>
          <TicketizerPanel />
        </CardContent>
      </Card>

      {/* Monetizer */}
      <Card className="ga-panel ga-outline">
        <CardContent className="space-y-3 p-4">
          <h2 className="font-semibold">Monetizer 💰</h2>
          <MonetizerPanel />
          <Input placeholder="App idea" value={idea} onChange={(e)=>setIdea(e.target.value)} />
          <Input placeholder="Audience" value={audience} onChange={(e)=>setAudience(e.target.value)} />
          <Button
            className="ga-btn"
            onClick={async ()=>{
              const data = await call("/roles/monetizer/plan", { app_idea: idea, audience, features: [] });
              setResult({ role: "Monetizer", data });
            }}
          >Plan pricing</Button>
        </CardContent>
      </Card>

      {/* Coder */}
      <Card className="ga-panel ga-outline">
        <CardContent className="space-y-3 p-4">
          <h2 className="font-semibold">Coder 👩‍💻</h2>
          <div className="grid gap-2 sm:grid-cols-3">
            <CoderPanel />
            <Input placeholder="Ticket ID" value={ticketId} onChange={(e)=>setTicketId(e.target.value)} />
            <Input placeholder="Title" value={ticketTitle} onChange={(e)=>setTicketTitle(e.target.value)} />
          </div>
          <Textarea placeholder="Description" value={ticketDesc} onChange={(e)=>setTicketDesc(e.target.value)} />
          <Button
            className="ga-btn"
            onClick={async ()=>{
              const data = await call("/roles/coder/generate", {
                tech_stack: "fullstack",
                guidance: null,
                ticket: {
                  id: ticketId,
                  title: ticketTitle,
                  description: ticketDesc,
                  files: [],
                  acceptance: [],
                },
              });
              setResult({ role: "Coder", data });
            }}
          >Generate files</Button>
        </CardContent>
      </Card>

      {/* Reviewer */}
      <Card className="ga-panel ga-outline">
        <CardContent className="space-y-3 p-4">
          <h2 className="font-semibold">Reviewer 🔍</h2>
          <ReviewerPanel />
          <Textarea
            value={files[0].contents}
            onChange={(e)=>setFiles([{ ...files[0], contents: e.target.value }])}
            className="min-h-28"
          />
          <Button
            className="ga-btn"
            onClick={async ()=>{
              const data = await call("/roles/reviewer/review", { files });
              setFindings(data.findings || []);
              setResult({ role: "Reviewer", data });
            }}
          >Run review</Button>
        </CardContent>
      </Card>

      {/* Fixer */}
      <Card className="ga-panel ga-outline">
        <CardContent className="space-y-3 p-4">
          <h2 className="font-semibold">Fixer 🔧</h2>
          <FixerPanel /> 
          <Button
            className="ga-btn"
            onClick={async ()=>{
              const data = await call("/roles/fixer/suggest_patches", {
                files: files.map(f => f.path),
                findings,
              });
              setResult({ role: "Fixer", data });
            }}
          >Suggest patches</Button>
        </CardContent>
      </Card>

      {/* Output */}
      {result && (
        <Card className="ga-panel ga-outline">
          <CardContent className="p-4 overflow-auto">
            <div className="text-sm opacity-70 mb-2">Last result — {result.role}</div>
            <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(result.data, null, 2)}</pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
