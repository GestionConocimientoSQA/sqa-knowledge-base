"use client";

import { Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { ORDERED_MODES, MODE_COPY } from "@/lib/chat/mode-copy";
import type { SessionMode } from "@/types/domain";
import type { SessionStatus } from "@/types/agent";

const STATUS_OPTIONS: { value: SessionStatus; label: string }[] = [
  { value: "active", label: "Activa" },
  { value: "paused", label: "Pausada" },
  { value: "completed", label: "Completada" },
];

export interface SessionFiltersState {
  search: string;
  mode: SessionMode | null;
  status: SessionStatus | null;
}

interface SessionFiltersProps {
  value: SessionFiltersState;
  onChange: (next: SessionFiltersState) => void;
}

/**
 * Filtros del panel de historial: search por título, chip group de modo,
 * chip group de status. Estado controlado por el padre — SRP, sin estado
 * interno que se desincronice.
 */
export function SessionFilters({ value, onChange }: SessionFiltersProps) {
  const hasActiveFilters =
    value.search.length > 0 || value.mode !== null || value.status !== null;

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden
        />
        <Input
          type="search"
          value={value.search}
          onChange={(e) => onChange({ ...value, search: e.target.value })}
          placeholder="Buscar por título..."
          className="pl-9"
          aria-label="Buscar sesiones por título"
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="font-display text-[10.5px] font-extrabold uppercase tracking-wider text-muted-foreground">
          Modo
        </span>
        <FilterChip
          label="Todos"
          active={value.mode === null}
          onClick={() => onChange({ ...value, mode: null })}
        />
        {ORDERED_MODES.map((mode) => (
          <FilterChip
            key={mode}
            label={MODE_COPY[mode].short}
            active={value.mode === mode}
            onClick={() => onChange({ ...value, mode })}
          />
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="font-display text-[10.5px] font-extrabold uppercase tracking-wider text-muted-foreground">
          Estado
        </span>
        <FilterChip
          label="Todos"
          active={value.status === null}
          onClick={() => onChange({ ...value, status: null })}
        />
        {STATUS_OPTIONS.map((opt) => (
          <FilterChip
            key={opt.value}
            label={opt.label}
            active={value.status === opt.value}
            onClick={() => onChange({ ...value, status: opt.value })}
          />
        ))}
      </div>

      {hasActiveFilters && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => onChange({ search: "", mode: null, status: null })}
          className="text-muted-foreground"
        >
          <X className="h-3.5 w-3.5" />
          Limpiar filtros
        </Button>
      )}
    </div>
  );
}

interface FilterChipProps {
  label: string;
  active: boolean;
  onClick: () => void;
}

function FilterChip({ label, active, onClick }: FilterChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-2.5 py-0.5 font-display text-[11px] font-semibold transition-colors",
        active
          ? "border-sqa-naranja bg-sqa-naranja/15 text-sqa-naranja"
          : "border-border bg-card text-muted-foreground hover:border-muted-foreground hover:text-foreground",
      )}
      aria-pressed={active}
    >
      {label}
    </button>
  );
}
