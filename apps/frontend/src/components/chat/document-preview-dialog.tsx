"use client";

import { Download, FileSearch } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { iconForFile, extensionFromFilename } from "@/lib/files";
import type { DocumentArtifactPayload } from "@/types/agent";

interface DocumentPreviewDialogProps {
  artifact: DocumentArtifactPayload | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Sheet con preview stub de documentos generados.
 *
 * En sub-fase 6.6 los artifacts son URLs ficticias (`/mock/downloads/...`) que
 * no resuelven a contenido real. Mostramos metadata + un placeholder que
 * explica el flujo real. Cuando llegue Fase 4 (generadores DOCX/PPTX/etc),
 * este componente embeberá un viewer real (object URL del blob descargado).
 */
export function DocumentPreviewDialog({
  artifact,
  open,
  onOpenChange,
}: DocumentPreviewDialogProps) {
  if (!artifact) return null;
  const Icon = iconForFile(artifact.filename);
  const ext = extensionFromFilename(artifact.filename).toUpperCase() || "DOC";

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-2xl sm:px-8"
      >
        <SheetHeader>
          <div className="flex items-center gap-3">
            <span
              className="hex-clip-flat flex h-10 w-10 items-center justify-center bg-sqa-naranja/15 text-sqa-naranja"
              aria-hidden
            >
              <Icon className="h-4 w-4" />
            </span>
            <div className="min-w-0 flex-1">
              <SheetTitle className="truncate">{artifact.filename}</SheetTitle>
              <SheetDescription className="font-mono text-[11px]">
                {ext} · {artifact.blobPath}
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div className="mt-6 flex h-[calc(100vh-260px)] flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-border bg-muted/30 p-8 text-center">
          <FileSearch className="h-12 w-12 text-muted-foreground" aria-hidden />
          <div className="space-y-1.5">
            <h3 className="font-display text-lg font-bold text-foreground">
              Vista previa pendiente
            </h3>
            <p className="max-w-md text-sm text-muted-foreground">
              La generación real del documento llega en Fase 4 (generadores
              docx / pptx / pdf con branding SQA). Mientras tanto, podés
              descargar el archivo simulado.
            </p>
          </div>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 rounded-lg bg-card p-4 text-left text-[12px]">
            <dt className="font-semibold text-muted-foreground">Document ID</dt>
            <dd className="break-all font-mono">{artifact.documentId}</dd>
            <dt className="font-semibold text-muted-foreground">Blob path</dt>
            <dd className="break-all font-mono">{artifact.blobPath}</dd>
          </dl>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cerrar
          </Button>
          <Button variant="accent" asChild>
            <a href={artifact.downloadUrl} download={artifact.filename}>
              <Download className="h-4 w-4" />
              Descargar
            </a>
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
