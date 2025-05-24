import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import REYAApp from "./app/reya-app";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <REYAApp />
  </React.StrictMode>,
);
