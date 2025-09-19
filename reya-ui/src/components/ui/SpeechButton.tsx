import { useEffect, useRef, useState } from "react";

type Props = {
  onResult: (text: string) => void;
  lang?: "ja-JP" | "zh-CN" | "en-US";
  size?: "sm" | "md";
};

export default function SpeechButton({ onResult, lang = "ja-JP", size = "md" }: Props) {
  const Recog = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  const [supported] = useState(!!Recog);
  const [listening, setListening] = useState(false);
  const recRef = useRef<any>(null);

  useEffect(() => {
    if (!supported) return;
    const rec = new Recog();
    rec.lang = lang;
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (e: any) => {
      const txt = e.results?.[0]?.[0]?.transcript?.trim();
      if (txt) onResult(txt);
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recRef.current = rec;
  }, [supported, lang, onResult]);

  const toggle = () => {
    if (!supported) {
      alert("Speech recognition not supported in this browser.");
      return;
    }
    if (!listening) {
      setListening(true);
      recRef.current?.start();
    } else {
      recRef.current?.stop();
    }
  };

  const cls = size === "sm" ? "px-2 py-1 text-xs" : "px-3 py-2 text-sm";
  return (
    <button
      onClick={toggle}
      className={`inline-flex items-center rounded border border-zinc-700 hover:bg-zinc-800 ${cls}`}
      title={supported ? "Hold to speak / click to toggle" : "Speech not supported"}
    >
      {listening ? "🎙️ Listening…" : "🎤 Speak"}
    </button>
  );
}
