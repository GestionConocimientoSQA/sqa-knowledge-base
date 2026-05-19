/**
 * Adaptador local para metadata de attachments (stub Fase 6.6).
 *
 * Solo metadata — el blob real no se persiste (localStorage no aguanta
 * archivos grandes y blobs serializados rompen el patrón). En el backend
 * real (Fase 1) el blob vive en Azure Blob Storage y aquí solo guardamos
 * el handle.
 */
import type { AttachmentMetadata } from "@/types/agent";

const STORAGE_KEY = "sqa-kb.attachments.v1";

type AttachmentsStorage = Record<string, AttachmentMetadata[]>;

function hasWindow(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function readAll(): AttachmentsStorage {
  if (!hasWindow()) return {};
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === "object"
      ? (parsed as AttachmentsStorage)
      : {};
  } catch {
    return {};
  }
}

function writeAll(data: AttachmentsStorage): void {
  if (!hasWindow()) return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export const attachmentsStore = {
  list(sessionId: string): AttachmentMetadata[] {
    return readAll()[sessionId] ?? [];
  },
  upsert(meta: AttachmentMetadata): AttachmentMetadata {
    const all = readAll();
    const current = all[meta.sessionId] ?? [];
    const idx = current.findIndex((a) => a.id === meta.id);
    if (idx === -1) current.push(meta);
    else current[idx] = meta;
    all[meta.sessionId] = current;
    writeAll(all);
    return meta;
  },
  remove(sessionId: string, attachmentId: string): void {
    const all = readAll();
    const current = all[sessionId] ?? [];
    all[sessionId] = current.filter((a) => a.id !== attachmentId);
    writeAll(all);
  },
  removeSession(sessionId: string): void {
    const all = readAll();
    delete all[sessionId];
    writeAll(all);
  },
  clear(): void {
    if (!hasWindow()) return;
    window.localStorage.removeItem(STORAGE_KEY);
  },
};
