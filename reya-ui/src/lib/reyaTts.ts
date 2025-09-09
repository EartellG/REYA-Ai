const API_BASE = "http://127.0.0.1:8000";

export async function playReyaTTS(text: string): Promise<HTMLAudioElement | null> {
  const res = await fetch(`${API_BASE}/chat?speak=true`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text }),
  });
  if (!res.ok) return null;

  const data: { audio_url?: string | null } = await res.json();
  if (!data?.audio_url) return null;

  const audio = new Audio(`${API_BASE}${data.audio_url}`);
  try {
    await audio.play(); // may throw if autoplay blocked
  } catch {
    // ignore; LiveAvatarTab will stop animating if audio is null or paused
  }
  return audio;
}
