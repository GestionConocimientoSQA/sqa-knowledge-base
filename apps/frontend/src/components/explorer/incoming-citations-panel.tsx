"use client";

import Link from "next/link";
import { Quote } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/shared/empty-state";
import type { IncomingCitation } from "@/types/domain";

interface IncomingCitationsPanelProps {
  citations: IncomingCitation[];
}

/**
 * Sidebar con citaciones recibidas por este documento desde otras
 * piezas del KB. Útil para detectar relevancia transversal y mapear
 * el grafo de conocimiento. Backend Fase 3 (RAG) las genera al
 * indexar el doc origen.
 */
export function IncomingCitationsPanel({
  citations,
}: IncomingCitationsPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Quote className="h-4 w-4 text-sqa-naranja" aria-hidden />
          Citado por
          {citations.length > 0 && (
            <Badge variant="secondary" className="ml-auto font-mono">
              {citations.length}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {citations.length === 0 ? (
          <EmptyState
            icon={Quote}
            title="Sin citaciones recibidas"
            description="Cuando otros documentos referencien éste, aparecerán acá."
            className="border-0 py-4"
          />
        ) : (
          <ul className="space-y-3" aria-label={`${citations.length} citaciones recibidas`}>
            {citations.map((c) => (
              <li key={`${c.sourceDocId}-${c.section}`}>
                <Link
                  href={`/explorer/${c.sourceDocId}` as never}
                  className="block rounded-md border border-border bg-card/50 p-3 transition-colors hover:border-sqa-naranja/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <div className="flex items-center gap-2 text-[11px]">
                    <Badge variant="outline" className="font-mono">
                      {c.sourceFolder}
                    </Badge>
                    <span className="font-mono text-muted-foreground">
                      {c.section}
                    </span>
                  </div>
                  <div className="mt-2 font-display text-[13px] font-bold leading-snug">
                    {c.sourceTitle}
                  </div>
                  <blockquote className="mt-2 border-l-2 border-sqa-naranja/40 pl-2 text-[12px] italic text-muted-foreground">
                    {c.snippet}
                  </blockquote>
                  <div className="mt-2 text-[10.5px] text-muted-foreground">
                    Citado el {c.citedAt}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
