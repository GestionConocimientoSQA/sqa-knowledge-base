/**
 * Badge visual por estado de ingesta (Fase 8.3).
 *
 * Espejo de los 6 estados del backend (`IngestionStatus`). Mapea cada estado
 * a un variant + label en español. SRP: solo se encarga de presentación.
 */
import { Badge } from "@/components/ui/badge";
import type { IngestionStatus } from "@/types/domain";

interface StatusMeta {
  label: string;
  variant: "default" | "secondary" | "destructive" | "outline" | "accent" | "authoritative";
}

const STATUS_META: Record<IngestionStatus, StatusMeta> = {
  "pendiente-metadata": { label: "Pendiente metadata", variant: "secondary" },
  listo: { label: "Listo para revisar", variant: "outline" },
  "en-revision": { label: "En revisión", variant: "accent" },
  aprobado: { label: "Aprobado", variant: "authoritative" },
  indexado: { label: "Indexado", variant: "authoritative" },
  rechazado: { label: "Rechazado", variant: "destructive" },
};

export function IngestionStatusBadge({ status }: { status: IngestionStatus }) {
  const meta = STATUS_META[status];
  return (
    <Badge variant={meta.variant} data-status={status} aria-label={`Estado: ${meta.label}`}>
      {meta.label}
    </Badge>
  );
}
