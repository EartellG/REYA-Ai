import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const API = "http://127.0.0.1:8000";

export default function WireframesPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [prompt, setPrompt] = useState("Homepage + Chat + Tutor layout for REYA");
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  return (
    <Card className="ga-panel ga-outline">
      <CardContent className="space-y-3 p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">Wireframes ✏️</h2>
        </div>
        <p className="text-sm ga-subtle">
          <b>How to use:</b> Upload a sketch to keep it with the project, or enter a prompt to auto-generate a wireframe image.
        </p>

        {/* Upload */}
        <div className="flex items-center gap-2">
          <Input type="file" accept="image/*" onChange={(e)=>setFile(e.target.files?.[0] || null)} />
          <Button
              className="ga-btn"
        disabled={loading}
        onClick={async ()=>{
        setLoading(true);
        try {
      // Placeholder: hook this to FastAPI later
      console.log("Would call:", `${API}/wireframes/generate`, { prompt });
      setImageUrl(null);
      alert("Stub: hook /wireframes/generate backend to return an image URL.");
    } finally { setLoading(false); }
  }}
>
  {loading ? "Generating…" : "Generate wireframe"}
          </Button>
        </div>

        {/* Generate */}
        <Textarea value={prompt} onChange={(e)=>setPrompt(e.target.value)} />
        <Button
          className="ga-btn"
          disabled={loading}
          onClick={async ()=>{
            setLoading(true);
            try {
              // Placeholder generation call:
              // const res = await fetch(`${API}/wireframes/generate`, { method:"POST", headers:{ "Content-Type":"application/json" }, body: JSON.stringify({ prompt }) });
              // const data = await res.json();
              // setImageUrl(data.url);
              // For now, just clear preview:
              setImageUrl(null);
              alert("Stub: hook /wireframes/generate backend to return an image URL.");
            } finally { setLoading(false); }
          }}
        >
          {loading ? "Generating…" : "Generate wireframe"}
        </Button>

        {imageUrl && (
          <div className="mt-2">
            <img src={imageUrl} alt="Wireframe" className="rounded-xl border border-white/10" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
