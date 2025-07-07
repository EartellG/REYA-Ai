import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
const icons = {
    Chat: "💬",
    Projects: "📁",
    Avatar: "🧍",
    Logic: "🧠",
    Settings: "⚙️",
};
export function Sidebar({ items, activeTab, onTabChange }) {
    return (_jsx("div", { className: "space-y-4", children: items.map((item) => (_jsxs("div", { onClick: () => onTabChange(item), className: `cursor-pointer p-2 rounded transition ${activeTab === item
                ? "bg-gray-800 font-semibold text-white"
                : "text-gray-400 hover:bg-gray-700"}`, children: [_jsx("span", { className: "mr-2", children: icons[item] || "•" }), item] }, item))) }));
}
