/**
 * Adaptador de persistencia local para sesiones del agente (stub Fase 6.1).
 *
 * Encapsula `localStorage` detrás de funciones puras. El día que arranque el
 * backend real (Fase 2), las funciones públicas de `sessions.ts` cambian su
 * cuerpo para invocar al API con ky; este módulo se elimina sin afectar a la
 * UI (DIP — la UI nunca importa este archivo).
 */
import type { AgentSession } from "@/types/agent";

const STORAGE_KEY = "sqa-kb.sessions.v1";

function hasWindow(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function readAll(): AgentSession[] {
  if (!hasWindow()) return [];
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as AgentSession[]) : [];
  } catch {
    return [];
  }
}

function writeAll(sessions: AgentSession[]): void {
  if (!hasWindow()) return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export const sessionsStore = {
  list(): AgentSession[] {
    return readAll();
  },
  get(id: string): AgentSession | null {
    return readAll().find((s) => s.id === id) ?? null;
  },
  upsert(session: AgentSession): AgentSession {
    const all = readAll();
    const idx = all.findIndex((s) => s.id === session.id);
    if (idx === -1) {
      all.push(session);
    } else {
      all[idx] = session;
    }
    writeAll(all);
    return session;
  },
  remove(id: string): void {
    writeAll(readAll().filter((s) => s.id !== id));
  },
  clear(): void {
    if (!hasWindow()) return;
    window.localStorage.removeItem(STORAGE_KEY);
  },
};
