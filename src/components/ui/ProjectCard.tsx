// src/components/ui/ProjectCard.tsx

import { Card, CardContent } from "@/components/ui/card";

interface ProjectCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
}

export default function ProjectCard({ title, description, icon }: ProjectCardProps) {
  return (
    <Card className="bg-gray-800 hover:bg-gray-700 transition cursor-pointer">
      <CardContent className="p-4 space-y-2">
        <div className="text-3xl">{icon}</div>
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="text-sm text-gray-300">{description}</p>
      </CardContent>
    </Card>
  );
}
