// src/lib/reyaTts.ts
export async function playReyaTTS(text: string, voice?: string) {
  const r = await fetch("http://127.0.0.1:8000/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice }),
  });
  const data = await r.json();
  if (!r.ok || !data?.url) throw new Error(data?.detail || "No URL");

  // prevent stale/partial caching on very first read
  const url = data.url + (data.url.includes("?") ? "&" : "?") + "v=" + Date.now();

  const a = new Audio(url);
  a.preload = "auto";
  await a.play();
  return a;
}
