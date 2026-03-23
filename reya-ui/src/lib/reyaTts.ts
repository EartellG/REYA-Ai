export async function playReyaTTS(text: string, voice?: string) {
  const r = await fetch("http://127.0.0.1:8000/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice }),
  });

  const data = await r.json();

  if (!r.ok || !data?.audio_url)
    throw new Error(data?.detail || "No audio_url returned by backend");

  const url =
    "http://127.0.0.1:8000" +
    data.audio_url +
    (data.audio_url.includes("?") ? "&" : "?") +
    "v=" + Date.now();

  const a = new Audio(url);
  a.preload = "auto";
  await a.play();
  return a;
}
