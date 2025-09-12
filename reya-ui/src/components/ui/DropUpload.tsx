import { useCallback, useState } from "react";

export type UploadedFile = { path: string; content: string };

export default function DropUpload({
  onFiles,
  accept = [".ts", ".tsx", ".js", ".jsx", ".json", ".py", ".md"],
}: {
  onFiles: (files: UploadedFile[]) => void;
  accept?: string[];
}) {
  const [hover, setHover] = useState(false);

  const readFiles = useCallback(async (fileList: FileList) => {
    const out: UploadedFile[] = [];
    for (const f of Array.from(fileList)) {
      // strip fakepath and keep just the filename; allow user to edit path later if needed
      const path = f.webkitRelativePath || f.name;
      const text = await f.text();
      out.push({ path, content: text });
    }
    onFiles(out);
  }, [onFiles]);

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setHover(true); }}
      onDragLeave={() => setHover(false)}
      onDrop={async (e) => {
        e.preventDefault();
        setHover(false);
        if (e.dataTransfer.files?.length) await readFiles(e.dataTransfer.files);
      }}
      className={`border-2 border-dashed rounded-lg p-6 text-sm
                  ${hover ? "border-emerald-400 bg-emerald-500/5" : "border-gray-700 bg-gray-900"}`}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="font-medium">Drag & drop files or a folder</div>
          <div className="text-zinc-400">Accepted: {accept.join(", ")}</div>
        </div>
        <label className="px-3 py-2 rounded bg-gray-800 border border-gray-700 cursor-pointer">
          Browse…
          <input
            type="file"
            multiple
            className="hidden"
            accept={accept.join(",")}
            onChange={(e) => e.target.files && readFiles(e.target.files)}
            // NOTE: if you want full folder upload, add webkitdirectory attribute:
            // @ts-expect-error – not in standard typing but supported by Chrome/Edge
            // webkitdirectory
          />
        </label>
      </div>
    </div>
  );
}
