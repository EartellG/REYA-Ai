const API_BASE = "http://127.0.0.1:8000";

export async function playReyaTTS(text: string): Promise<HTMLAudioElement | null> {
  const res = await fetch(`${API_BASE}/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) return null;

  const data: { ok?: boolean; audio_url?: string | null } = await res.json();
  if (!data?.ok || !data.audio_url) return null;

  const audio = new Audio(`${API_BASE}${data.audio_url}`);
  try { await audio.play(); } catch { /* autoplay blocked — caller handles */ }
  return audio;
}
