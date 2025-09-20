import { useRef, useState } from "react";

type Props = {
  onTranscript: (text: string) => void;   // add it to chat log
  onNavigate: (tab: "chat"|"projects"|"tutor"|"kb"|"settings"|"roles") => void;
  lang?: "ja-JP" | "zh-CN" | "en-US";      // STT language hint
};

export default function VoiceController({ onTranscript, onNavigate, lang = "en-US" }: Props) {
  const Recog = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  const supported = !!Recog;
  const [listening, setListening] = useState(false);
  const [last, setLast] = useState<string>("");
  const recRef = useRef<any>(null);

  const start = () => {
    if (!supported) return alert("Speech recognition not supported in this browser.");
    const rec = new Recog();
    rec.lang = lang;
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = async (e: any) => {
      const txt = e.results?.[0]?.[0]?.transcript?.trim();
      if (!txt) return;
      setLast(txt);
      onTranscript(txt);
      try {
        const r = await fetch("/voice/route", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: txt }),
        });
        const data = await r.json();
        if (r.ok && data?.intent) onNavigate(data.intent);
      } catch (e) {
        console.error("route failed", e);
      }
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recRef.current = rec;
    setListening(true);
    rec.start();
  };

  const stop = () => recRef.current?.stop();

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={listening ? stop : start}
        className={`rounded border border-zinc-700 px-3 py-1 text-sm hover:bg-zinc-800 ${listening ? "bg-zinc-800" : ""}`}
        title="Toggle voice"
      >
        {listening ? "🎙️ Listening" : "🎤 Voice"}
      </button>
      {last && <span className="hidden md:inline text-xs text-zinc-400 truncate max-w-[220px]">“{last}”</span>}
    </div>
  );
}
