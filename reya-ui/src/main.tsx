// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import REYAApp from "./pages/reya-app";
import "./index.css";
import { ModesProvider } from "@/state/modes";

console.log("REYA UI boot", new Date().toISOString());

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ModesProvider>
      <REYAApp />
    </ModesProvider>
  </React.StrictMode>
);
