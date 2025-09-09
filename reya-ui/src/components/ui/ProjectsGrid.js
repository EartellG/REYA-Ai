import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// src/components/ui/ProjectsGrid.tsx
import ProjectCard from "@/components/ui/ProjectCard";
import { Input } from "@/components/ui/input";
export default function ProjectsGrid() {
    return (_jsxs("div", { className: "p-6 space-y-4", children: [_jsx("h2", { className: "text-2xl font-bold", children: "Projects" }), _jsx(Input, { placeholder: "Search...", className: "bg-gray-900 border-gray-700" }), _jsxs("div", { className: "grid grid-cols-2 gap-4", children: [_jsx(ProjectCard, { title: "Document Analysis", description: "Extract text and data from documents", icon: _jsx("span", { children: "\uD83D\uDCC4" }) }), _jsx(ProjectCard, { title: "Image Classifier", description: "Categorize images using machine learning", icon: _jsx("span", { children: "\uD83D\uDDBC\uFE0F" }) }), _jsx(ProjectCard, { title: "Voice Assistant", description: "Transcribe and respond to voice input", icon: _jsx("span", { children: "\uD83C\uDF99\uFE0F" }) }), _jsx(ProjectCard, { title: "GitHub Insights", description: "Summarize issues and PRs in repos", icon: _jsx("span", { children: "\uD83D\uDC19" }) })] })] }));
}
