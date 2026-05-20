"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface PaginationProps {
  page: number;
  limit: number;
  total: number;
  onPageChange: (page: number) => void;
  className?: string;
}

/**
 * Paginación simple prev/next con indicador "Página X de Y" y contador
 * de items. No incluye salto numérico — para catálogo de 45 docs y
 * límite de 20 alcanza con prev/next. Si más adelante necesitamos
 * jump-to-page, lo extendemos.
 */
export function Pagination({
  page,
  limit,
  total,
  onPageChange,
  className,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const safePage = Math.min(Math.max(1, page), totalPages);
  const hasPrev = safePage > 1;
  const hasNext = safePage < totalPages;

  const startItem = total === 0 ? 0 : (safePage - 1) * limit + 1;
  const endItem = Math.min(safePage * limit, total);

  return (
    <nav
      aria-label="Paginación"
      className={cn(
        "flex items-center justify-between border-t border-border pt-3",
        className,
      )}
    >
      <div className="text-[12px] text-muted-foreground">
        {total === 0 ? (
          <>0 resultados</>
        ) : (
          <>
            <span className="font-mono">{startItem}</span>–
            <span className="font-mono">{endItem}</span> de{" "}
            <span className="font-mono">{total}</span>
          </>
        )}
      </div>
      <div className="flex items-center gap-1.5">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => onPageChange(safePage - 1)}
          disabled={!hasPrev}
          aria-label="Página anterior"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Anterior
        </Button>
        <span className="px-2 text-[12px] text-muted-foreground" aria-live="polite">
          Página <span className="font-mono">{safePage}</span> de{" "}
          <span className="font-mono">{totalPages}</span>
        </span>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => onPageChange(safePage + 1)}
          disabled={!hasNext}
          aria-label="Página siguiente"
        >
          Siguiente
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </nav>
  );
}
