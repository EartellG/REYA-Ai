const API = "http://127.0.0.1:8000";

export type CodeFile = { path: string; content: string };

export async function createFixPR(input: {
  title: string;
  description?: string;
  base_branch?: string;
  repo_url?: string | null;
  files: CodeFile[];
}) {
  const res = await fetch(`${API}/proj/fix-pr`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`fix-pr failed: ${res.status}`);
  return res.json() as Promise<{
    ok: boolean;
    pr_id: string;
    bundle_url: string;
    message: string;
  }>;
}
