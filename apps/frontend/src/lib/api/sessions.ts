/**
 * API pública de sesiones del agente.
 *
 * En Fase 6.1 las funciones operan contra `sessionsStore` (localStorage); en
 * Fase 1 cambian a HTTP contra `/api/v1/sessions/*` sin cambiar la firma. Por
 * eso devuelven `Promise` aun cuando la implementación local es sincrónica.
 *
 * Espejo del catálogo §15.3 del ROADMAP:
 *   POST   /sessions                       → createSession
 *   GET    /sessions                       → listSessions
 *   GET    /sessions/{id}                  → getSession
 *   DELETE /sessions/{id}                  → deleteSession
 *   POST   /sessions/{id}/pause            → pauseSession
 *   POST   /sessions/{id}/resume           → resumeSession
 *   GET    /sessions/{id}/messages         → getMessages
 */
import type {
  AgentMessage,
  AgentSession,
  AgentSessionSummary,
} from "@/types/agent";
import type { SessionMode } from "@/types/domain";
import { sessionsStore } from "@/lib/api/sessions-store";
import { messagesStore } from "@/lib/api/messages-store";
import { attachmentsStore } from "@/lib/api/attachments-store";

const STUB_DELAY_MS = 120;

function delay<T>(value: T, ms = STUB_DELAY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

function generateSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `ses-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

const DEFAULT_TITLES: Record<SessionMode, string> = {
  captura: "Nueva captura",
  consulta: "Nueva consulta",
  ingesta: "Nueva ingesta",
};

export interface CreateSessionInput {
  mode: SessionMode;
  ownerOid: string;
  title?: string;
}

export async function createSession(
  input: CreateSessionInput,
): Promise<AgentSession> {
  const now = new Date().toISOString();
  const session: AgentSession = {
    id: generateSessionId(),
    mode: input.mode,
    ownerOid: input.ownerOid,
    title: input.title?.trim() || DEFAULT_TITLES[input.mode],
    status: "active",
    createdAt: now,
    updatedAt: now,
    messageCount: 0,
    currentStage: null,
  };
  sessionsStore.upsert(session);
  return delay(session);
}

function toSummary(s: AgentSession): AgentSessionSummary {
  return {
    id: s.id,
    mode: s.mode,
    title: s.title,
    status: s.status,
    createdAt: s.createdAt,
    updatedAt: s.updatedAt,
    messageCount: s.messageCount,
    currentStage: s.currentStage,
  };
}

export interface ListSessionsFilter {
  ownerOid?: string;
  mode?: SessionMode;
  status?: AgentSession["status"];
}

export async function listSessions(
  filter: ListSessionsFilter = {},
): Promise<AgentSessionSummary[]> {
  const items = sessionsStore
    .list()
    .filter((s) =>
      filter.ownerOid ? s.ownerOid === filter.ownerOid : true,
    )
    .filter((s) => (filter.mode ? s.mode === filter.mode : true))
    .filter((s) => (filter.status ? s.status === filter.status : true))
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
    .map(toSummary);
  return delay(items);
}

export async function getSession(id: string): Promise<AgentSession | null> {
  return delay(sessionsStore.get(id));
}

export async function pauseSession(id: string): Promise<AgentSession | null> {
  const current = sessionsStore.get(id);
  if (!current) return delay(null);
  const updated: AgentSession = {
    ...current,
    status: "paused",
    updatedAt: new Date().toISOString(),
  };
  sessionsStore.upsert(updated);
  return delay(updated);
}

export async function resumeSession(id: string): Promise<AgentSession | null> {
  const current = sessionsStore.get(id);
  if (!current) return delay(null);
  const updated: AgentSession = {
    ...current,
    status: "active",
    updatedAt: new Date().toISOString(),
  };
  sessionsStore.upsert(updated);
  return delay(updated);
}

export async function deleteSession(id: string): Promise<void> {
  sessionsStore.remove(id);
  messagesStore.remove(id);
  attachmentsStore.removeSession(id);
  return delay(undefined);
}

/**
 * Restaura una sesión + sus mensajes — usado para undo de borrado accidental.
 * En el backend real (Fase 1) el borrado es soft (`status: "abandoned"`) y
 * undo será un endpoint dedicado; acá lo cubrimos volviendo a upsert.
 */
export async function restoreSession(
  session: AgentSession,
  messages: AgentMessage[],
): Promise<AgentSession> {
  sessionsStore.upsert(session);
  if (messages.length > 0) messagesStore.save(session.id, messages);
  return delay(session);
}

export async function getMessages(sessionId: string): Promise<AgentMessage[]> {
  return delay(messagesStore.get(sessionId));
}

/**
 * Persiste mensajes y mantiene en sync `messageCount` + `currentStage` +
 * `updatedAt` de la sesión. El caller filtra los mensajes en curso
 * (`status === "streaming"`) — solo se persiste estado terminal.
 */
export async function saveMessages(
  sessionId: string,
  messages: AgentMessage[],
): Promise<void> {
  messagesStore.save(sessionId, messages);
  const session = sessionsStore.get(sessionId);
  if (session) {
    const lastAgentWithStage = [...messages]
      .reverse()
      .find((m) => m.role === "agent" && m.stage !== null);
    sessionsStore.upsert({
      ...session,
      messageCount: messages.length,
      currentStage: lastAgentWithStage?.stage ?? session.currentStage,
      updatedAt: new Date().toISOString(),
    });
  }
  return delay(undefined);
}
