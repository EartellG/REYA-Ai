/* eslint react/react-in-jsx-scope: "off" */
import { useEffect, useRef } from "react";
import TicketizerPanel from "@/features/roles/TicketizerPanel";
import CoderPanel from "@/features/roles/CoderPanel";
import ReviewerPanel from "@/features/roles/ReviewerPanel";
import FixerPanel from "@/features/roles/FixerPanel";
import MonetizerPanel from "@/features/roles/MonetizerPanel";
import { Card, CardContent } from "@/components/ui/card";

type PanelKey = "ticketizer" | "monetizer" | "coder" | "reviewer" | "fixer";

export default function RolesPage() {
  // Refs to each card wrapper
  const ticketizerRef = useRef<HTMLDivElement>(null);
  const monetizerRef  = useRef<HTMLDivElement>(null);
  const coderRef      = useRef<HTMLDivElement>(null);
  const reviewerRef   = useRef<HTMLDivElement>(null);
  const fixerRef      = useRef<HTMLDivElement>(null);

  // Map of panel -> ref (note the | null on the RefObject type)
  const refMap: Record<PanelKey, React.RefObject<HTMLDivElement | null>> = {
    ticketizer: ticketizerRef,
    monetizer : monetizerRef,
    coder     : coderRef,
    reviewer  : reviewerRef,
    fixer     : fixerRef,
  };

  useEffect(() => {
    const onFocus = (e: Event) => {
      const detail = (e as CustomEvent<{ panel?: PanelKey }>).detail;
      const panel = detail?.panel;
      if (!panel) return;
      const ref = refMap[panel];
      ref?.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    window.addEventListener("reya:roles-focus", onFocus as EventListener);
    return () => window.removeEventListener("reya:roles-focus", onFocus as EventListener);
  }, [refMap]);

  return (
    <div className="container mx-auto max-w-5xl space-y-6">
      <h1 className="text-2xl font-bold">REYA Roles</h1>

      {/* Ticketizer */}
      <div ref={ticketizerRef}>
        <Card className="ga-panel ga-outline">
          <CardContent className="p-4">
            <h2 className="font-semibold mb-2">Ticketizer 🎟️</h2>
            <TicketizerPanel />
          </CardContent>
        </Card>
      </div>

      {/* Monetizer */}
      <div ref={monetizerRef}>
        <Card className="ga-panel ga-outline">
          <CardContent className="p-4">
            <h2 className="font-semibold mb-2">Monetizer 💰</h2>
            <MonetizerPanel />
          </CardContent>
        </Card>
      </div>

      {/* Coder */}
      <div ref={coderRef}>
        <Card className="ga-panel ga-outline">
          <CardContent className="p-4">
            <h2 className="font-semibold mb-2">Coder 👩‍💻</h2>
            <CoderPanel />
          </CardContent>
        </Card>
      </div>

      {/* Reviewer */}
      <div ref={reviewerRef}>
        <Card className="ga-panel ga-outline">
          <CardContent className="p-4">
            <h2 className="font-semibold mb-2">Reviewer 🔍</h2>
            <ReviewerPanel />
          </CardContent>
        </Card>
      </div>

      {/* Fixer */}
      <div ref={fixerRef}>
        <Card className="ga-panel ga-outline">
          <CardContent className="p-4">
            <h2 className="font-semibold mb-2">Fixer 🔧</h2>
            <FixerPanel />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
