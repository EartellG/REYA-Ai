// src/features/wireframes/WireframesPanel.tsx
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
      <CardContent className="space-y-4 p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">Wireframes ✏️</h2>
        </div>

        <p className="text-sm ga-subtle">
          <b>How to use:</b> Upload a sketch to store it with your project, or enter a prompt to auto-generate a wireframe.
        </p>

        {/* Upload (stub for now) */}
        <div className="flex items-center gap-2">
          <Input
            type="file"
            accept="image/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <Button
             className="ga-btn"
  variant="secondary"
  disabled={!file || loading}
  onClick={async () => {
    if (!file) {
      alert("Pick an image first.");
      return;
    }
    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("project_id", "default"); // or pass your current project id

      const res = await fetch(`${API}/wireframes/upload`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Upload failed.");
      // Show uploaded image immediately
      setImageUrl(`${API}${data.url}`);
    } catch (e: any) {
      console.error(e);
      alert(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }}
>
  {loading ? "Uploading…" : "Save sketch"}
          </Button>
        </div>
        {file && (
          <div className="text-xs ga-subtle">
            Selected: <span className="opacity-90">{file.name}</span>
          </div>
        )}

        {/* Prompt → Generate */}
        <div className="space-y-2">
          <Textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the screens/components you want…"
          />
          <Button
            className="ga-btn"
            disabled={loading || !prompt.trim()}
            onClick={async () => {
              setLoading(true);
              try {
                const res = await fetch(`${API}/wireframes/generate`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    prompt: prompt.trim(),
                    style: "glass-aurora-purple",
                  }),
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data?.detail || "Failed to generate wireframe.");
                // data.url is like /static/wireframes/xxxx.svg — prefix with API host for the browser
                setImageUrl(`${API}${data.url}`);
              } catch (e: any) {
                console.error(e);
                alert(e?.message || String(e));
              } finally {
                setLoading(false);
              }
            }}
          >
            {loading ? "Generating…" : "Generate wireframe"}
          </Button>
        </div>

        {/* Preview */}
        <div className="mt-2">
          {imageUrl ? (
            <img
              src={imageUrl}
              alt="Wireframe"
              className="rounded-xl border border-white/10 max-w-full"
            />
          ) : (
            <div className="ga-card p-6 text-sm ga-subtle rounded-xl text-center">
              No wireframe yet — generate one or upload a sketch.
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
