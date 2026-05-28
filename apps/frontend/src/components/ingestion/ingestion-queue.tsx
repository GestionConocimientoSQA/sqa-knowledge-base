"use client";

/**
 * Cola filtrada por estado(s) (Fase 8.3).
 *
 * Compone `useIngestionList` + `IngestionItemRow` y maneja los 4 estados de
 * UI obligatorios del §19 del ROADMAP: loading / error / empty / populated.
 * Las mutaciones (classify/reject) se disparan acá porque dependen de la
 * misma key de cache; aprobar vive en `/ingestion/[id]` (form completo de
 * trazabilidad).
 */
import { Inbox } from "lucide-react";
import { toast } from "sonner";

import { IngestionItemRow } from "@/components/ingestion/ingestion-item-row";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useClassifyIngestion,
  useIngestionList,
  useRejectIngestion,
} from "@/lib/hooks/use-ingestion";
import type { IngestionStatus } from "@/types/domain";

interface IngestionQueueProps {
  statuses: IngestionStatus[];
  emptyMessage: string;
}

/**
 * Prompt simple para capturar motivo de rechazo. En Fase 8.4 se reemplaza por
 * un modal con textarea + validación; mientras tanto `window.prompt` es
 * suficiente para los 3 estados de pendiente/listo/en-revisión.
 */
function askRejectionReason(): string | null {
  if (typeof window === "undefined") return null;
  const reason = window.prompt(
    "Motivo del rechazo (se guarda en el ítem y el captador lo verá):",
  );
  if (reason === null) return null;
  const trimmed = reason.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function IngestionQueue({ statuses, emptyMessage }: IngestionQueueProps) {
  const { data, isLoading, isError, error } = useIngestionList(statuses);
  const classify = useClassifyIngestion();
  const reject = useRejectIngestion();

  const inFlight = new Set<string>();
  if (classify.isPending && classify.variables) inFlight.add(classify.variables);
  if (reject.isPending && reject.variables)
    inFlight.add(reject.variables.itemId);

  const handleClassify = (itemId: string) => {
    classify.mutate(itemId, {
      onSuccess: () => toast.success("Item clasificado y enviado a revisión."),
      onError: (err) =>
        toast.error(
          err instanceof Error ? err.message : "No se pudo clasificar el item.",
        ),
    });
  };

  const handleReject = (itemId: string) => {
    const reason = askRejectionReason();
    if (!reason) return;
    reject.mutate(
      { itemId, reason },
      {
        onSuccess: () => toast.success("Item rechazado."),
        onError: (err) =>
          toast.error(
            err instanceof Error ? err.message : "No se pudo rechazar el item.",
          ),
      },
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-2" aria-busy="true" aria-label="Cargando cola">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <EmptyState
        icon={Inbox}
        title="No se pudo cargar la cola"
        description={
          error instanceof Error ? error.message : "Error desconocido."
        }
      />
    );
  }

  const items = data ?? [];

  if (items.length === 0) {
    return <EmptyState icon={Inbox} title="Sin items" description={emptyMessage} />;
  }

  return (
    <ul
      className="space-y-2"
      aria-label="Items en cola de ingesta"
      data-testid="ingestion-queue"
    >
      {items.map((item) => (
        <IngestionItemRow
          key={item.id}
          item={item}
          onClassify={handleClassify}
          onReject={handleReject}
          isMutating={inFlight.has(item.id)}
        />
      ))}
    </ul>
  );
}
