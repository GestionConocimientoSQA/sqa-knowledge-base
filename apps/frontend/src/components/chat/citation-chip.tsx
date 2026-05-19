"use client";

import { FileText } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { CitationPayload } from "@/types/agent";

interface CitationChipProps {
  citation: CitationPayload;
}

/**
 * Chip de citación. Trigger compacto que abre tooltip con sección + snippet.
 * Presentational puro — el padre maneja navegación al documento cuando exista.
 */
export function CitationChip({ citation }: CitationChipProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-sqa-azul-medio-claro/30 bg-sqa-azul-medio-claro/10 px-2.5 py-1 font-display text-[11px] font-semibold text-sqa-azul-medio-claro transition-colors hover:bg-sqa-azul-medio-claro/20"
          aria-label={`Citación: ${citation.filename}, ${citation.section}`}
        >
          <FileText className="h-3 w-3 shrink-0" />
          <span className="truncate">{citation.filename}</span>
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-sm">
        <div className="space-y-1">
          <div className="font-display text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            {citation.section}
          </div>
          <p className="text-[12px] leading-snug text-foreground">
            {citation.snippet}
          </p>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}
