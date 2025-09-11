// src/lib/projectClient.ts
const API = "http://127.0.0.1:8000";

export type PlanResponse = {
  spec: string;
  tasks: string[];
  files?: string[];   // optional (if you return it)
  env?: string[];     // optional
};

export type StatusLog = { ts: string; line: string };

export type StatusResponse = {
  project_id: string;
  phase: "planning" | "scaffolding" | "generating" | "done" | "error";
  progress: number;       // 0..100
  log: StatusLog[];
  error?: string | null;
};

// --- PLAN ---
export async function planProject(
  idea: string,
  target: "web" | "mobile" | "desktop",
  constraints: string[] = []
): Promise<PlanResponse> {
  const res = await fetch(`${API}/proj/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idea, target, constraints }),
  });
  if (!res.ok) throw new Error("planProject failed");
  return res.json();
}

// --- SCAFFOLD ---
export async function scaffoldProject(spec: string): Promise<{ project_id: string; message: string }> {
  const res = await fetch(`${API}/proj/scaffold`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ spec }),
  });
  if (!res.ok) throw new Error("scaffoldProject failed");
  return res.json();
}

// --- STATUS (polling) ---
export async function getStatus(projectId: string): Promise<StatusResponse> {
  const res = await fetch(`${API}/proj/status/${encodeURIComponent(projectId)}`);
  if (!res.ok) throw new Error("getStatus failed");
  return res.json();
}

// --- DOWNLOAD ZIP ---
export function getDownloadUrl(projectId: string): string {
  const q = new URLSearchParams({ project_id: projectId });
  return `${API}/proj/download?${q.toString()}`;
}
