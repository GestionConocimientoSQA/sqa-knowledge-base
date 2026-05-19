"use client";

import { Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { DOC_TYPES, FOLDERS } from "@/lib/mocks/data";
import type { ClassificationPayload } from "@/types/agent";

interface ClassificationCardProps {
  classification: ClassificationPayload;
}

/**
 * Card que muestra la clasificación sugerida por el agente.
 * Lookup de etiquetas se hace contra los mocks de Fase 5; en Fase 1 se
 * reemplaza por una query a `/api/v1/categories` y `/api/v1/document-types`.
 */
export function ClassificationCard({ classification }: ClassificationCardProps) {
  const folder = FOLDERS.find((f) => f.code === classification.category);
  const docType = DOC_TYPES.find((t) => t.code === classification.documentType);
  const confidencePct = Math.round(classification.confidence * 100);

  return (
    <aside
      className="rounded-lg border border-border bg-card/80 p-3 shadow-sm"
      aria-label="Clasificación sugerida"
    >
      <header className="mb-2 flex items-center gap-2">
        <Sparkles className="h-3.5 w-3.5 text-sqa-naranja" aria-hidden />
        <div className="eyebrow text-[10px] text-muted-foreground">
          Clasificación sugerida
        </div>
      </header>
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="accent" className="font-mono">
          {classification.category}
        </Badge>
        <span className="text-sm font-semibold text-foreground">
          {folder?.label ?? classification.category}
        </span>
        <span className="text-muted-foreground" aria-hidden>
          ·
        </span>
        <Badge variant="outline" className="font-mono">
          {classification.documentType}
        </Badge>
        <span className="text-sm font-semibold text-foreground">
          {docType?.label ?? classification.documentType}
        </span>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <div className="flex-1">
          <div className="mb-1 flex items-center justify-between text-[11px]">
            <span className="text-muted-foreground">Confianza</span>
            <span className="font-display font-bold text-foreground">
              {confidencePct}%
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-sqa-naranja transition-[width] duration-500"
              style={{ width: `${confidencePct}%` }}
              aria-hidden
            />
          </div>
        </div>
      </div>
      {classification.rationale && (
        <p className="mt-3 text-[12px] italic text-muted-foreground">
          {classification.rationale}
        </p>
      )}
    </aside>
  );
}
