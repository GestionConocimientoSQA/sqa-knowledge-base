/**
 * Validación cliente de archivos para la cola de ingesta (Fase 8.2).
 *
 * Espejo de los límites del backend (`IngestionService`):
 * - Tamaño máximo 10 MB.
 * - Formatos con extractor: docx, pptx, pdf, xlsx.
 *
 * Validar en el cliente evita un round-trip para archivos que el backend
 * rechazaría igual; el backend re-valida siempre (no confiamos en el
 * cliente como única defensa).
 */
import { extensionFromFilename } from "@/lib/files";

export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

export const SUPPORTED_EXTENSIONS = ["docx", "pptx", "pdf", "xlsx"] as const;

export interface FileValidation {
  ok: boolean;
  /** Mensaje de error en español si `ok=false`. */
  error?: string;
}

export function validateIngestionFile(file: File): FileValidation {
  const ext = extensionFromFilename(file.name);
  if (!ext) {
    return { ok: false, error: "El archivo no tiene extensión." };
  }
  if (!SUPPORTED_EXTENSIONS.includes(ext as (typeof SUPPORTED_EXTENSIONS)[number])) {
    return {
      ok: false,
      error: `Formato no soportado (.${ext}). Permitidos: ${SUPPORTED_EXTENSIONS.join(", ")}.`,
    };
  }
  if (file.size === 0) {
    return { ok: false, error: "El archivo está vacío." };
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return {
      ok: false,
      error: `Supera el límite de ${MAX_UPLOAD_BYTES / (1024 * 1024)} MB.`,
    };
  }
  return { ok: true };
}
