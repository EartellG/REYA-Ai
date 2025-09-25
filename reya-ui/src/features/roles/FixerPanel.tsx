import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

const API = "http://127.0.0.1:8000";

export default function FixerPanel() {
  const [filesCsv, setFilesCsv] = useState("reya-ui/src/components/Old.tsx");
  const [findingsJson, setFindingsJson] = useState(`[{"path":"reya-ui/src/components/Old.tsx","notes":["Avoid console.log in production","Missing prop types"]}]`);
  const [patches, setPatches] = useState<any>(null);
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
        <h2 className="font-semibold">Fixer 🔧</h2>
        <p className="text-sm ga-subtle">
          <b>How to use:</b> Pass Reviewer’s findings + file paths → Fixer proposes patches/PR bundle.
        </p>

        <Input value={filesCsv} onChange={(e)=>setFilesCsv(e.target.value)} placeholder="Files (comma-separated)" />
        <Textarea className="min-h-24" value={findingsJson} onChange={(e)=>setFindingsJson(e.target.value)} placeholder='Findings JSON from Reviewer' />

        <Button
          className="ga-btn"
          disabled={loading}
          onClick={async ()=>{
            setLoading(true);
            try {
              const files = filesCsv.split(",").map(s=>s.trim()).filter(Boolean);
              const findings = JSON.parse(findingsJson || "[]");
              const data = await call("/roles/fixer/suggest_patches", { files, findings });
              setPatches(data);
            } finally { setLoading(false); }
          }}
        >
          {loading ? "Suggesting…" : "Suggest patches"}
        </Button>

        {patches && (
          <pre className="text-xs whitespace-pre-wrap mt-3">{JSON.stringify(patches, null, 2)}</pre>
        )}
      </CardContent>
    </Card>
  );
}
