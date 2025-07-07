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
    <div className="space-y-2 px-2 py-4">
      {items.map((item) => (
        <button
          key={item}
          onClick={() => onTabChange(item)}
          className={`flex items-center w-full px-4 py-2 rounded-md transition-colors duration-200 text-left font-medium ${
            activeTab === item
              ? "bg-gray-800 text-white"
              : "text-gray-400 hover:bg-gray-700 hover:text-white"
          }`}
        >
          <span className="mr-2 text-lg">{icons[item] || "•"}</span>
          {item}
        </button>
      ))}
    </div>
  );
}
