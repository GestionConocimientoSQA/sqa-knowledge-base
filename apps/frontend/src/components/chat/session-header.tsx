"use client";

import { PauseCircle, PlayCircle, ArrowLeft } from "lucide-react";
import { format } from "date-fns";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { MODE_COPY } from "@/lib/chat/mode-copy";
import type { AgentSession, SessionStatus } from "@/types/agent";

const STATUS_LABEL: Record<SessionStatus, string> = {
  active: "Activa",
  paused: "Pausada",
  completed: "Completada",
  abandoned: "Abandonada",
};

const STATUS_CLASSES: Record<SessionStatus, string> = {
  active: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  paused: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  completed: "bg-sqa-azul-medio-claro/15 text-sqa-azul-medio-claro",
  abandoned: "bg-muted text-muted-foreground",
};

interface SessionHeaderProps {
  session: AgentSession;
  onPause: () => void;
  onResume: () => void;
  pendingAction: boolean;
}

export function SessionHeader({
  session,
  onPause,
  onResume,
  pendingAction,
}: SessionHeaderProps) {
  const copy = MODE_COPY[session.mode];
  const Icon = copy.icon;
  const isActive = session.status === "active";
  const isPaused = session.status === "paused";

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border bg-card px-6 py-5">
      <div className="flex min-w-0 items-center gap-4">
        <Button variant="ghost" size="icon" asChild aria-label="Volver al selector">
          <Link href="/chat">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <span
          className="hex-clip-flat flex h-10 w-10 items-center justify-center bg-sqa-naranja/15 text-sqa-naranja"
          aria-hidden
        >
          <Icon className="h-4 w-4" />
        </span>
        <div className="min-w-0">
          <div className="eyebrow text-[10px] text-muted-foreground">
            Modo {copy.letter} · {copy.short}
          </div>
          <h2 className="truncate font-display text-lg font-extrabold tracking-tight text-foreground">
            {session.title}
          </h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Creada el {format(new Date(session.createdAt), "dd MMM yyyy HH:mm")}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Badge
          variant="outline"
          className={cn("font-display", STATUS_CLASSES[session.status])}
        >
          {STATUS_LABEL[session.status]}
        </Badge>
        {isActive && (
          <Button
            variant="outline"
            size="sm"
            onClick={onPause}
            disabled={pendingAction}
          >
            <PauseCircle className="h-4 w-4" />
            Pausar
          </Button>
        )}
        {isPaused && (
          <Button
            variant="accent"
            size="sm"
            onClick={onResume}
            disabled={pendingAction}
          >
            <PlayCircle className="h-4 w-4" />
            Reanudar
          </Button>
        )}
      </div>
    </header>
  );
}
