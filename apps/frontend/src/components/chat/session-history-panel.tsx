"use client";

import { useMemo, useState } from "react";
import { History } from "lucide-react";
import { EmptyState } from "@/components/shared/empty-state";
import { SessionListItem } from "@/components/chat/session-list-item";
import {
  SessionFilters,
  type SessionFiltersState,
} from "@/components/chat/session-filters";
import { Skeleton } from "@/components/ui/skeleton";
import type { AgentSessionSummary } from "@/types/agent";

interface SessionHistoryPanelProps {
  sessions: AgentSessionSummary[] | undefined;
  isLoading?: boolean;
  onDelete: (sessionId: string) => void;
}

/**
 * Panel listado de sesiones del usuario con filtros locales.
 * Estado de filtros vive acá (no en URL) — sub-fase 6.5 es interactiva,
 * no necesita URL compartible. Si en Fase 7 (explorer) se vuelve necesario,
 * migramos a query params.
 */
export function SessionHistoryPanel({
  sessions,
  isLoading = false,
  onDelete,
}: SessionHistoryPanelProps) {
  const [filters, setFilters] = useState<SessionFiltersState>({
    search: "",
    mode: null,
    status: null,
  });

  const filtered = useMemo(() => {
    if (!sessions) return [];
    const term = filters.search.trim().toLowerCase();
    return sessions.filter((s) => {
      if (filters.mode && s.mode !== filters.mode) return false;
      if (filters.status && s.status !== filters.status) return false;
      if (term && !s.title.toLowerCase().includes(term)) return false;
      return true;
    });
  }, [sessions, filters]);

  return (
    <section className="rounded-lg border border-border bg-card/50 p-5">
      <header className="mb-4 flex items-center justify-between gap-4">
        <div>
          <h3 className="font-display text-base font-extrabold tracking-tight text-foreground">
            Tus sesiones
          </h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {sessions?.length ?? 0} en total
          </p>
        </div>
      </header>

      <SessionFilters value={filters} onChange={setFilters} />

      <div className="mt-5 space-y-1">
        {isLoading && (
          <>
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </>
        )}

        {!isLoading && (sessions?.length ?? 0) === 0 && (
          <EmptyState
            icon={History}
            title="Sin sesiones todavía"
            description="Cuando inicies una conversación, va a aparecer acá para retomarla más tarde."
          />
        )}

        {!isLoading && (sessions?.length ?? 0) > 0 && filtered.length === 0 && (
          <EmptyState
            icon={History}
            title="Ningún resultado"
            description="Ajustá la búsqueda o limpiá los filtros para ver todas las sesiones."
          />
        )}

        {filtered.map((session) => (
          <SessionListItem key={session.id} session={session} onDelete={onDelete} />
        ))}
      </div>
    </section>
  );
}
