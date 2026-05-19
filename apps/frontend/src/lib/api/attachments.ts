/**
 * API stub de attachments.
 *
 * Espejo de `POST /api/v1/sessions/{id}/attachments` del catálogo §15.3.
 * En Fase 1 cambia el cuerpo a un upload multipart con presigned URL hacia
 * Blob Storage; la firma pública (`uploadAttachment`, `listAttachments`,
 * `removeAttachment`) queda igual.
 */
import type { AttachmentMetadata, AttachmentStatus } from "@/types/agent";
import { attachmentsStore } from "@/lib/api/attachments-store";

const STUB_DELAY_MS = 80;
const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
const UPLOAD_TICK_MS = 220;
const UPLOAD_TICKS = 6;

export const ALLOWED_MIME_TYPES: ReadonlySet<string> = new Set([
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/msword",
  "application/vnd.ms-excel",
  "application/vnd.ms-powerpoint",
  "text/markdown",
  "text/plain",
  "text/csv",
]);

export const ALLOWED_EXTENSIONS = [
  ".pdf",
  ".docx",
  ".doc",
  ".pptx",
  ".ppt",
  ".xlsx",
  ".xls",
  ".md",
  ".txt",
  ".csv",
];

export class AttachmentValidationError extends Error {
  constructor(
    message: string,
    public readonly code: "size" | "mime",
  ) {
    super(message);
    this.name = "AttachmentValidationError";
  }
}

function delay<T>(value: T, ms = STUB_DELAY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

function generateId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `att-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function validateFile(file: File): void {
  if (file.size > MAX_SIZE_BYTES) {
    throw new AttachmentValidationError(
      `Archivo supera el máximo de ${MAX_SIZE_BYTES / 1024 / 1024} MB.`,
      "size",
    );
  }
  const ext = file.name.includes(".")
    ? `.${file.name.split(".").pop()!.toLowerCase()}`
    : "";
  const mimeOk = ALLOWED_MIME_TYPES.has(file.type);
  const extOk = ALLOWED_EXTENSIONS.includes(ext);
  if (!mimeOk && !extOk) {
    throw new AttachmentValidationError(
      `Tipo de archivo no permitido (${file.type || ext || "desconocido"}).`,
      "mime",
    );
  }
}

export interface UploadOptions {
  sessionId: string;
  file: File;
  onProgress?: (meta: AttachmentMetadata) => void;
  signal?: AbortSignal;
}

/**
 * Sube un archivo con progress simulado.
 * Cada tick actualiza el storage para que un re-fetch desde otro lugar vea
 * el avance. El callback `onProgress` recibe la metadata actualizada en cada
 * paso para que la UI re-renderice.
 */
export async function uploadAttachment(
  options: UploadOptions,
): Promise<AttachmentMetadata> {
  const { sessionId, file, onProgress, signal } = options;
  validateFile(file);

  const baseMeta: AttachmentMetadata = {
    id: generateId(),
    sessionId,
    filename: file.name,
    size: file.size,
    mimeType: file.type || "application/octet-stream",
    status: "uploading",
    progress: 0,
    uploadedAt: new Date().toISOString(),
  };

  attachmentsStore.upsert(baseMeta);
  onProgress?.(baseMeta);

  for (let i = 1; i <= UPLOAD_TICKS; i++) {
    if (signal?.aborted) {
      const aborted: AttachmentMetadata = {
        ...baseMeta,
        status: "error",
        progress: Math.round((i / UPLOAD_TICKS) * 100),
        error: "Carga cancelada",
      };
      attachmentsStore.upsert(aborted);
      onProgress?.(aborted);
      return aborted;
    }
    await delay(undefined, UPLOAD_TICK_MS);
    const tickStatus: AttachmentStatus = i === UPLOAD_TICKS ? "uploaded" : "uploading";
    const tick: AttachmentMetadata = {
      ...baseMeta,
      status: tickStatus,
      progress: Math.round((i / UPLOAD_TICKS) * 100),
      blobPath:
        tickStatus === "uploaded"
          ? `blob://attachments/${sessionId}/${baseMeta.id}-${file.name}`
          : undefined,
    };
    attachmentsStore.upsert(tick);
    onProgress?.(tick);
  }

  return attachmentsStore.list(sessionId).find((a) => a.id === baseMeta.id)!;
}

export async function listAttachments(
  sessionId: string,
): Promise<AttachmentMetadata[]> {
  return delay(attachmentsStore.list(sessionId));
}

export async function removeAttachment(
  sessionId: string,
  attachmentId: string,
): Promise<void> {
  attachmentsStore.remove(sessionId, attachmentId);
  return delay(undefined);
}
