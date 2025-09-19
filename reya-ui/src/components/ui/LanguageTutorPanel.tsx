import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toRomaji } from "wanakana";
import { pinyin } from "pinyin-pro";
import PronounceButton from "@/components/ui/PronounceButton";
import SpeechButton from "@/components/ui/SpeechButton";
import { normalizeLatin, similarity, toPhonetic } from "@/lib/pronounce";

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

  // Pronunciation state
  const [spoken, setSpoken] = useState<string>("");
  const [score, setScore] = useState<number | null>(null);
  const [hint, setHint] = useState<string>("");

  const phonetic = (text: string) =>
    language === "Japanese" ? toRomaji(text) : pinyin(text, { toneType: "mark" });

  const defaultVoice = () =>
    language === "Japanese" ? "ja-JP-NanamiNeural" : "zh-CN-XiaoxiaoNeural";

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
      const p = await fetch(`${API}/tutor/progress?language=${encodeURIComponent(language)}`).then(r => r.json());
      setProgress(p);
    } catch {
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
    setSpoken("");
    setScore(null);
    setHint("");
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

  // === Pronunciation scoring ===
  const onSpeech = (heard: string) => {
    setSpoken(heard);
    if (!quiz) return;

    const targetDisplay = quiz.native || quiz.question; // what the learner should say
    const targetPhon = toPhonetic(targetDisplay, language);
    const heardPhon = normalizeLatin(heard);

    const s = similarity(targetPhon, heardPhon); // 0..1
    setScore(s);

    // Simple hints
    if (s >= 0.92) setHint("Excellent! Sounds right.");
    else if (s >= 0.80) setHint("Good! A few sounds were off—try again, slower.");
    else if (s >= 0.65) setHint("Close. Focus on syllable lengths and tones.");
    else setHint("Let’s try again—check syllable order and vowels.");
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

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
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

      {/* Quiz */}
      {quiz && (
        <Card>
          <CardContent className="py-4 space-y-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="font-medium text-lg">{quiz.question}</div>
                {!!quiz.native && (
                  <div className="text-xs text-zinc-400">
                    {phonetic(quiz.native)}
                  </div>
                )}
              </div>
              <PronounceButton text={quiz.native || quiz.question} voice={defaultVoice()} />
            </div>

            {/* Multiple choice */}
            <div className="flex gap-2 flex-wrap">
              {quiz.options.map(opt => (
                <Button key={opt} variant={answer === opt ? "default" : "outline"} onClick={() => setAnswer(opt)}>
                  {opt}
                </Button>
              ))}
            </div>

            <div className="flex gap-2 items-center">
  <Input
    placeholder="Or type your answer…"
    value={answer}
    onChange={(e) => setAnswer(e.target.value)}
    className="flex-1"
  />
  <Button onClick={checkAnswer} className="px-3 py-1 text-sm">
    Check
  </Button>
</div>


            {/* Pronunciation Check */}
            <div className="mt-2 rounded border border-zinc-800 p-3 bg-zinc-900/40">
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-medium">Pronunciation</div>
                <SpeechButton
                  onResult={onSpeech}
                  lang={language === "Japanese" ? "ja-JP" : "zh-CN"}
                  size="sm"
                />
              </div>

              <div className="mt-2 text-sm">
                <div className="text-zinc-400">Target:</div>
                <div className="text-zinc-200">{quiz.native || quiz.question}</div>
                <div className="text-xs text-zinc-400">{phonetic(quiz.native || quiz.question)}</div>
              </div>

              {spoken && (
                <div className="mt-2 text-sm">
                  <div className="text-zinc-400">You said:</div>
                  <div className="text-zinc-200">{spoken}</div>
                  <div className="text-xs text-zinc-400">
                    {language === "Japanese" ? toRomaji(spoken) : pinyin(spoken, { toneType: "mark" })}
                  </div>
                </div>
              )}

              {score !== null && (
                <div className="mt-2 text-sm">
                  <div>Score: <b>{Math.round(score * 100)}</b>/100</div>
                  <div className="text-zinc-400">{hint}</div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Progress & sample vocab */}
      {progress && (
        <Card>
          <CardContent className="py-4">
            <div className="font-semibold mb-2">Progress</div>
            <div className="text-sm text-zinc-300">
              Streak: <b>{progress.streak}</b> • Lessons: <b>{progress.lessons_completed.length}</b> • Vocab:{" "}
              <b>{progress.vocab_count}</b>
            </div>
            {!!progress.sample_vocab?.length && (
              <ul className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
                {progress.sample_vocab.map((v, i) => (
                  <li key={i} className="rounded border border-zinc-800 bg-zinc-900/40 px-3 py-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="text-base text-zinc-100">{v.native}</div>
                        <div className="text-xs text-zinc-400">{phonetic(v.native)}</div>
                        <div className="text-xs text-zinc-300 mt-1">{v.translated}</div>
                      </div>
                      <div className="shrink-0">
                        <PronounceButton text={v.native} voice={defaultVoice()} size="sm" />
                      </div>
                    </div>
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
