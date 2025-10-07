// src/pages/RolesPage.tsx
/* eslint react/react-in-jsx-scope: "off" */
import TicketizerPanel from "@/features/roles/TicketizerPanel";
import CoderPanel from "@/features/roles/CoderPanel";
import ReviewerPanel from "@/features/roles/ReviewerPanel";
import FixerPanel from "@/features/roles/FixerPanel";
import MonetizerPanel from "@/features/roles/MonetizerPanel";
import { Card, CardContent } from "@/components/ui/card";

export default function RolesPage() {
  return (
    <div className="container mx-auto max-w-5xl space-y-6">
      <h1 className="text-2xl font-bold">REYA Roles</h1>

      <Card className="ga-panel ga-outline">
        <CardContent className="p-4">
          <h2 className="font-semibold mb-2">Ticketizer 🎟️</h2>
          <TicketizerPanel />
        </CardContent>
      </Card>

      <Card className="ga-panel ga-outline">
        <CardContent className="p-4">
          <h2 className="font-semibold mb-2">Monetizer 💰</h2>
          <MonetizerPanel />
        </CardContent>
      </Card>

      <Card className="ga-panel ga-outline">
        <CardContent className="p-4">
          <h2 className="font-semibold mb-2">Coder 👩‍💻</h2>
          <CoderPanel />
        </CardContent>
      </Card>

      <Card className="ga-panel ga-outline">
        <CardContent className="p-4">
          <h2 className="font-semibold mb-2">Reviewer 🔍</h2>
          <ReviewerPanel />
        </CardContent>
      </Card>

      <Card className="ga-panel ga-outline">
        <CardContent className="p-4">
          <h2 className="font-semibold mb-2">Fixer 🔧</h2>
          <FixerPanel />
        </CardContent>
      </Card>
    </div>
  );
}
