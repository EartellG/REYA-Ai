// src/components/TopModeBar.tsx
import { Button } from "@/components/ui/button";
import { useModes } from "@/state/modes";

export default function TopModeBar() {
  const { multimodal, liveAvatar, logicEngine, offlineSmart, setModes } = useModes();
  const Chip = ({
    on,
    label,
    onClick,
  }: { on: boolean; label: string; onClick: () => void }) => (
    <Button
      variant={on ? "default" : "secondary"}
      onClick={onClick}
      className="rounded-full"
      title={label}
    >
      {label} {on ? "●" : "○"}
    </Button>
  );
  return (
    <div className="flex items-center gap-2 px-4 py-3">
      <Chip on={multimodal} label="🧠 Multimodal" onClick={() => setModes({ multimodal: !multimodal })} />
      <Chip on={liveAvatar} label="🗣️ Live Avatar" onClick={() => setModes({ liveAvatar: !liveAvatar })} />
      <Chip on={logicEngine} label="⚙️ Logic Mode" onClick={() => setModes({ logicEngine: !logicEngine })} />
      <Chip on={offlineSmart} label="🌐 Offline Smart" onClick={() => setModes({ offlineSmart: !offlineSmart })} />
    </div>
  );
}
