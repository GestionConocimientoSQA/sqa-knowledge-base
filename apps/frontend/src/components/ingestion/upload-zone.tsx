"use client";

import { useCallback, useRef, useState, type ChangeEvent } from "react";
import { CheckCircle2, FileUp, Loader2, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { uploadIngestion } from "@/lib/api/ingestion";
import { formatBytes, iconForFile } from "@/lib/files";
import { useFileDropZone } from "@/lib/hooks/use-file-drop-zone";
import {
  SUPPORTED_EXTENSIONS,
  validateIngestionFile,
} from "@/lib/ingestion-validation";
import { cn } from "@/lib/utils";
import type { IngestionItem } from "@/types/domain";

type UploadStatus = "uploading" | "done" | "error";

interface UploadEntry {
  id: string;
  filename: string;
  sizeBytes: number;
  status: UploadStatus;
  error?: string;
}

interface UploadZoneProps {
  /** Se invoca cuando un archivo se sube con éxito — el padre refresca la cola. */
  onUploaded?: (item: IngestionItem) => void;
}

const ACCEPT = SUPPORTED_EXTENSIONS.map((e) => `.${e}`).join(",");

/**
 * Zona de carga de documentos a la cola de ingesta (modo C).
 *
 * Soporta drag & drop (vía `useFileDropZone`) + file picker. Valida cada
 * archivo en el cliente (formato + tamaño) antes de subirlo y muestra el
 * progreso/estado por archivo. La validación real la repite el backend.
 */
export function UploadZone({ onUploaded }: UploadZoneProps) {
  const zoneRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [entries, setEntries] = useState<UploadEntry[]>([]);

  const handleFiles = useCallback(
    (files: File[]) => {
      for (const file of files) {
        const entryId = `${file.name}-${Date.now()}-${Math.random()}`;
        const validation = validateIngestionFile(file);
        if (!validation.ok) {
          setEntries((prev) => [
            {
              id: entryId,
              filename: file.name,
              sizeBytes: file.size,
              status: "error",
              error: validation.error,
            },
            ...prev,
          ]);
          continue;
        }
        setEntries((prev) => [
          {
            id: entryId,
            filename: file.name,
            sizeBytes: file.size,
            status: "uploading",
          },
          ...prev,
        ]);
        void uploadIngestion(file)
          .then((item) => {
            setEntries((prev) =>
              prev.map((e) =>
                e.id === entryId ? { ...e, status: "done" } : e,
              ),
            );
            onUploaded?.(item);
          })
          .catch((err: unknown) => {
            setEntries((prev) =>
              prev.map((e) =>
                e.id === entryId
                  ? {
                      ...e,
                      status: "error",
                      error: err instanceof Error ? err.message : "Error al subir",
                    }
                  : e,
              ),
            );
          });
      }
    },
    [onUploaded],
  );

  const { isDragging } = useFileDropZone({ ref: zoneRef, onFiles: handleFiles });

  const onPick = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) handleFiles(Array.from(files));
    event.target.value = "";
  };

  return (
    <div className="space-y-3">
      <div
        ref={zoneRef}
        data-testid="upload-zone"
        className={cn(
          "flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-8 text-center transition-colors",
          isDragging
            ? "border-brand bg-brand/5"
            : "border-border bg-muted/30",
        )}
      >
        <FileUp className="h-8 w-8 text-muted-foreground" aria-hidden />
        <div>
          <p className="font-medium">Arrastrá documentos aquí o</p>
          <p className="text-sm text-muted-foreground">
            Formatos: {SUPPORTED_EXTENSIONS.join(", ")} · máx 10 MB
          </p>
        </div>
        <Button type="button" onClick={() => inputRef.current?.click()}>
          Seleccionar archivos
        </Button>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          accept={ACCEPT}
          onChange={onPick}
          aria-label="Seleccionar archivos para ingesta"
        />
      </div>

      {entries.length > 0 && (
        <ul className="space-y-2" aria-label="Archivos en carga">
          {entries.map((entry) => {
            const Icon = iconForFile(entry.filename);
            return (
              <li
                key={entry.id}
                className="flex items-center gap-3 rounded-md border border-border bg-card px-3 py-2 text-sm"
              >
                <Icon className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{entry.filename}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatBytes(entry.sizeBytes)}
                    {entry.error ? ` · ${entry.error}` : ""}
                  </p>
                </div>
                <StatusIcon status={entry.status} />
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: UploadStatus }) {
  if (status === "uploading") {
    return (
      <Loader2
        className="h-4 w-4 shrink-0 animate-spin text-muted-foreground"
        aria-label="Subiendo"
      />
    );
  }
  if (status === "done") {
    return (
      <CheckCircle2
        className="h-4 w-4 shrink-0 text-success"
        aria-label="Subido"
      />
    );
  }
  return <XCircle className="h-4 w-4 shrink-0 text-error" aria-label="Error" />;
}
