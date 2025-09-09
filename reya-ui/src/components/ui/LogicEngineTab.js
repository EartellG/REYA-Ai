import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// src/components/ui/LogicEngineTab.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
export default function LogicEngineTab() {
    const [logicInput, setLogicInput] = useState("");
    const [logicOutput, setLogicOutput] = useState("");
    const [logicLoading, setLogicLoading] = useState(false);
    const handleLogicSubmit = async () => {
        if (!logicInput.trim())
            return;
        setLogicLoading(true);
        setLogicOutput("");
        try {
            const res = await fetch("http://127.0.0.1:8000/reya/logic", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: logicInput }),
            });
            const data = await res.json();
            setLogicOutput(data.response);
        }
        catch (err) {
            console.error(err);
            setLogicOutput("⚠️ Failed to fetch logic engine response.");
        }
        finally {
            setLogicLoading(false);
        }
    };
    return (_jsxs("div", { className: "flex flex-col p-6 gap-4 h-full", children: [_jsx("h2", { className: "text-2xl font-bold mb-2", children: "Logic Engine" }), _jsx("p", { className: "text-gray-400 mb-4", children: "Ask REYA to perform structured reasoning or symbolic logic tasks." }), _jsxs("div", { className: "flex gap-2", children: [_jsx("input", { type: "text", value: logicInput, onChange: (e) => setLogicInput(e.target.value), placeholder: "Enter a logic question or deduction task...", className: "flex-1 bg-gray-800 text-white p-2 rounded border border-gray-700" }), _jsx(Button, { onClick: handleLogicSubmit, children: "Run" })] }), _jsx("div", { className: "bg-gray-800 text-white p-4 rounded min-h-[100px] whitespace-pre-wrap", children: logicLoading ? "⏳ Processing with Logic Engine..." : logicOutput })] }));
}
