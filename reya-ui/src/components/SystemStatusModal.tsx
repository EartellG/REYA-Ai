import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import DiagnosticsPanel from "./DiagnosticsPanel";

/**
 * SystemStatusModal
 * - Uses shadcn/ui Dialog
 * - Opens a modal that contains the DiagnosticsPanel (green/yellow/red icons)
 */
export default function SystemStatusModal() {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="secondary" title="Open system status">🛠️ System Status</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl bg-gray-900 border-gray-800">
        <DialogHeader>
          <DialogTitle className="text-lg">System Status</DialogTitle>
        </DialogHeader>
        <Separator className="bg-gray-800" />
        <div className="mt-3">
          <DiagnosticsPanel />
        </div>
      </DialogContent>
    </Dialog>
  );
}
