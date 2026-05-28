"use client";

/**
 * Row de un item de la cola de ingesta (Fase 8.3).
 *
 * Presenta metadata del archivo + estado actual + acciones contextuales según
 * el estado (clasificar / revisar / rechazar / sin acción). SRP: la lógica de
 * mutación vive en los hooks; este componente solo dispara callbacks.
 */
import Link from "next/link";
import { CheckCheck, Eye, Sparkles, XCircle } from "lucide-react";

import { IngestionStatusBadge } from "@/components/ingestion/status-badge";
import { Button } from "@/components/ui/button";
import { formatBytes, iconForFile } from "@/lib/files";
import { cn } from "@/lib/utils";
import type { IngestionItem } from "@/types/domain";

interface IngestionItemRowProps {
  item: IngestionItem;
  onClassify: (itemId: string) => void;
  onReject: (itemId: string) => void;
  /** True mientras alguna mutación sobre este item está en vuelo. */
  isMutating?: boolean;
}

/** ISO → "dd/mm/yyyy HH:mm". Toleramos timestamps mal formados sin crashear. */
function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function IngestionItemRow({
  item,
  onClassify,
  onReject,
  isMutating = false,
}: IngestionItemRowProps) {
  const Icon = iconForFile(item.filename);
  const canClassify =
    item.status === "pendiente-metadata" || item.status === "listo";
  const canApprove = item.status === "en-revision";
  const canReject =
    item.status === "pendiente-metadata" ||
    item.status === "listo" ||
    item.status === "en-revision";

  return (
    <li
      data-testid={`ingestion-row-${item.id}`}
      className="flex flex-col gap-3 rounded-md border border-border bg-card px-4 py-3 sm:flex-row sm:items-center"
    >
      <Icon
        className="h-5 w-5 shrink-0 text-muted-foreground"
        aria-hidden
      />

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate font-medium" title={item.filename}>
            {item.filename}
          </p>
          <IngestionStatusBadge status={item.status} />
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          {formatBytes(item.sizeBytes)}
          {item.paginas > 0 ? ` · ${item.paginas} pág.` : ""}
          {item.carpetaSugerida ? ` · ${item.carpetaSugerida}` : ""}
          {item.tipoSugerido ? `/${item.tipoSugerido}` : ""}
          {" · "}
          <span title={item.uploadedAt}>{formatTimestamp(item.uploadedAt)}</span>
        </p>
        {item.errorDetail && (
          <p className={cn("mt-1 text-xs text-error")} role="alert">
            {item.errorDetail}
          </p>
        )}
      </div>

      <div className="flex shrink-0 gap-2">
        {canClassify && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={isMutating}
            onClick={() => onClassify(item.id)}
            aria-label={`Clasificar ${item.filename}`}
          >
            <Sparkles className="h-4 w-4" aria-hidden />
            Clasificar
          </Button>
        )}
        {canApprove && (
          <Button asChild type="button" variant="default" size="sm">
            <Link
              href={`/ingestion/${item.id}` as never}
              aria-label={`Revisar y aprobar ${item.filename}`}
            >
              <CheckCheck className="h-4 w-4" aria-hidden />
              Revisar
            </Link>
          </Button>
        )}
        {canReject && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={isMutating}
            onClick={() => onReject(item.id)}
            aria-label={`Rechazar ${item.filename}`}
          >
            <XCircle className="h-4 w-4" aria-hidden />
            Rechazar
          </Button>
        )}
        {!canClassify && !canApprove && !canReject && (
          <Button asChild type="button" variant="ghost" size="sm">
            <Link
              href={`/ingestion/${item.id}` as never}
              aria-label={`Ver detalle de ${item.filename}`}
            >
              <Eye className="h-4 w-4" aria-hidden />
              Ver
            </Link>
          </Button>
        )}
      </div>
    </li>
  );
}
