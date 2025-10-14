// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import REYAApp from "./pages/reya-app";
import { ModesProvider } from "@/state/modes";
import { ToastProvider } from "@/components/ui/use-toast";
import "@/index.css";
import "@/styles/fold.css";

document.documentElement.setAttribute("data-theme", "glass-aurora-purple");

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ModesProvider>
      {/* ToastProvider already portal-renders <Toaster /> */}
      <ToastProvider>
        <REYAApp />
      </ToastProvider>
    </ModesProvider>
  </React.StrictMode>
);
