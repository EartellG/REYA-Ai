// src/components/ui/ProjectsGrid.tsx

import ProjectCard from "@/components/ui/ProjectCard";
import { Input } from "@/components/ui/input";

export default function ProjectsGrid() {
  return (
    <div className="p-6 space-y-4">
      <h2 className="text-2xl font-bold">Projects</h2>
      <Input placeholder="Search..." className="bg-gray-900 border-gray-700" />
      <div className="grid grid-cols-2 gap-4">
        <ProjectCard
          title="Document Analysis"
          description="Extract text and data from documents"
          icon={<span>📄</span>}
        />
        <ProjectCard
          title="Image Classifier"
          description="Categorize images using machine learning"
          icon={<span>🖼️</span>}
        />
        <ProjectCard
          title="Voice Assistant"
          description="Transcribe and respond to voice input"
          icon={<span>🎙️</span>}
        />
        <ProjectCard
          title="GitHub Insights"
          description="Summarize issues and PRs in repos"
          icon={<span>🐙</span>}
        />
      </div>
    </div>
  );
}
