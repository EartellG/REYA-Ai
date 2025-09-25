import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const API = "http://127.0.0.1:8000";

export default function MonetizerPanel() {
  const [idea, setIdea] = useState("");
  const [audience, setAudience] = useState("Indie devs");
  const [features, setFeatures] = useState("chat,tutor,projects");
  const [plan, setPlan] = useState<any>(null);
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
        <h2 className="font-semibold">Monetizer 💰</h2>
        <p className="text-sm ga-subtle">
          <b>How to use:</b> Provide the idea + audience (and optional feature list) → get pricing tiers and monetization options.
        </p>

        <Input placeholder="App idea" value={idea} onChange={(e)=>setIdea(e.target.value)} />
        <Input placeholder="Audience" value={audience} onChange={(e)=>setAudience(e.target.value)} />
        <Textarea placeholder="Comma-separated features (optional)" value={features} onChange={(e)=>setFeatures(e.target.value)} />

        <Button
          className="ga-btn"
          disabled={loading}
          onClick={async ()=>{
            setLoading(true);
            try {
              const data = await call("/roles/monetizer/plan", {
                app_idea: idea,
                audience,
                features: features.split(",").map(s=>s.trim()).filter(Boolean),
              });
              setPlan(data);
            } finally { setLoading(false); }
          }}
        >
          {loading ? "Planning…" : "Plan pricing"}
        </Button>

        {plan && (
          <pre className="text-xs whitespace-pre-wrap mt-3">{JSON.stringify(plan, null, 2)}</pre>
        )}
      </CardContent>
    </Card>
  );
}
