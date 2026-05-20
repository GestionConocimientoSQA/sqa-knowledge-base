"use client";

import { useId } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FilterChip } from "@/components/explorer/filter-chip";
import { DOC_TYPES, FOLDERS } from "@/lib/mocks/data";
import type {
  CategoryCode,
  DocStatus,
  DocTypeCode,
  DocumentSearchFilters,
  DocumentSortBy,
} from "@/types/domain";

interface FilterBarProps {
  filters: DocumentSearchFilters;
  sortBy: DocumentSortBy | undefined;
  activeFilterCount: number;
  onPatchFilters: (patch: Partial<DocumentSearchFilters>) => void;
  onSortChange: (sortBy: DocumentSortBy | undefined) => void;
  onClear: () => void;
}

const SORT_OPTIONS: { value: DocumentSortBy; label: string }[] = [
  { value: "relevance", label: "Relevancia" },
  { value: "date_desc", label: "Más recientes" },
  { value: "score_desc", label: "Mayor score" },
  { value: "citations_desc", label: "Más citados" },
];

const ESTADOS_VISIBLES: { code: DocStatus; label: string }[] = [
  { code: "vigente", label: "Vigente" },
  { code: "generado", label: "Generado" },
  { code: "en-revision", label: "En revisión" },
  { code: "obsoleto", label: "Obsoleto" },
];

/** Helper para toggle en multi-select inmutable. */
function toggleInArray<T>(arr: readonly T[] | undefined, item: T): T[] {
  const list = arr ?? [];
  return list.includes(item)
    ? list.filter((x) => x !== item)
    : [...list, item];
}

/**
 * Barra de filtros del Explorer. Mantiene visibilidad de los filtros
 * más usados (carpetas, tipos, estados, autoritativo, anonimizado,
 * score, sort). Fechas y `autorOid` se setean por URL — fuera de 7.2.
 */
export function FilterBar({
  filters,
  sortBy,
  activeFilterCount,
  onPatchFilters,
  onSortChange,
  onClear,
}: FilterBarProps) {
  const scoreId = useId();
  const sortId = useId();

  const carpetasActive = new Set<CategoryCode>(filters.carpetas ?? []);
  const tiposActive = new Set<DocTypeCode>(filters.tipos ?? []);
  const estadosActive = new Set<DocStatus>(filters.estados ?? []);

  return (
    <section
      aria-label="Filtros del catálogo"
      className="rounded-lg border border-border bg-card p-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-eyebrow eyebrow">Filtros</div>
        <div className="flex items-center gap-2">
          {activeFilterCount > 0 && (
            <>
              <span className="text-[11px] text-muted-foreground">
                {activeFilterCount} {activeFilterCount === 1 ? "filtro activo" : "filtros activos"}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onClear}
                aria-label="Limpiar todos los filtros"
              >
                <X className="h-3.5 w-3.5" />
                Limpiar
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Carpetas */}
      <fieldset className="mt-3">
        <legend className="mb-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
          Carpeta
        </legend>
        <div className="flex flex-wrap gap-1.5">
          {FOLDERS.map((f) => (
            <FilterChip
              key={f.code}
              label={f.code}
              sub={f.label}
              active={carpetasActive.has(f.code)}
              ariaLabel={`Carpeta ${f.label} (${f.code})`}
              onClick={() =>
                onPatchFilters({
                  carpetas: toggleInArray(filters.carpetas, f.code),
                })
              }
            />
          ))}
        </div>
      </fieldset>

      {/* Tipos */}
      <fieldset className="mt-3">
        <legend className="mb-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
          Tipo de documento
        </legend>
        <div className="flex flex-wrap gap-1.5">
          {DOC_TYPES.map((t) => (
            <FilterChip
              key={t.code}
              label={t.code}
              active={tiposActive.has(t.code)}
              ariaLabel={`Tipo ${t.label} (${t.code})`}
              onClick={() =>
                onPatchFilters({
                  tipos: toggleInArray(filters.tipos, t.code),
                })
              }
            />
          ))}
        </div>
      </fieldset>

      {/* Estados */}
      <fieldset className="mt-3">
        <legend className="mb-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
          Estado
        </legend>
        <div className="flex flex-wrap gap-1.5">
          {ESTADOS_VISIBLES.map((e) => (
            <FilterChip
              key={e.code}
              label={e.label}
              active={estadosActive.has(e.code)}
              ariaLabel={`Estado ${e.label}`}
              onClick={() =>
                onPatchFilters({
                  estados: toggleInArray(filters.estados, e.code),
                })
              }
            />
          ))}
        </div>
      </fieldset>

      {/* Toggles + score + sort en línea */}
      <div className="mt-4 flex flex-wrap items-end gap-4">
        <TriStateToggle
          legend="Autoritativo"
          value={filters.autoritativo}
          onChange={(v) => onPatchFilters({ autoritativo: v })}
        />
        <TriStateToggle
          legend="Anonimizado"
          value={filters.anonimizado}
          onChange={(v) => onPatchFilters({ anonimizado: v })}
        />

        <fieldset>
          <legend className="mb-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
            Score mínimo
          </legend>
          <div className="flex items-center gap-2">
            <input
              id={scoreId}
              type="range"
              min={1}
              max={5}
              step={0.1}
              value={filters.minScore ?? 1}
              onChange={(e) => {
                const n = Number.parseFloat(e.target.value);
                onPatchFilters({ minScore: n > 1 ? n : undefined });
              }}
              aria-label="Score mínimo"
              className="h-2 w-32 cursor-pointer appearance-none rounded-full bg-muted accent-sqa-naranja"
            />
            <span className="w-8 font-mono text-[12px] tabular-nums">
              {(filters.minScore ?? 1).toFixed(1)}
            </span>
          </div>
        </fieldset>

        <div className="ml-auto">
          <label
            htmlFor={sortId}
            className="mb-1.5 block text-[11px] uppercase tracking-wider text-muted-foreground"
          >
            Orden
          </label>
          <select
            id={sortId}
            value={sortBy ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              onSortChange(v === "" ? undefined : (v as DocumentSortBy));
            }}
            className="h-9 rounded-md border border-input bg-card px-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Ordenar por"
          >
            <option value="">Por defecto</option>
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </section>
  );
}

interface TriStateToggleProps {
  legend: string;
  value: boolean | undefined;
  onChange: (value: boolean | undefined) => void;
}

/**
 * Toggle de 3 estados (undefined → true → false → undefined). Patrón
 * útil para filtros booleanos opcionales — el undefined significa
 * "ignorar este filtro" y mostrar ambos casos.
 */
function TriStateToggle({ legend, value, onChange }: TriStateToggleProps) {
  return (
    <fieldset>
      <legend className="mb-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
        {legend}
      </legend>
      <div className="flex gap-1" role="radiogroup" aria-label={legend}>
        <FilterChip
          label="Todos"
          active={value === undefined}
          onClick={() => onChange(undefined)}
        />
        <FilterChip
          label="Sí"
          active={value === true}
          onClick={() => onChange(true)}
        />
        <FilterChip
          label="No"
          active={value === false}
          onClick={() => onChange(false)}
        />
      </div>
    </fieldset>
  );
}
