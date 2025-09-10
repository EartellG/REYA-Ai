import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

export function DialogContent({
  className = "",
  children,
}: React.PropsWithChildren<{ className?: string }>) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 bg-black/60" />
      <DialogPrimitive.Content
        className={`fixed left-1/2 top-1/2 z-50 w-[90vw] max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-gray-800 bg-gray-900 p-4 shadow-xl focus:outline-none ${className}`}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DialogHeader({
  className = "",
  children,
}: React.PropsWithChildren<{ className?: string }>) {
  return <div className={`mb-2 ${className}`}>{children}</div>;
}

export function DialogTitle({
  className = "",
  children,
}: React.PropsWithChildren<{ className?: string }>) {
  // Screen-reader friendly title
  return <DialogPrimitive.Title className={`text-lg font-semibold ${className}`}>{children}</DialogPrimitive.Title>;
}

export function DialogDescription({
  className = "",
  children,
}: React.PropsWithChildren<{ className?: string }>) {
  // Screen-reader friendly description (fixes Radix warning)
  return (
    <DialogPrimitive.Description className={`text-sm text-zinc-400 ${className}`}>
      {children}
    </DialogPrimitive.Description>
  );
}
