"use client";

import { Loader2, X, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { formatBytes, iconForFile } from "@/lib/files";
import type { AttachmentMetadata } from "@/types/agent";

interface AttachmentChipProps {
  attachment: AttachmentMetadata;
  onRemove?: (attachmentId: string) => void;
}

/**
 * Chip de archivo adjunto en el composer. Cambia visual según estado.
 * Solo se muestra mientras el archivo está pre-envío — al enviar el mensaje,
 * los attachments quedan asociados al user message y los chips se limpian.
 */
export function AttachmentChip({ attachment, onRemove }: AttachmentChipProps) {
  const Icon = iconForFile(attachment.filename);
  const isUploading = attachment.status === "uploading";
  const hasError = attachment.status === "error";

  return (
    <div
      className={cn(
        "group flex max-w-[260px] items-center gap-2 rounded-lg border px-2.5 py-1.5 text-[12px] transition-colors",
        hasError
          ? "border-destructive/40 bg-destructive/5 text-destructive"
          : "border-border bg-card",
      )}
    >
      <span
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-md",
          hasError
            ? "bg-destructive/10 text-destructive"
            : "bg-muted text-muted-foreground",
        )}
        aria-hidden
      >
        {isUploading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : hasError ? (
          <AlertTriangle className="h-3.5 w-3.5" />
        ) : (
          <Icon className="h-3.5 w-3.5" />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate font-display text-[12px] font-semibold">
          {attachment.filename}
        </div>
        <div className="font-mono text-[10px] text-muted-foreground">
          {isUploading
            ? `${attachment.progress}%`
            : hasError
              ? (attachment.error ?? "Error")
              : formatBytes(attachment.size)}
        </div>
        {isUploading && (
          <div className="mt-1 h-0.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-sqa-naranja transition-[width] duration-200"
              style={{ width: `${attachment.progress}%` }}
              aria-hidden
            />
          </div>
        )}
      </div>
      {onRemove && (
        <Button
          // `type="button"` evita que el chip submitea el form del composer
          // (default sería "submit" → enviaría un mensaje vacío).
          type="button"
          variant="ghost"
          size="icon"
          className="h-6 w-6 shrink-0 text-muted-foreground hover:text-foreground"
          onClick={() => onRemove(attachment.id)}
          aria-label={`Quitar ${attachment.filename}`}
          disabled={isUploading}
        >
          <X className="h-3 w-3" />
        </Button>
      )}
    </div>
  );
}
