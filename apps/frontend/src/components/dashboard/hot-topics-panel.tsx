"use client";

import { Flame, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { HotTopic } from "@/types/domain";

interface HotTopicsPanelProps {
  topics: HotTopic[] | undefined;
  isLoading?: boolean;
}

/**
 * Top de temas demandados en los últimos 30 días. Resalta `isGap=true`
 * — temas con alta demanda pero pocas citaciones, indicador de KB
 * faltante que el equipo debería capturar.
 */
export function HotTopicsPanel({ topics, isLoading }: HotTopicsPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Flame className="h-4 w-4 text-sqa-naranja" aria-hidden />
          Temas en demanda · 30 días
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2" aria-label="Cargando temas en demanda">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : !topics || topics.length === 0 ? (
          <EmptyState
            icon={Flame}
            title="Sin actividad reciente"
            description="Cuando se registren consultas, los temas más buscados aparecerán acá."
            className="border-0 py-4"
          />
        ) : (
          <ul className="space-y-2" aria-label={`${topics.length} temas en demanda`}>
            {topics.map((t) => (
              <li
                key={t.topic}
                className="flex items-center justify-between gap-3 rounded-md border border-border bg-card/50 px-3 py-2"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-display text-[13px] font-semibold">
                      {t.topic}
                    </span>
                    {t.isGap && (
                      <Badge
                        variant="outline"
                        className="border-destructive/40 text-destructive"
                      >
                        <AlertTriangle className="h-3 w-3" />
                        Gap
                      </Badge>
                    )}
                  </div>
                  <div className="mt-0.5 text-[11px] text-muted-foreground">
                    <span className="font-mono">{t.queries30d}</span> consultas ·{" "}
                    <span className="font-mono">{t.citationCount}</span> citaciones
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
