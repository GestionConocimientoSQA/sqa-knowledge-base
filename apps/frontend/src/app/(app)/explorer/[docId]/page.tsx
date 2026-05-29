"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, LibraryBig, BadgeCheck, EyeOff } from "lucide-react";
import { PageContainer } from "@/components/shared/page-container";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DocumentMetaPanel } from "@/components/explorer/document-meta-panel";
import { DocumentActionsBar } from "@/components/explorer/document-actions-bar";
import { DocumentPreviewPlaceholder } from "@/components/explorer/document-preview-placeholder";
import { IncomingCitationsPanel } from "@/components/explorer/incoming-citations-panel";
import { getDocumentDetail } from "@/lib/api/documents";
import { docTypeLabel } from "@/lib/taxonomy";

interface DocumentDetailPageProps {
  params: Promise<{ docId: string }>;
}

export default function DocumentDetailPage({ params }: DocumentDetailPageProps) {
  const { docId } = use(params);
  const router = useRouter();

  const { data: doc, isLoading, isError } = useQuery({
    queryKey: ["document-detail", docId],
    queryFn: () => getDocumentDetail(docId),
  });

  if (isLoading) {
    return (
      <PageContainer>
        <Skeleton className="mb-4 h-8 w-2/3" />
        <Skeleton className="mb-2 h-4 w-1/2" />
        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_360px]">
          <div className="space-y-4">
            <Skeleton className="h-72 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
          <Skeleton className="h-96 w-full" />
        </div>
      </PageContainer>
    );
  }

  if (isError) {
    return (
      <PageContainer>
        <EmptyState
          icon={LibraryBig}
          title="No se pudo cargar el documento"
          description="Reintentá la consulta en unos minutos."
          action={
            <Button variant="outline" onClick={() => router.refresh()}>
              Reintentar
            </Button>
          }
        />
      </PageContainer>
    );
  }

  if (!doc) {
    return (
      <PageContainer>
        <EmptyState
          icon={LibraryBig}
          title="Documento no encontrado"
          description={`No existe un documento con id "${docId}". Puede haber sido archivado o reemplazado.`}
          action={
            <Button asChild variant="outline">
              <Link href={"/explorer" as never}>
                <ArrowLeft className="h-4 w-4" />
                Volver al catálogo
              </Link>
            </Button>
          }
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      {/* Breadcrumb */}
      <div className="mb-3 flex items-center gap-2 text-[12px] text-muted-foreground">
        <Link
          href={"/explorer" as never}
          className="inline-flex items-center gap-1 hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
          Catálogo
        </Link>
        <span aria-hidden>/</span>
        <span className="font-mono">{doc.carpeta}</span>
        <span aria-hidden>·</span>
        <span title={doc.tipo}>{docTypeLabel(doc.tipo)}</span>
      </div>

      {/* Header */}
      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="font-mono">
              {doc.carpeta}
            </Badge>
            <Badge variant="secondary" title={doc.tipo}>
              {docTypeLabel(doc.tipo)}
            </Badge>
            {doc.autoritativo && (
              <Badge variant="authoritative">
                <BadgeCheck className="h-3 w-3" />
                Autoritativo
              </Badge>
            )}
            {doc.anonimizado && (
              <Badge variant="outline">
                <EyeOff className="h-3 w-3" />
                Anonimizado
              </Badge>
            )}
            {doc.estado !== "vigente" && (
              <Badge variant="outline" className="capitalize">
                {doc.estado.replace("-", " ")}
              </Badge>
            )}
          </div>
          <h1 className="mt-3 font-display text-2xl font-extrabold leading-tight">
            {doc.titulo}
          </h1>
          <div className="mt-1 font-mono text-[11px] text-muted-foreground">
            {doc.id}
          </div>
        </div>
        <DocumentActionsBar document={doc} />
      </div>

      {/* Layout 2-cols */}
      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <DocumentPreviewPlaceholder document={doc} />
          <DocumentMetaPanel document={doc} />
        </div>
        <aside aria-label="Citaciones recibidas">
          <IncomingCitationsPanel citations={doc.incomingCitations} />
        </aside>
      </div>
    </PageContainer>
  );
}
