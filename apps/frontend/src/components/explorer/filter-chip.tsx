"use client";

import { cn } from "@/lib/utils";

interface FilterChipProps {
  label: string;
  /** Texto secundario opcional (ej: nombre largo de la categoría). */
  sub?: string;
  active: boolean;
  onClick: () => void;
  /** Identifica el filtro semánticamente para lectores de pantalla. */
  ariaLabel?: string;
  /** True ⇒ render `label` con `font-mono` (códigos cortos como `PROC`).
   * Default `true` para back-compat con carpetas. Tipos lo pasan en
   * `false` para mostrar el nombre completo legible. */
  monospaceLabel?: boolean;
  className?: string;
}

/**
 * Chip toggleable usado en `FilterBar` para representar opciones de
 * filtro (carpetas, tipos, estados). Visualmente sigue la paleta SQA
 * — naranja con outline cuando está activo.
 */
export function FilterChip({
  label,
  sub,
  active,
  onClick,
  ariaLabel,
  monospaceLabel = true,
  className,
}: FilterChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      aria-label={ariaLabel ?? label}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12px] font-display font-semibold transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        active
          ? "border-sqa-naranja bg-sqa-naranja/15 text-foreground"
          : "border-border bg-card text-muted-foreground hover:border-sqa-naranja/40 hover:text-foreground",
        className,
      )}
    >
      <span className={monospaceLabel ? "font-mono" : undefined}>{label}</span>
      {sub && <span className="text-muted-foreground">{sub}</span>}
    </button>
  );
}
