// src/components/ui/ToasterMount.tsx
import React from "react";
import { ToastProvider } from "@/components/ui/use-toast";

/**
 * Wrap your app with <ToastProvider>. It already portal-renders <Toaster />,
 * so you don't need a separate Toaster component or import.
 */
export default function ToasterMount({ children }: { children?: React.ReactNode }) {
  return <ToastProvider>{children}</ToastProvider>;
}
