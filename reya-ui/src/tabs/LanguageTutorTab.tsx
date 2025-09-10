// src/tabs/LanguageTutorTab.tsx
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type LangKey = "japanese" | "mandarin";

type Progress = {
  lessonIndex: number;
  mastered: string[];    // vocab ids
  lastOpenedAt: number;  // timestamp for “resume” banner
};

const defaultProgress: Progress = { lessonIndex: 0, mastered: [], lastOpenedAt: 0 };

const lessons: Record<LangKey, { id: string; title: string; words: { id: string; q: string; a: string }[] }[]> = {
  japanese: [
    { id: "jp-1", title: "Basics 1", words: [
      { id: "jp-1-1", q: "こんにちは", a: "hello" },
      { id: "jp-1-2", q: "ありがとう", a: "thank you" },
    ]},
    { id: "jp-2", title: "Greetings", words: [
      { id: "jp-2-1", q: "おはよう", a: "good morning" },
    ]},
  ],
  mandarin: [
    { id: "zh-1", title: "Basics 1", words: [
      { id: "zh-1-1", q: "你好 (nǐ hǎo)", a: "hello" },
      { id: "zh-1-2", q: "谢谢 (xièxie)", a: "thank you" },
    ]},
  ],
};

function useProgress(lang: LangKey) {
  const key = `reya:tutor:${lang}`;
  const [progress, setProgress] = useState<Progress>(() => {
    try { return JSON.parse(localStorage.getItem(key) || "") as Progress; }
    catch { return defaultProgress; }
  });
  useEffect(() => { localStorage.setItem(key, JSON.stringify(progress)); }, [key, progress]);
  return { progress, setProgress, storageKey: key };
}

export default function LanguageTutorTab() {
  const [lang, setLang] = useState<LangKey>("japanese");
  const { progress, setProgress } = useProgress(lang);

  const lesson = useMemo(() => lessons[lang][progress.lessonIndex] ?? lessons[lang][0], [lang, progress.lessonIndex]);

  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState("");

  const currentCard = lesson.words[0]; // simple “current card”; iterate later

  const check = () => {
    const ok = answer.trim().toLowerCase() === currentCard.a.toLowerCase();
    setFeedback(ok ? "✅ Correct!" : `❌ Answer: ${currentCard.a}`);
    if (ok) {
      setProgress({ ...progress, mastered: Array.from(new Set([...progress.mastered, currentCard.id])), lastOpenedAt: Date.now() });
    }
  };

  const nextLesson = () => {
    const next = Math.min(progress.lessonIndex + 1, lessons[lang].length - 1);
    setProgress({ ...progress, lessonIndex: next, lastOpenedAt: Date.now() });
    setAnswer(""); setFeedback("");
  };

  const canResume = progress.lastOpenedAt > 0 && (progress.lessonIndex > 0 || progress.mastered.length > 0);

  return (
    <div className="p-6 space-y-4">
      {/* Resume banner */}
      {canResume && (
        <div className="rounded-xl border border-emerald-600/40 bg-emerald-900/20 p-3 flex items-center justify-between">
          <div className="text-emerald-300">
            Resume where you left off: <b>{lesson.title}</b> ({progress.mastered.length} words mastered)
          </div>
          <Button onClick={() => setProgress({ ...progress, lessonIndex: progress.lessonIndex })}>
            Resume
          </Button>
        </div>
      )}

      {/* Language selector */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <Button
            variant={lang === "japanese" ? "default" : "secondary"}
            onClick={() => setLang("japanese")}
          >🇯🇵 Japanese</Button>
          <Button
            variant={lang === "mandarin" ? "default" : "secondary"}
            onClick={() => setLang("mandarin")}
          >🇨🇳 Mandarin</Button>
        </div>
        <div className="text-sm text-zinc-400">
          Lesson: <b>{lesson.title}</b> · Progress: {progress.mastered.length} words
        </div>
      </div>

      <div className="rounded-xl border border-zinc-700 p-5 bg-zinc-900/40">
        <div className="text-lg mb-2">Translate:</div>
        <div className="text-2xl font-semibold mb-4">{currentCard.q}</div>
        <div className="flex gap-2">
          <Input value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Your answer…" />
          <Button onClick={check}>Check</Button>
          <Button variant="secondary" onClick={nextLesson}>Next Lesson</Button>
        </div>
        {feedback && <div className="mt-3">{feedback}</div>}
      </div>

      <div className="text-sm text-zinc-400">
        Your progress is saved separately for 🇯🇵 and 🇨🇳 — you can switch anytime and resume later.
      </div>
    </div>
  );
}
