// src/features/system/SystemStatusPanel.tsx
// If you placed PrimaryUserCard in a different folder (e.g., "systems"),
// update the import path below accordingly.
import React, { useEffect, useMemo, useState } from "react";
import PrimaryUserCard from "@/features/system/PrimaryUserCard";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

declare const __API__: string | undefined;
const API = typeof __API__ !== "undefined" ? __API__! : "http://127.0.0.1:8000";

type HealthResp = {
  ok: boolean;
  tools: { npx: boolean; eslint: boolean; ruff: boolean; python: string | boolean };
};

function Pill({ children, tone = "zinc" }: { children: React.ReactNode; tone?: "zinc" | "emerald" | "amber" | "rose" }) {
  const map: Record<string, string> = {
    zinc: "bg-zinc-500/10 text-zinc-700 border-zinc-500/30",
    emerald: "bg-emerald-500/15 text-emerald-800 border-emerald-500/40",
    amber: "bg-amber-500/15 text-amber-800 border-amber-500/40",
    rose: "bg-rose-500/15 text-rose-800 border-rose-500/40",
  };
  return <span className={`px-2 py-0.5 text-xs rounded-full border ${map[tone]}`}>{children}</span>;
}

function LintHealthRow() {
  const [h, setH] = useState<HealthResp | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let on = true;
    (async () => {
      try {
        const r = await fetch(`${API}/roles/reviewer/lint/health`);
        const data = (await r.json()) as HealthResp;
        if (on) setH(data);
      } catch (e: any) {
        if (on) setErr(e?.message || "health failed");
      }
    })();
    return () => {
      on = false;
    };
  }, []);

  const ok = h?.tools ? h.tools.eslint || h.tools.npx || h.tools.ruff : false;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm font-medium">Lint Health</span>
      {err ? (
        <Pill tone="rose">error</Pill>
      ) : ok ? (
        <Pill tone="emerald">ready</Pill>
      ) : (
        <Pill>unknown</Pill>
      )}
      <div className="text-xs text-zinc-600">
        ESLint: {h?.tools?.eslint ? "yes" : "no"} • NPX: {h?.tools?.npx ? "yes" : "no"} • Ruff:{" "}
        {h?.tools?.ruff ? "yes" : "no"}
      </div>
    </div>
  );
}

function ServiceInfo() {
  const [info, setInfo] = useState<any>(null);
  useEffect(() => {
    let on = true;
    (async () => {
      try {
        const r = await fetch(`${API}/`);
        const data = await r.json();
        if (on) setInfo(data);
      } catch {
        if (on) setInfo(null);
      }
    })();
    return () => {
      on = false;
    };
  }, []);
  return (
    <div className="text-sm">
      <div className="text-zinc-600">Backend:</div>
      <div className="mt-0.5 font-mono text-xs">
        {info ? `${info.service} v${info.version}` : "—"}
      </div>
      <div className="mt-1">
        <a
          href={`${API}/docs`}
          target="_blank"
          rel="noreferrer"
          className="text-xs underline text-indigo-700"
        >
          Open API Docs
        </a>
      </div>
    </div>
  );
}

export default function SystemStatusPanel() {
  const [ts] = useState(() => new Date());

  const when = useMemo(
    () => ts.toLocaleString(),
    [ts]
  );

  return (
    <Card className="ga-panel ga-outline">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">System Status</h2>
          <Pill>Updated: {when}</Pill>
        </div>

        {/* Service */}
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded border p-3">
            <ServiceInfo />
          </div>
          <div className="rounded border p-3">
            <LintHealthRow />
          </div>
        </div>

        {/* Identity */}
        <PrimaryUserCard />

        {/* Quick Links */}
        <div className="rounded border p-3">
          <div className="text-sm font-medium mb-2">Utilities</div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => window.open(`${API}/_debug/routes`, "_blank")}>
              View Routes
            </Button>
            <Button variant="outline" size="sm" onClick={() => window.open(`${API}/workspace/root`, "_blank")}>
              Workspace Root
            </Button>
            <Button variant="outline" size="sm" onClick={() => window.open(`${API}/roles/reviewer/lint/health`, "_blank")}>
              Lint Health JSON
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
