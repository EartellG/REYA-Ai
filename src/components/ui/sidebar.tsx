// src/components/ui/Sidebar.tsx

interface SidebarProps {
  items: string[];
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const icons: Record<string, string> = {
  Chat: "💬",
  Projects: "📁",
  Avatar: "🧍",
  Logic: "🧠",
  Settings: "⚙️",
};

export function Sidebar({ items, activeTab, onTabChange }: SidebarProps) {
  return (
    <div className="space-y-4">
      {items.map((item) => (
        <div
          key={item}
          onClick={() => onTabChange(item)}
          className={`cursor-pointer p-2 rounded transition ${
            activeTab === item
              ? "bg-gray-800 font-semibold text-white"
              : "text-gray-400 hover:bg-gray-700"
          }`}
        >
          <span className="mr-2">{icons[item] || "•"}</span>
          {item}
        </div>
      ))}
    </div>
  );
}
