import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// src/components/ui/ProjectCard.tsx
import { Card, CardContent } from "@/components/ui/card";
export default function ProjectCard({ title, description, icon }) {
    return (_jsx(Card, { className: "bg-gray-800 hover:bg-gray-700 transition cursor-pointer", children: _jsxs(CardContent, { className: "p-4 space-y-2", children: [_jsx("div", { className: "text-3xl", children: icon }), _jsx("h3", { className: "text-lg font-semibold", children: title }), _jsx("p", { className: "text-sm text-gray-300", children: description })] }) }));
}
