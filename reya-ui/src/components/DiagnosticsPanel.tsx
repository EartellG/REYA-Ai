import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const API_BASE = "http://127.0.0.1:8000";

type Check = { name: string; ok: boolean; warn?: boolean; detail?: string };

type DiagPayload = { summary: string; checks: Check[] };

function StatusIcon({ ok, warn }: { ok: boolean; warn?: boolean }) {
  if (ok) return <span className="text-green-500" title="OK">●</span>;
  if (warn) return <span className="text-yellow-500" title="Warning">●</span>;
  return <span className="text-red-500" title="Failed">●</span>;
}

export default function DiagnosticsPanel() {
  const [data, setData] = useState<DiagPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/diagnostics`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: DiagPayload = await res.json();
      setData(json);
    } catch (e: any) {
      setError(e?.message || "Failed to load diagnostics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <Card className="bg-gray-900 border-gray-800">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">System Diagnostics</h3>
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={load} disabled={loading}>
              {loading ? "Checking…" : "Refresh"}
            </Button>
          </div>
        </div>
        <Separator className="bg-gray-800" />
        {error && (
          <div className="text-red-400 text-sm">{error}</div>
        )}
        {!error && !data && (
          <div className="text-gray-400 text-sm">Loading…</div>
        )}
        {data && (
          <div className="space-y-2">
            <div className="text-sm text-gray-300">Summary: {data.summary}</div>
            <ul className="space-y-1">
              {data.checks.map((c, i) => (
                <li key={i} className="flex items-start gap-2">
                  <StatusIcon ok={c.ok} warn={c.warn} />
                  <div>
                    <div className="text-sm font-medium">{c.name}</div>
                    {c.detail && (
                      <div className="text-xs text-gray-400">{c.detail}</div>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}