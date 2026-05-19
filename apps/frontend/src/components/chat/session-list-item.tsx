"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { MODE_COPY } from "@/lib/chat/mode-copy";
import type { AgentSessionSummary, SessionStatus } from "@/types/agent";

const STATUS_DOT_CLASSES: Record<SessionStatus, string> = {
  active: "bg-emerald-500",
  paused: "bg-amber-500",
  completed: "bg-sqa-azul-medio-claro",
  abandoned: "bg-muted-foreground",
};

const STATUS_LABEL: Record<SessionStatus, string> = {
  active: "Activa",
  paused: "Pausada",
  completed: "Completada",
  abandoned: "Abandonada",
};

interface SessionListItemProps {
  session: AgentSessionSummary;
  active?: boolean;
  compact?: boolean;
  onDelete?: (sessionId: string) => void;
  /** Para sidebar oscuro: invierte colores de hover/borde. */
  dark?: boolean;
}

/**
 * Item visual de una sesión. Lo usa el sidebar (compact + dark) y el panel
 * de historial en /chat (full + light). Toda la lógica de filtros y delete
 * vive en el contenedor — este componente solo renderiza.
 */
export function SessionListItem({
  session,
  active = false,
  compact = false,
  onDelete,
  dark = false,
}: SessionListItemProps) {
  const copy = MODE_COPY[session.mode];
  const Icon = copy.icon;
  const updated = formatDistanceToNow(new Date(session.updatedAt), {
    addSuffix: true,
    locale: es,
  });

  return (
    <div
      className={cn(
        "group relative flex items-center gap-2 rounded-[10px] transition-colors",
        compact ? "px-2 py-1.5" : "px-3 py-2.5",
        active && !dark && "bg-sqa-naranja/10 ring-1 ring-sqa-naranja/30",
        active && dark && "bg-sqa-naranja/[0.12]",
        !active && !dark && "hover:bg-muted",
        !active && dark && "hover:bg-white/[0.05]",
      )}
    >
      <Link
        href={`/chat/${session.id}` as never}
        className="flex min-w-0 flex-1 items-center gap-2.5"
        aria-current={active ? "page" : undefined}
      >
        <span
          className={cn(
            "hex-clip-flat flex shrink-0 items-center justify-center",
            compact ? "h-6 w-6" : "h-8 w-8",
            active
              ? "bg-sqa-naranja text-sqa-ink"
              : dark
                ? "bg-white/[0.06] text-white/70"
                : "bg-muted text-muted-foreground",
          )}
          aria-hidden
        >
          <Icon className={compact ? "h-3 w-3" : "h-3.5 w-3.5"} />
        </span>
        <div className="min-w-0 flex-1">
          <div
            className={cn(
              "truncate font-display font-semibold",
              compact ? "text-[12.5px]" : "text-[13px]",
              dark ? "text-white" : "text-foreground",
            )}
          >
            {session.title}
          </div>
          <div
            className={cn(
              "flex items-center gap-1.5",
              compact ? "text-[10px]" : "text-[11px]",
              dark ? "text-white/55" : "text-muted-foreground",
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 shrink-0 rounded-full",
                STATUS_DOT_CLASSES[session.status],
              )}
              aria-label={STATUS_LABEL[session.status]}
            />
            <span className="truncate">
              {STATUS_LABEL[session.status]} · {updated}
            </span>
          </div>
        </div>
      </Link>
      {onDelete && (
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            "h-7 w-7 shrink-0 opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100",
            dark && "text-white/60 hover:bg-white/[0.08] hover:text-white",
          )}
          onClick={() => onDelete(session.id)}
          aria-label={`Eliminar sesión "${session.title}"`}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  );
}
