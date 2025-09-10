// src/tabs/KnowledgeBaseTab.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const kb = {
  quantum: `
# Quantum Physics (quick brief)
- Superposition: states can exist in combinations until measurement.
- Entanglement: correlated states with nonlocal correlations.
- Measurement problem: collapse vs decoherence interpretations.
- Key equations: Schrödinger equation, Born rule.
`.trim(),
  ocean: `
# Deep Sea Exploration (quick brief)
- Zones: epipelagic to hadal, pressure & light constraints.
- Vehicles: ROVs, AUVs, crewed submersibles.
- Sensing: sonar, CTD, cameras, environmental DNA.
- Hazards: pressure, comms limits, energy, biofouling.
`.trim(),
};

export default function KnowledgeBaseTab() {
  const [topic, setTopic] = useState<"quantum" | "ocean">("quantum");
  const [notes, setNotes] = useState("");

  return (
    <div className="p-6 space-y-4">
      <div className="flex gap-2">
        <Button variant={topic === "quantum" ? "default" : "secondary"} onClick={() => setTopic("quantum")}>🧪 Quantum Physics</Button>
        <Button variant={topic === "ocean" ? "default" : "secondary"} onClick={() => setTopic("ocean")}>🌊 Deep Sea</Button>
      </div>

      <pre className="whitespace-pre-wrap rounded-xl border border-zinc-700 p-5 bg-zinc-900/40 text-zinc-200">
        {topic === "quantum" ? kb.quantum : kb.ocean}
      </pre>

      <div>
        <div className="text-sm text-zinc-400 mb-1">Your scratch notes</div>
        <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Write thoughts, links, and prompts you'd like REYA to use…" />
      </div>
    </div>
  );
}
