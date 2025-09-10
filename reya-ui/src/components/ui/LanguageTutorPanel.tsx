import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const API = "http://127.0.0.1:8000";

type Progress = {
  language: string;
  streak: number;
  last_level?: string | null;
  last_lesson_id?: string | null;
  lessons_completed: string[];
  vocab_count: number;
  sample_vocab: { native: string; translated: string }[];
};

type QuizPayload = {
  question: string;
  answer: string;
  native: string;
  options: string[];
};

export default function LanguageTutorPanel() {
  const [language, setLanguage] = useState<"Japanese" | "Mandarin">("Japanese");
  const [progress, setProgress] = useState<Progress | null>(null);
  const [status, setStatus] = useState<string>("");
  const [quiz, setQuiz] = useState<QuizPayload | null>(null);
  const [answer, setAnswer] = useState("");

  // load progress on mount + when language changes
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API}/tutor/progress?language=${encodeURIComponent(language)}`);
        if (res.ok) setProgress(await res.json());
      } catch {}
    })();
  }, [language]);

  const startLesson = async (level: "beginner" | "intermediate" | "advanced") => {
    setStatus("Starting lesson…");
    setQuiz(null);
    try {
      const res = await fetch(`${API}/tutor/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language, level }),
      });
      const data = await res.json();
      setStatus(data.message || data);
      // refresh progress
      const p = await fetch(`${API}/tutor/progress?language=${encodeURIComponent(language)}`).then(r => r.json());
      setProgress(p);
    } catch (e) {
      setStatus("⚠️ Failed to start lesson.");
    }
  };

  const resume = async () => {
    setStatus("Resuming…");
    setQuiz(null);
    try {
      const res = await fetch(`${API}/tutor/resume?language=${encodeURIComponent(language)}`);
      setStatus((await res.json()).message);
    } catch {
      setStatus("⚠️ Failed to resume.");
    }
  };

  const nextLesson = async () => {
    setStatus("Loading next lesson…");
    setQuiz(null);
    try {
      const res = await fetch(`${API}/tutor/next?language=${encodeURIComponent(language)}`);
      setStatus((await res.json()).message);
      const p = await fetch(`${API}/tutor/progress?language=${encodeURIComponent(language)}`).then(r => r.json());
      setProgress(p);
    } catch {
      setStatus("⚠️ Failed to load next lesson.");
    }
  };

  const getQuiz = async () => {
    setStatus("");
    setAnswer("");
    try {
      const res = await fetch(`${API}/tutor/quiz?language=${encodeURIComponent(language)}`);
      if (res.ok) setQuiz(await res.json());
      else setStatus("No vocab to quiz yet—do a lesson first.");
    } catch {
      setStatus("⚠️ Quiz failed.");
    }
  };

  const checkAnswer = async () => {
    if (!quiz) return;
    try {
      const res = await fetch(`${API}/tutor/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payload: quiz, user_answer: answer }),
      });
      const data = await res.json();
      setStatus(data.message);
    } catch {
      setStatus("⚠️ Check failed.");
    }
  };

  return (
    <div className="p-6 space-y-4">
      {/* Resume banner */}
      {progress?.last_level && progress?.last_lesson_id && (
        <Card className="border border-teal-600/40 bg-teal-950/30">
          <CardContent className="py-4 flex items-center justify-between">
            <div>
              <div className="font-semibold">Resume where you left off</div>
              <div className="text-sm text-zinc-400">
                {language}: level <b>{progress.last_level}</b>, lesson <b>{progress.last_lesson_id}</b>
              </div>
            </div>
            <Button onClick={resume}>Resume</Button>
          </CardContent>
        </Card>
      )}

      <div className="flex items-center gap-3">
        <div className="w-56">
          <Select value={language} onValueChange={(v) => setLanguage(v as any)}>
            <SelectTrigger><SelectValue placeholder="Language" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="Japanese">Japanese</SelectItem>
              <SelectItem value="Mandarin">Mandarin</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button onClick={() => startLesson("beginner")}>Start Beginner</Button>
        <Button variant="secondary" onClick={() => startLesson("intermediate")}>Intermediate</Button>
        <Button variant="secondary" onClick={() => startLesson("advanced")}>Advanced</Button>
        <Button variant="outline" onClick={nextLesson}>Next lesson</Button>
        <Button variant="outline" onClick={getQuiz}>Quiz me</Button>
      </div>

      {status && <div className="text-sm text-zinc-300">{status}</div>}

      {/* quiz */}
      {quiz && (
        <Card>
          <CardContent className="py-4 space-y-3">
            <div className="font-medium">{quiz.question}</div>
            <div className="flex gap-2 flex-wrap">
              {quiz.options.map(opt => (
                <Button key={opt} variant={answer === opt ? "default" : "outline"} onClick={() => setAnswer(opt)}>
                  {opt}
                </Button>
              ))}
            </div>
            <div className="flex gap-2">
              <Input placeholder="Or type your answer…" value={answer} onChange={(e) => setAnswer(e.target.value)} />
              <Button onClick={checkAnswer}>Check</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* progress */}
      {progress && (
        <Card>
          <CardContent className="py-4">
            <div className="font-semibold mb-2">Progress</div>
            <div className="text-sm text-zinc-300">
              Streak: <b>{progress.streak}</b> • Lessons: <b>{progress.lessons_completed.length}</b> • Vocab:{" "}
              <b>{progress.vocab_count}</b>
            </div>
            {!!progress.sample_vocab?.length && (
              <ul className="mt-2 grid grid-cols-2 gap-2 text-sm">
                {progress.sample_vocab.map((v, i) => (
                  <li key={i} className="rounded bg-zinc-800/60 px-2 py-1">
                    {v.native} — {v.translated}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
