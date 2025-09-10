// src/components/ui/select.tsx
import * as React from "react";
import * as SelectPrimitive from "@radix-ui/react-select";

export const Select = SelectPrimitive.Root;

export function SelectTrigger({
  className = "",
  children,
  ...props
}: React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>) {
  return (
    <SelectPrimitive.Trigger
      {...props}
      className={`inline-flex h-10 w-full items-center justify-between rounded-md border border-zinc-700 bg-zinc-900 px-3 text-sm text-zinc-100 hover:bg-zinc-800 ${className}`}
    >
      {children}
    </SelectPrimitive.Trigger>
  );
}

export const SelectValue = SelectPrimitive.Value;

export function SelectContent({
  className = "",
  children,
  ...props
}: React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        {...props}
        className={`z-50 overflow-hidden rounded-md border border-zinc-700 bg-zinc-900 text-zinc-100 shadow-xl ${className}`}
      >
        <SelectPrimitive.Viewport className="p-1">{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  );
}

export function SelectItem({
  className = "",
  children,
  ...props
}: React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      {...props}
      className={`relative flex cursor-pointer select-none items-center rounded px-2 py-2 text-sm outline-none hover:bg-zinc-800 ${className}`}
    >
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  );
}
