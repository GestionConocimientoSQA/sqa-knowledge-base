"use client";

import { useState } from "react";
import { Eye, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DocumentPreviewDialog } from "@/components/chat/document-preview-dialog";
import { iconForFile, extensionFromFilename } from "@/lib/files";
import type { DocumentArtifactPayload } from "@/types/agent";

interface DocumentArtifactCardProps {
  artifact: DocumentArtifactPayload;
}

/**
 * Card visual del documento generado por el agente.
 * Reemplaza el botón simple "FileDown" que tenía el MessageBubble inicial —
 * ahora con preview + download separados.
 */
export function DocumentArtifactCard({ artifact }: DocumentArtifactCardProps) {
  const [previewOpen, setPreviewOpen] = useState(false);
  const Icon = iconForFile(artifact.filename);
  const ext = extensionFromFilename(artifact.filename).toUpperCase() || "DOC";

  return (
    <>
      <div className="flex items-center gap-3 rounded-lg border border-border bg-card p-3 shadow-sm">
        <span
          className="hex-clip-flat flex h-10 w-10 shrink-0 items-center justify-center bg-sqa-naranja/15 text-sqa-naranja"
          aria-hidden
        >
          <Icon className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate font-display text-[13px] font-bold text-foreground">
            {artifact.filename}
          </div>
          <div className="font-mono text-[10.5px] text-muted-foreground">
            {ext} · generado por Aria
          </div>
        </div>
        <div className="flex shrink-0 gap-1.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPreviewOpen(true)}
            aria-label={`Vista previa de ${artifact.filename}`}
          >
            <Eye className="h-3.5 w-3.5" />
            Vista previa
          </Button>
          <Button variant="accent" size="sm" asChild>
            <a href={artifact.downloadUrl} download={artifact.filename}>
              <Download className="h-3.5 w-3.5" />
              Descargar
            </a>
          </Button>
        </div>
      </div>
      <DocumentPreviewDialog
        artifact={artifact}
        open={previewOpen}
        onOpenChange={setPreviewOpen}
      />
    </>
  );
}
