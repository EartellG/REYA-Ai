const API = "http://127.0.0.1:8000";

export type CodeFile = { path: string; content: string };
export type FixFile = { path: string; content: string }; 


export async function createFixPR(payload: {
  title: string;
  description: string;
  files: FixFile[];
}) {
  const res = await fetch(`${API}/proj/fix/pr`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// NEW: local git commit
export async function commitLocalFix(payload: {
  repo_path: string;
  branch?: string;
  title: string;
  description?: string;
  files: FixFile[];
  push?: boolean;
}) {
  const res = await fetch(`${API}/git/commit-local`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
