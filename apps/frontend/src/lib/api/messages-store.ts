/**
 * Adaptador de persistencia local para mensajes del agente (stub Fase 6.5).
 *
 * Storage separado del de sesiones porque el listado del sidebar solo
 * necesita summaries — cargar todos los mensajes al listar sesiones inflaría
 * el bundle inicial. Cuando llegue el backend real (Fase 2), este módulo se
 * elimina y `messages.ts` consulta `/api/v1/sessions/{id}/messages` con cursor.
 */
import type { AgentMessage } from "@/types/agent";

const STORAGE_KEY = "sqa-kb.messages.v1";

type MessagesStorage = Record<string, AgentMessage[]>;

function hasWindow(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function readAll(): MessagesStorage {
  if (!hasWindow()) return {};
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === "object" ? (parsed as MessagesStorage) : {};
  } catch {
    return {};
  }
}

function writeAll(data: MessagesStorage): void {
  if (!hasWindow()) return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export const messagesStore = {
  get(sessionId: string): AgentMessage[] {
    return readAll()[sessionId] ?? [];
  },
  save(sessionId: string, messages: AgentMessage[]): void {
    const all = readAll();
    all[sessionId] = messages;
    writeAll(all);
  },
  remove(sessionId: string): void {
    const all = readAll();
    delete all[sessionId];
    writeAll(all);
  },
  clear(): void {
    if (!hasWindow()) return;
    window.localStorage.removeItem(STORAGE_KEY);
  },
};
