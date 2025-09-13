import React, { useCallback, useRef, useState } from "react";

export type UploadedFile = {
  /** Best-effort relative path (uses webkitRelativePath when available) */
  path: string;
  /** Full file text (utf-8). For binaries, adapt as needed. */
  content: string;
};

type Props = {
  onFiles: (files: UploadedFile[]) => void;
  /** Accepts string | string[] | undefined */
  accept?: string | string[];
  multiple?: boolean;
  className?: string;
};

export default function DropUpload({
  onFiles,
  accept,
  multiple = true,
  className = "",
}: Props) {
  const [hover, setHover] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const acceptAttr = Array.isArray(accept) ? accept.join(",") : accept ?? "";

  const readFiles = useCallback(async (fileList: FileList | File[]) => {
    const files = Array.from(fileList);
    // guard: no setState here; only when finished we call onFiles once
    const results: UploadedFile[] = [];
    for (const f of files) {
      const text = await f.text().catch(() => "");
      const path =
        // keep folder structure when dropping directories (Chrome)
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ((f as any).webkitRelativePath as string) || f.name;
      results.push({ path, content: text });
    }
    onFiles(results);
  }, [onFiles]);

  const onDrop = useCallback(async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setHover(false);

    // Prefer DataTransferItemList to walk directories
    if (e.dataTransfer.items && e.dataTransfer.items.length) {
      const filePromises: Promise<File>[] = [];
      // @ts-expect-error: webkitGetAsEntry exists in Chromium
      const toFilePromises = (entry: any): void => {
        if (!entry) return;
        if (entry.isFile) {
          filePromises.push(new Promise<File>((resolve, reject) => {
            entry.file(resolve, reject);
          }));
        } else if (entry.isDirectory) {
          const reader = entry.createReader();
          reader.readEntries((entries: any[]) => {
            entries.forEach(toFilePromises);
          });
        }
      };

      for (const item of Array.from(e.dataTransfer.items)) {
        if (item.kind === "file") {
          // @ts-expect-error: getAsEntry is webkit API
          const entry = item.getAsEntry?.() || item.webkitGetAsEntry?.();
          if (entry) {
            toFilePromises(entry);
          } else {
            const f = item.getAsFile();
            if (f) filePromises.push(Promise.resolve(f));
          }
        }
      }
      const files = await Promise.all(filePromises);
      await readFiles(files);
    } else if (e.dataTransfer.files && e.dataTransfer.files.length) {
      await readFiles(e.dataTransfer.files);
    }
  }, [readFiles]);

  const onChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length) {
      await readFiles(e.target.files);
      // reset so selecting same files again still triggers onChange
      e.target.value = "";
    }
  }, [readFiles]);

  return (
    <div
      onDragEnter={(e) => { e.preventDefault(); setHover(true); }}
      onDragOver={(e) => { e.preventDefault(); setHover(true); }}
      onDragLeave={(e) => { e.preventDefault(); setHover(false); }}
      onDrop={onDrop}
      className={[
        "rounded-lg border border-dashed px-4 py-6 text-sm cursor-pointer",
        hover ? "border-emerald-500 bg-emerald-500/5" : "border-gray-700 bg-gray-900/40",
        className,
      ].join(" ")}
      onClick={() => inputRef.current?.click()}
      role="button"
      aria-label="Drop files here or click to select"
    >
      <div className="text-center">
        <div className="font-medium">Drop files/folders here</div>
        <div className="text-xs text-zinc-400 mt-1">
          or click to choose {multiple ? "multiple files" : "a file"}
          {acceptAttr ? ` (${acceptAttr})` : ""}
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={acceptAttr}
        multiple={multiple}
        onChange={onChange}
        className="hidden"
        // Chromium directory selection (optional)
        // @ts-expect-error – non-standard attributes are fine in Chromium
        webkitdirectory=""
        // @ts-expect-error – same as above
        directory=""
      />
    </div>
  );
}
