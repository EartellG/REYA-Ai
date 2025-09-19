import { useState } from "react";

export default function PronounceButton({
  text,
  voice, // optional: override per item (e.g., "ja-JP-NanamiNeural")
  size = "sm",
}: { text: string; voice?: string; size?: "sm" | "md" }) {
  const [loading, setLoading] = useState(false);

  const synth = async () => {
    if (!text?.trim()) return;
    setLoading(true);
    try {
      const r = await fetch("/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voice }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "TTS failed");
      new Audio(data.url).play();
    } catch (e) {
      console.error(e);
      alert("TTS failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={synth}
      disabled={loading}
      className={`inline-flex items-center rounded px-2 py-1 border border-zinc-700 hover:bg-zinc-800 ${size === "sm" ? "text-xs" : "text-sm"}`}
      title="Play audio"
    >
      {loading ? "…" : "▶"}
    </button>
  );
}
