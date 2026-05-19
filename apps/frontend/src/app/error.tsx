"use client";

import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="grid min-h-screen place-items-center bg-background p-6">
      <EmptyState
        icon={AlertTriangle}
        title="Algo salió mal"
        description={
          error.digest
            ? `Referencia técnica: ${error.digest}`
            : "Reintentá la operación o avisá al equipo de soporte."
        }
        action={<Button onClick={reset}>Reintentar</Button>}
      />
    </div>
  );
}
