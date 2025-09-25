import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const API = "http://127.0.0.1:8000";

export default function CoderPanel() {
  const [ticketId, setTicketId] = useState("TCK-001");
  const [title, setTitle] = useState("Implement chat composer");
  const [desc, setDesc] = useState("Add chat input & send logic with streaming");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function call(path: string, body: any) {
    const res = await fetch(`${API}${path}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.detail || "request failed");
    return data;
  }

  return (
    <Card className="ga-panel ga-outline">
      <CardContent className="space-y-3 p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">Coder 👩‍💻</h2>
        </div>
        <p className="text-sm ga-subtle">
          <b>How to use:</b> Pick one ticket → Coder generates or updates files for that specific task.
        </p>

        <div className="grid gap-2 sm:grid-cols-3">
          <Input placeholder="Ticket ID" value={ticketId} onChange={(e)=>setTicketId(e.target.value)} />
          <Input placeholder="Title" value={title} onChange={(e)=>setTitle(e.target.value)} />
        </div>
        <Textarea placeholder="Description" value={desc} onChange={(e)=>setDesc(e.target.value)} />

        <Button
          className="ga-btn"
          disabled={loading}
          onClick={async ()=>{
            setLoading(true);
            try {
              const data = await call("/roles/coder/generate", {
                tech_stack: "fullstack",
                guidance: null,
                ticket: {
                  id: ticketId,
                  title,
                  description: desc,
                  files: [],
                  acceptance: [],
                },
              });
              setResult(data);
            } finally { setLoading(false); }
          }}
        >
          {loading ? "Generating…" : "Generate files"}
        </Button>

        {result && (
          <pre className="text-xs whitespace-pre-wrap mt-3">{JSON.stringify(result, null, 2)}</pre>
        )}
      </CardContent>
    </Card>
  );
}
