import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const API = "http://127.0.0.1:8000";

type KBItem = {
  id: string;
  title: string;
  tags: string[];
  preview?: string;
};

const CATS = ["documents", "interests", "work", "personal", "quantum_physics", "deep_sea"] as const;
type Category = typeof CATS[number];

export default function KnowledgeBasePanel() {
  const [category, setCategory] = useState<Category>("quantum_physics");
  const [items, setItems] = useState<KBItem[]>([]);
  const [q, setQ] = useState("");

  const load = async (c: Category) => {
    const res = await fetch(`${API}/kb/list?category=${encodeURIComponent(c)}`);
    if (res.ok) setItems(await res.json());
  };

  useEffect(() => { load(category); }, [category]);

  const doSearch = async () => {
    if (!q.trim()) return load(category);
    const res = await fetch(`${API}/kb/search?query=${encodeURIComponent(q)}&category=${encodeURIComponent(category)}`);
    if (res.ok) setItems(await res.json());
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex gap-2 flex-wrap">
        {CATS.map((c) => (
          <Button key={c} variant={c === category ? "default" : "outline"} onClick={() => setCategory(c)}>
            {c.replace("_", " ")}
          </Button>
        ))}
      </div>

      <div className="flex gap-2">
        <Input placeholder="Search notes…" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && doSearch()} />
        <Button onClick={doSearch}>Search</Button>
      </div>

      <div className="grid md:grid-cols-2 gap-3">
        {items.map((it) => (
          <Card key={it.id}>
            <CardContent className="py-4">
              <div className="font-semibold">{it.title}</div>
              {!!it.tags?.length && <div className="text-xs text-zinc-400 mt-1">#{it.tags.join(" #")}</div>}
              {it.preview && <div className="mt-2 text-sm text-zinc-300">{it.preview}</div>}
            </CardContent>
          </Card>
        ))}
        {!items.length && <div className="text-zinc-400">No items yet.</div>}
      </div>
    </div>
  );
}
