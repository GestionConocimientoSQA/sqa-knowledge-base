"use client";

/**
 * Detalle de un item de la cola de ingesta (Fase 8.4).
 *
 * Muestra metadata + preview placeholder + formulario de trazabilidad si el
 * item está en estado revisable. Permite aprobar (con TraceabilityForm) o
 * rechazar (prompt simple). Tras aprobar/rechazar redirige a /ingestion.
 *
 * Gating: solo `isAdmin` (Owner / GK Lead). En Fase 9 esto se reemplaza por
 * permission check basado en membership del proyecto activo.
 */
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft, ChevronRight, FileText, Shield, XCircle } from "lucide-react";
import { toast } from "sonner";

import { IngestionStatusBadge } from "@/components/ingestion/status-badge";
import { TraceabilityForm } from "@/components/ingestion/traceability-form";
import { EmptyState } from "@/components/shared/empty-state";
import { PageContainer } from "@/components/shared/page-container";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth/auth-provider";
import { formatBytes, iconForFile } from "@/lib/files";
import {
  useApproveIngestion,
  useIngestionItem,
  useRejectIngestion,
} from "@/lib/hooks/use-ingestion";
import { categoryLabel, docTypeLabel } from "@/lib/taxonomy";
import type { IngestionItem, TraceabilityInput } from "@/types/domain";

function isRevisable(item: IngestionItem): boolean {
  return (
    item.status === "pendiente-metadata" ||
    item.status === "listo" ||
    item.status === "en-revision"
  );
}

function askRejectionReason(): string | null {
  if (typeof window === "undefined") return null;
  const reason = window.prompt("Motivo del rechazo:");
  if (reason === null) return null;
  const trimmed = reason.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export default function IngestionDetailPage() {
  const router = useRouter();
  const params = useParams<{ itemId: string }>();
  const itemId = params?.itemId;
  const { user } = useAuth();

  const { data: item, isLoading, isError, error } = useIngestionItem(itemId);
  const approve = useApproveIngestion();
  const reject = useRejectIngestion();

  if (!user?.isAdmin) {
    return (
      <PageContainer>
        <EmptyState
          icon={Shield}
          title="Acceso restringido"
          description="El detalle de ingesta está disponible solo para Owner de carpeta y GK Lead."
        />
      </PageContainer>
    );
  }

  if (isLoading) {
    return (
      <PageContainer>
        <Skeleton className="mb-3 h-6 w-1/3" />
        <Skeleton className="mb-6 h-10 w-2/3" />
        <Skeleton className="h-48 w-full" />
      </PageContainer>
    );
  }

  if (isError || !item) {
    return (
      <PageContainer>
        <EmptyState
          icon={FileText}
          title="Item no encontrado"
          description={
            error instanceof Error
              ? error.message
              : "No pudimos cargar el detalle del item."
          }
          action={
            <Button asChild variant="outline">
              <Link href={"/ingestion" as never}>
                <ArrowLeft className="h-4 w-4" />
                Volver a la cola
              </Link>
            </Button>
          }
        />
      </PageContainer>
    );
  }

  const FileIcon = iconForFile(item.filename);
  const revisable = isRevisable(item);

  const handleApprove = (input: TraceabilityInput) => {
    approve.mutate(
      { itemId: item.id, traceability: input },
      {
        onSuccess: () => {
          toast.success("Item aprobado e ingresado al pipeline de indexado.");
          router.push("/ingestion");
        },
        onError: (err) =>
          toast.error(
            err instanceof Error
              ? err.message
              : "No se pudo aprobar el item.",
          ),
      },
    );
  };

  const handleReject = () => {
    const reason = askRejectionReason();
    if (!reason) return;
    reject.mutate(
      { itemId: item.id, reason },
      {
        onSuccess: () => {
          toast.success("Item rechazado.");
          router.push("/ingestion");
        },
        onError: (err) =>
          toast.error(
            err instanceof Error
              ? err.message
              : "No se pudo rechazar el item.",
          ),
      },
    );
  };

  return (
    <PageContainer>
      <nav
        aria-label="Migas de pan"
        className="mb-4 flex items-center gap-1 text-sm text-muted-foreground"
      >
        <Link href={"/ingestion" as never} className="hover:text-foreground">
          Cola de ingesta
        </Link>
        <ChevronRight className="h-4 w-4" aria-hidden />
        <span className="truncate text-foreground">{item.filename}</span>
      </nav>

      <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <FileIcon className="h-8 w-8 text-muted-foreground" aria-hidden />
          <div>
            <h2 className="font-display text-xl font-extrabold">
              {item.filename}
            </h2>
            <p className="text-sm text-muted-foreground">
              {formatBytes(item.sizeBytes)}
              {item.paginas > 0 ? ` · ${item.paginas} páginas` : ""}
            </p>
          </div>
        </div>
        <IngestionStatusBadge status={item.status} />
      </header>

      <section
        aria-labelledby="meta-heading"
        className="mb-6 rounded-lg border border-border bg-card p-5"
      >
        <h3 id="meta-heading" className="mb-3 font-display text-base font-bold">
          Metadata sugerida
        </h3>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase text-muted-foreground">
              Carpeta sugerida
            </dt>
            <dd>
              {item.carpetaSugerida
                ? `${item.carpetaSugerida} — ${categoryLabel(item.carpetaSugerida)}`
                : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-muted-foreground">
              Tipo sugerido
            </dt>
            <dd>
              {item.tipoSugerido
                ? `${item.tipoSugerido} — ${docTypeLabel(item.tipoSugerido)}`
                : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-muted-foreground">
              Subido
            </dt>
            <dd title={item.uploadedAt}>
              {new Date(item.uploadedAt).toLocaleString("es-AR")}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-muted-foreground">
              Fuente original
            </dt>
            <dd>{item.fuenteOriginal || "—"}</dd>
          </div>
        </dl>
        {item.errorDetail && (
          <p
            role="alert"
            className="mt-3 rounded-md border border-error/40 bg-error/5 px-3 py-2 text-sm text-error"
          >
            {item.errorDetail}
          </p>
        )}
      </section>

      <section
        aria-labelledby="preview-heading"
        className="mb-6 rounded-lg border border-dashed border-border bg-muted/30 p-8 text-center"
        data-testid="preview-placeholder"
      >
        <h3 id="preview-heading" className="font-display text-base font-bold">
          Vista previa del documento
        </h3>
        <p className="mt-2 text-sm text-muted-foreground">
          La vista previa nativa de docx/pptx/pdf/xlsx llega en Fase 10
          (hardening). Por ahora, descargá el archivo desde Blob para validarlo
          (path: <span className="font-mono">{item.blobPath ?? "—"}</span>).
        </p>
      </section>

      {revisable && (
        <section aria-labelledby="trace-heading">
          <h3
            id="trace-heading"
            className="mb-3 font-display text-base font-bold"
          >
            Trazabilidad para aprobar
          </h3>
          <TraceabilityForm
            item={item}
            approverName={user.name}
            isSubmitting={approve.isPending}
            onSubmit={handleApprove}
            onCancel={() => router.push("/ingestion")}
          />
          <div className="mt-3 flex justify-end">
            <Button
              type="button"
              variant="ghost"
              disabled={reject.isPending}
              onClick={handleReject}
            >
              <XCircle className="h-4 w-4" aria-hidden />
              Rechazar item
            </Button>
          </div>
        </section>
      )}

      {!revisable && (
        <section
          aria-labelledby="closed-heading"
          className="rounded-lg border border-border bg-card p-5"
        >
          <h3
            id="closed-heading"
            className="mb-2 font-display text-base font-bold"
          >
            Item cerrado
          </h3>
          <p className="text-sm text-muted-foreground">
            Este item ya fue {item.status === "rechazado" ? "rechazado" : "aprobado e indexado"}.
            {item.aprobadorName ? ` Aprobador: ${item.aprobadorName}.` : ""}
            {item.fechaAprobacion ? ` Fecha: ${item.fechaAprobacion}.` : ""}
          </p>
        </section>
      )}
    </PageContainer>
  );
}
