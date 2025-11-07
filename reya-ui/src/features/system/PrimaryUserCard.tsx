import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";

declare const __API__: string | undefined;
const API = typeof __API__ !== "undefined" ? __API__! : "http://127.0.0.1:8000";

type PrimaryUser = { name: string; alias?: string | null; is_admin: boolean };
type IdentityStatus = {
  ok?: boolean;
  has_primary_user?: boolean;
  primary_user?: PrimaryUser | null;
  [key: string]: any;
};

export default function PrimaryUserCard() {
  const { toast } = useToast();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [status, setStatus] = useState<IdentityStatus>({
    primary_user: null,
    has_primary_user: false,
  });

  const [name, setName] = useState("");
  const [alias, setAlias] = useState("");
  const [isAdmin, setIsAdmin] = useState(true);

  // --- Fetch identity ---
  async function refresh() {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API}/memory/primary_user`);
      const data: IdentityStatus = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Failed to load identity");

      setStatus(data);
      const user = data.primary_user ?? data.identity ?? null;
      if (user) {
        setName(user.name ?? "");
        setAlias(user.alias ?? "");
        setIsAdmin(!!user.is_admin);
      }
    } catch (e: any) {
      setError(e?.message || "Failed to load identity");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const displayName = useMemo(
    () =>
      status.primary_user?.alias ||
      status.primary_user?.name ||
      "—",
    [status.primary_user]
  );

  // --- Save identity ---
  async function save() {
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${API}/memory/primary_user`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          alias: alias.trim() || null,
          is_admin: isAdmin,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Save failed");
      setStatus({ primary_user: data.primary_user, has_primary_user: true });

      toast({
        title: "Identity saved",
        description: `${alias || name} is now the primary user.`,
      });
    } catch (e: any) {
      setError(e?.message || "Save failed");
      toast({
        variant: "destructive",
        title: "Save failed",
        description: String(e?.message ?? e),
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="ga-panel ga-outline">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold">Identity</h3>
          <div className="text-xs text-zinc-600">
            {loading
              ? "Loading…"
              : status.has_primary_user
              ? "Primary user set"
              : "Not set"}
          </div>
        </div>

        {error && <div className="text-sm text-red-600">{error}</div>}

        {/* Current */}
        <div className="text-sm">
          <div className="text-zinc-600">Current:</div>
          <div className="mt-0.5">
            {status.primary_user ? (
              <span>
                <b>{displayName}</b>{" "}
                {status.primary_user.is_admin ? "(admin)" : "(user)"}
              </span>
            ) : (
              <span className="text-zinc-500">—</span>
            )}
          </div>
        </div>

        {/* Form */}
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="grid gap-1">
            <span className="text-xs text-zinc-600">Name</span>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Aretel Green"
            />
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-zinc-600">Alias (optional)</span>
            <Input
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
              placeholder="Sydni"
            />
          </label>
        </div>

        <label className="inline-flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            className="h-4 w-4"
            checked={isAdmin}
            onChange={(e) => setIsAdmin(e.target.checked)}
          />
          <span>Grant admin privileges</span>
        </label>

        <div className="flex gap-2">
          <Button
            className="ga-btn"
            disabled={saving || !name.trim()}
            onClick={save}
          >
            {saving ? "Saving…" : "Save primary user"}
          </Button>
          <Button
            variant="outline"
            disabled={loading}
            onClick={refresh}
          >
            Refresh
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
