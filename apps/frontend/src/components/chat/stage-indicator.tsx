"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SessionMode } from "@/types/domain";
import type { StageId } from "@/types/agent";

const CAPTURE_STAGES: { id: number; label: string }[] = [
  { id: 0, label: "Bienvenida" },
  { id: 1, label: "Identificación" },
  { id: 2, label: "Captura libre" },
  { id: 3, label: "Profundización" },
  { id: 4, label: "Validación" },
  { id: 5, label: "Generación" },
];

interface StageIndicatorProps {
  mode: SessionMode;
  currentStage: StageId | null;
}

/**
 * Indicador de etapa del agente.
 *  - Modo A: stepper horizontal de 6 puntos (ETAPAS 0-5)
 *  - Modo B/C: pill simple con la etapa única
 */
export function StageIndicator({ mode, currentStage }: StageIndicatorProps) {
  if (mode === "consulta" || mode === "ingesta") {
    const stageLetter = mode === "consulta" ? "C" : "I";
    const stageLabel =
      mode === "consulta" ? "Consultando base de conocimiento" : "Clasificando documento";
    const active = currentStage === stageLetter;
    return (
      <div className="border-b border-border bg-card px-6 py-3">
        <div className="flex items-center gap-2.5">
          <span
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-full font-display text-[11px] font-extrabold",
              active
                ? "bg-sqa-naranja text-sqa-ink"
                : "bg-muted text-muted-foreground",
            )}
            aria-hidden
          >
            {stageLetter}
          </span>
          <span className="font-display text-[13px] font-semibold text-foreground">
            {stageLabel}
          </span>
        </div>
      </div>
    );
  }

  const currentIndex =
    typeof currentStage === "number" ? currentStage : -1;

  return (
    <div className="border-b border-border bg-card px-6 py-3.5">
      <ol
        className="flex w-full items-center gap-1"
        aria-label="Etapas de la captura"
      >
        {CAPTURE_STAGES.map((stage, index) => {
          const completed = currentIndex > stage.id;
          const active = currentIndex === stage.id;
          const upcoming = !completed && !active;
          const lastItem = index === CAPTURE_STAGES.length - 1;
          return (
            <li
              key={stage.id}
              className="flex flex-1 items-center gap-2"
              aria-current={active ? "step" : undefined}
            >
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-full font-display text-[10px] font-extrabold transition-colors",
                    completed && "bg-sqa-azul-medio-claro text-white",
                    active && "bg-sqa-naranja text-sqa-ink ring-2 ring-sqa-naranja/30",
                    upcoming && "bg-muted text-muted-foreground",
                  )}
                  aria-hidden
                >
                  {completed ? <Check className="h-3 w-3" /> : stage.id}
                </span>
                <span
                  className={cn(
                    "hidden font-display text-[11px] font-semibold lg:inline",
                    completed && "text-foreground",
                    active && "text-foreground",
                    upcoming && "text-muted-foreground",
                  )}
                >
                  {stage.label}
                </span>
              </div>
              {!lastItem && (
                <span
                  className={cn(
                    "h-px flex-1 transition-colors",
                    completed ? "bg-sqa-azul-medio-claro" : "bg-border",
                  )}
                  aria-hidden
                />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
