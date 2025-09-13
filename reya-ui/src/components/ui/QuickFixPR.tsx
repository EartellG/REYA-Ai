import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import DropUpload, { type UploadedFile } from "@/components/ui/DropUpload";
import { createFixPR, commitLocalFix } from "@/lib/fixClient";
import { useToast } from "@/components/ui/use-toast";

export default function QuickFixPR() {
  const { toast } = useToast();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [title, setTitle] = useState("Fix: clean lint & minor refactors");
  const [desc, setDesc] = useState("");
  const [making, setMaking] = useState(false);
  const [bundleUrl, setBundleUrl] = useState<string | null>(null);
  const [commitLocal, setCommitLocal] = useState(false);
  const [repoPath, setRepoPath] = useState("");
  const [branch, setBranch] = useState("");

  const create = async () => {
    if (!files.length) {
      toast({ title: "No files", description: "Add at least one file to proceed." });
      return;
    }
    setMaking(true);
    try {
      if (commitLocal) {
        const res = await commitLocalFix({
          repo_path: repoPath,
          branch: branch || undefined,
          title,
          description: desc,
          files: files.map(f => ({ path: f.path, content: f.content })),
          push: false,
        });
        toast({
          title: res.commit ? `Committed ${res.commit}` : "No changes to commit",
          description: res.branch ? `Branch: ${res.branch}${res.pushed ? " (pushed)" : ""}` : undefined,
        });
      } else {
        const res = await createFixPR({
          title,
          description: desc,
          files: files.map(f => ({ path: f.path, content: f.content })),
        });
        setBundleUrl(`http://127.0.0.1:8000${res.bundle_url}`);
        toast({ title: "PR bundle created", description: "Download and attach to your repo." });
      }
    } catch (e: unknown) {
      console.error(e);
      toast({ title: "Fix failed", description: String(e), variant: "destructive" });
    } finally {
      setMaking(false);
    }
  };

  return (
    <div className="space-y-3">
      <DropUpload
        onFiles={(added) => setFiles(added)}
        accept={[".ts", ".tsx", ".js", ".py", ".json", ".md"]}
      />

      {!!files.length && (
        <div className="text-xs text-zinc-400">
          {files.length} file(s) staged:
          <ul className="list-disc ml-5 mt-1 max-h-24 overflow-auto">
            {files.slice(0, 8).map((f, i) => <li key={i}>{f.path}</li>)}
            {files.length > 8 && <li>…and more</li>}
          </ul>
        </div>
      )}

      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2"
        placeholder="PR title"
      />
      <textarea
        value={desc}
        onChange={(e) => setDesc(e.target.value)}
        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2"
        rows={3}
        placeholder="PR description (what you fixed, how to test)"
      />

      <div className="mt-2 space-y-2 rounded border border-gray-800 p-3">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={commitLocal}
            onChange={(e) => setCommitLocal(e.target.checked)}
          />
          Commit locally (advanced)
        </label>
        {commitLocal && (
          <div className="grid gap-2 sm:grid-cols-2">
            <input
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2"
              placeholder="Repo path (under /repos or absolute)"
            />
            <input
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2"
              placeholder="Branch (optional)"
            />
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <Button onClick={create} disabled={making}>
          {making ? (commitLocal ? "Committing…" : "Creating…") : (commitLocal ? "Commit Fix" : "Create Fix PR")}
        </Button>

        {!commitLocal && bundleUrl && (
          <Button variant="outline" onClick={() => window.open(bundleUrl!, "_blank")}>
            ⬇ Download PR Bundle
          </Button>
        )}
      </div>
    </div>
  );
}
