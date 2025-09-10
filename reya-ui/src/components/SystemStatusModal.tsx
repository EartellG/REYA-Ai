import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import DiagnosticsPanel from "./DiagnosticsPanel";

/**
 * SystemStatusModal
 * - Uses shadcn/ui Dialog
 * - Opens a modal that contains the DiagnosticsPanel (green/yellow/red icons)
 */
export default function SystemStatusModal() {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [open, setOpen] = useState(false);

  return (
      <Dialog>
      <DialogTrigger asChild>
      <Button variant="outline">System Status</Button>
      </DialogTrigger>
      <DialogContent>
      <DialogHeader>
      <DialogTitle>System Status</DialogTitle>
      <DialogDescription>Live checks for personality, LLM, TTS, and more.</DialogDescription>
      </DialogHeader>
        <Separator className="bg-gray-800" />
        <div className="mt-3">
          <DiagnosticsPanel />
        </div>
      </DialogContent>
    </Dialog>
  );
}
