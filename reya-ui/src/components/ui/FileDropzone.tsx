// src/components/ui/FileDropzone.tsx
import { useCallback, useState } from "react";

type Props = {
  onFiles: (files: File[]) => Promise<void> | void;
  accept?: string; // e.g. ".zip,.ts,.tsx,.py"
};

export default function FileDropzone({ onFiles, accept = "" }: Props) {
  const [dragOver, setDragOver] = useState(false);

  const handle = useCallback(
    async (files: FileList | null) => {
      if (!files?.length) return;
      await onFiles(Array.from(files));
    },
    [onFiles]
  );

  return (
    <div
      className={[
        "rounded-lg border-2 border-dashed p-6 text-center transition",
        dragOver ? "border-emerald-400 bg-emerald-400/10" : "border-gray-700 bg-gray-900",
      ].join(" ")}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={async (e) => {
        e.preventDefault();
        setDragOver(false);
        await handle(e.dataTransfer.files);
      }}
    >
      <p className="mb-2 text-zinc-300">Drag & drop code, or</p>
      <label className="inline-flex cursor-pointer items-center gap-2 rounded border border-gray-700 bg-gray-800 px-3 py-1 hover:bg-gray-700">
        <span>Choose files</span>
        <input
          type="file"
          className="hidden"
          multiple
          accept={accept}
          onChange={async (e) => await handle(e.target.files)}
        />
      </label>
      <p className="mt-2 text-xs text-zinc-500">Accepts ZIPs or individual files.</p>
    </div>
  );
}
