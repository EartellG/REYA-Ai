import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

const API = "http://127.0.0.1:8000";

type FilePatch = { path: string; contents: string; };

export default function ReviewerPanel() {
  const [path, setPath] = useState("reya-ui/src/components/Old.tsx");
  const [contents, setContents] = useState("// TODO: fix issue\nconsole.log('debug')");
  const [findings, setFindings] = useState<any[]>([]);
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
        <h2 className="font-semibold">Reviewer 🔍</h2>
        <p className="text-sm ga-subtle">
          <b>How to use:</b> Paste code for one file → Reviewer flags bugs, style issues, and risks.
        </p>

        <Input value={path} onChange={(e)=>setPath(e.target.value)} placeholder="File path" />
        <Textarea className="min-h-32" value={contents} onChange={(e)=>setContents(e.target.value)} />

        <Button
          className="ga-btn"
          disabled={loading}
          onClick={async ()=>{
            setLoading(true);
            try {
              const payload: FilePatch[] = [{ path, contents }];
              const data = await call("/roles/reviewer/review", { files: payload });
              setFindings(data.findings || []);
            } finally { setLoading(false); }
          }}
        >
          {loading ? "Reviewing…" : "Run review"}
        </Button>

        {!!findings.length && (
          <pre className="text-xs whitespace-pre-wrap mt-3">{JSON.stringify(findings, null, 2)}</pre>
        )}
      </CardContent>
    </Card>
  );
}
