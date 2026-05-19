"use client";

import { Target } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ScoringPayload } from "@/types/agent";

interface ScoringPanelProps {
  scoring: ScoringPayload;
}

interface Dimension {
  key: keyof Omit<ScoringPayload, "valueScore">;
  label: string;
}

const DIMENSIONS: Dimension[] = [
  { key: "specificity", label: "Especificidad" },
  { key: "depth", label: "Profundidad" },
  { key: "reusability", label: "Reutilizabilidad" },
  { key: "uniqueness", label: "Unicidad" },
];

function toneFromScore(score: number): string {
  if (score >= 4.0) return "text-emerald-600 dark:text-emerald-400";
  if (score >= 3.0) return "text-amber-600 dark:text-amber-400";
  return "text-rose-600 dark:text-rose-400";
}

/**
 * Panel de scoring de la captura. Muestra las 4 dimensiones (1-5) + value_score
 * agregado. El cálculo del agregado lo hace el backend (§13 ROADMAP); acá solo
 * lo renderizamos.
 */
export function ScoringPanel({ scoring }: ScoringPanelProps) {
  return (
    <section
      className="rounded-lg border border-border bg-card/80 p-3 shadow-sm"
      aria-label="Scoring de captura"
    >
      <header className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target className="h-3.5 w-3.5 text-sqa-naranja" aria-hidden />
          <div className="eyebrow text-[10px] text-muted-foreground">
            Scoring de captura
          </div>
        </div>
        <div className="flex items-baseline gap-1">
          <span
            className={cn(
              "font-display text-lg font-extrabold leading-none",
              toneFromScore(scoring.valueScore),
            )}
          >
            {scoring.valueScore.toFixed(1)}
          </span>
          <span className="text-[10px] text-muted-foreground">/ 5</span>
        </div>
      </header>
      <dl className="grid grid-cols-2 gap-2.5">
        {DIMENSIONS.map((dim) => {
          const value = scoring[dim.key];
          const widthPct = Math.round((value / 5) * 100);
          return (
            <div key={dim.key}>
              <div className="mb-1 flex items-center justify-between text-[11px]">
                <dt className="text-muted-foreground">{dim.label}</dt>
                <dd
                  className={cn(
                    "font-display font-bold",
                    toneFromScore(value),
                  )}
                >
                  {value.toFixed(1)}
                </dd>
              </div>
              <div
                className="h-1 overflow-hidden rounded-full bg-muted"
                role="progressbar"
                aria-valuenow={value}
                aria-valuemin={1}
                aria-valuemax={5}
              >
                <div
                  className="h-full rounded-full bg-sqa-azul-medio-claro"
                  style={{ width: `${widthPct}%` }}
                  aria-hidden
                />
              </div>
            </div>
          );
        })}
      </dl>
    </section>
  );
}
