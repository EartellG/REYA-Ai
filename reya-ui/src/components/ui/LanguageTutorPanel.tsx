import { useEffect, useRef, useState } from "react";
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

const VOICES: Record<"Japanese" | "Mandarin", string[]> = {
  Japanese: ["ja-JP-NanamiNeural", "ja-JP-AoiNeural", "ja-JP-MayuNeural"],
  Mandarin: ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "zh-CN-XiaoyiNeural"],
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

  // Voice Test state
  const defaultVoice = () => (language === "Japanese" ? "ja-JP-NanamiNeural" : "zh-CN-XiaoxiaoNeural");
  const defaultSample = () => (language === "Japanese" ? "こんにちは" : "你好");
  const [testVoice, setTestVoice] = useState<string>(defaultVoice());
  const [testText, setTestText] = useState<string>(defaultSample());
  const [testing, setTesting] = useState<boolean>(false);

  // Persistent audio element in the DOM (more reliable than new Audio())
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Load progress
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API}/tutor/progress?language=${encodeURIComponent(language)}`);
        if (res.ok) setProgress(await res.json());
      } catch {}
    })();
  }, [language]);

  // Reset voice test defaults when language changes
  useEffect(() => {
    setTestVoice(defaultVoice());
    setTestText(defaultSample());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

  const phonetic = (text: string) =>
    language === "Japanese" ? toRomaji(text) : pinyin(text, { toneType: "symbol" });

  // ---- Robust play helper: try direct streaming src first, then blob fallback
  const playFromEndpoint = async (endpointUrl: string) => {
    if (!audioRef.current) return;
    const a = audioRef.current;
    a.muted = false;
    a.volume = 1.0;
    a.autoplay = false;

    // Strategy A: direct src (best for gesture policies)
    try {
      a.src = `${endpointUrl}${endpointUrl.includes("?") ? "&" : "?"}_ts=${Date.now()}`;
      a.load(); // ensure ready to start
      await a.play();
      return true;
    } catch (eA) {
      console.warn("Direct play failed, trying blob:", eA);
    }

    // Strategy B: blob fallback
    try {
      const res = await fetch(endpointUrl);
      // Read headers for debug
      const engine = res.headers.get("X-REYA-TTS-Engine") || "";
      const vname = res.headers.get("X-REYA-TTS-Voice") || "";
      console.log("[TutorVoice] Backend headers:", { engine, voice: vname, status: res.status });

      const blob = await res.blob();
      if (blob.size === 0) throw new Error("Empty audio blob");
      const url = URL.createObjectURL(blob);
      a.src = url;
      a.load();
      await a.play();
      // Revoke later to keep playing
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
      return true;
    } catch (eB) {
      console.error("Blob play also failed:", eB);
      return false;
    }
  };

  // === Tutor Voice Test ===
  const testTutorVoice = async () => {
    setTesting(true);
    try {
      const url = `${API}/tutor/test_voice?text=${encodeURIComponent(testText)}&voice=${encodeURIComponent(testVoice)}`;
      const ok = await playFromEndpoint(url);
      if (!ok) {
        setStatus("⚠️ Couldn’t start audio. Click again, or try another browser/device output.");
      } else {
        setStatus("");
      }
    } finally {
      setTesting(false);
    }
  };

  // === Lesson helpers (unchanged) ===
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

  // Pronunciation scoring
  const onSpeech = (heard: string) => {
    setSpoken(heard);
    if (!quiz) return;

    const targetDisplay = quiz.native || quiz.question;
    const targetPhon = toPhonetic(targetDisplay, language);
    const heardPhon = normalizeLatin(heard);

    const s = similarity(targetPhon, heardPhon);
    setScore(s);

    if (s >= 0.92) setHint("Excellent! Sounds right.");
    else if (s >= 0.80) setHint("Good! A few sounds were off—try again, slower.");
    else if (s >= 0.65) setHint("Close. Focus on syllable lengths and tones.");
    else setHint("Let’s try again—check syllable order and vowels.");
  };

  return (
    <div className="p-6 space-y-4">
      {/* Hidden but persistent audio element */}
      <audio ref={audioRef} className="hidden" />

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

      {/* Voice Test */}
      <Card className="border border-zinc-800">
        <CardContent className="py-4 space-y-3">
          <div className="font-semibold">Tutor Voice Test</div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="w-64">
              <Select value={testVoice} onValueChange={setTestVoice}>
                <SelectTrigger><SelectValue placeholder="Select voice" /></SelectTrigger>
                <SelectContent>
                  {VOICES[language].map(v => (
                    <SelectItem key={v} value={v}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Input
              className="flex-1 min-w-[220px]"
              value={testText}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTestText(e.target.value)}
              placeholder={language === "Japanese" ? "テキストを入力..." : "输入文本…"}
            />
            <Button onClick={testTutorVoice} disabled={testing}>
              {testing ? "Testing…" : "Test Voice"}
            </Button>
          </div>
          <div className="text-xs text-zinc-400">
            If you still hear nothing, try clicking twice, make sure the tab is focused, and check Windows Sound → that your browser output device isn’t muted or routed elsewhere.
          </div>
        </CardContent>
      </Card>

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
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAnswer(e.target.value)}
                className="flex-1"
              />
              <Button onClick={checkAnswer} className="px-3 py-1 text-sm">
                Check
              </Button>
            </div>

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
                    {language === "Japanese" ? toRomaji(spoken) : pinyin(spoken, { toneType: "symbol" })}
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
