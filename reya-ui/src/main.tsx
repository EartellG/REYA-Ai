// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import REYAApp from "./pages/reya-app"; // or your router root; if you render reya-app.tsx directly, use that
import { ModesProvider } from "@/state/modes";
import { ToastProvider, Toaster } from "@/components/ui/use-toast";
import "@/index.css" // <-- provider + toaster
import "@/styles/fold.css";


ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ModesProvider>
      <ToastProvider>
        <REYAApp />         {/* or <REYAApp /> if that's your top page */}
        <Toaster />     {/* renders the toast container */}
      </ToastProvider>
    </ModesProvider>
  </React.StrictMode>
);
