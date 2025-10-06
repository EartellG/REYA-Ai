// reya-ui/src/lib/api.ts
const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${detail || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function postJSON<T = any>(path: string, body: any): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return json<T>(res);
}

export async function getJSON<T = any>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  return json<T>(res);
}

export { API };
