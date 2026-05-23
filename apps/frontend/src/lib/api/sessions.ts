/**
 * API pública de sesiones del agente.
 *
 * Modo stub (sin `NEXT_PUBLIC_API_URL`): persiste en `sessionsStore`
 * (localStorage) para que la UI siga funcionando sin backend, como en
 * Fase 6.1.
 *
 * Modo backend real: opera contra `/sessions/*` (Fase 1B.5). El swap es
 * automático según `USE_REAL_API`. Los attachments y la persistencia de
 * mensajes siguen usando los stores locales — Fase 2 los moverá al backend
 * cuando se implemente el streaming SSE.
 *
 * Espejo del catálogo §15.3 del ROADMAP:
 *   POST   /sessions                       → createSession
 *   GET    /sessions                       → listSessions
 *   GET    /sessions/{id}                  → getSession
 *   PATCH  /sessions/{id}/status           → pauseSession / resumeSession
 *   DELETE /sessions/{id}                  → deleteSession
 *   GET    /sessions/{id}/messages         → getMessages
 */
import { api, USE_REAL_API } from "@/lib/api/client";
import { attachmentsStore } from "@/lib/api/attachments-store";
import { messagesStore } from "@/lib/api/messages-store";
import { sessionsStore } from "@/lib/api/sessions-store";
import type {
  AgentMessage,
  AgentSession,
  AgentSessionSummary,
} from "@/types/agent";
import type { SessionMode } from "@/types/domain";

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
  if (USE_REAL_API) {
    return api
      .post("sessions", {
        json: {
          mode: input.mode,
          title: input.title?.trim() || undefined,
        },
      })
      .json<AgentSession>();
  }
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
  if (USE_REAL_API) {
    // El backend filtra por `caller_oid` automáticamente — `ownerOid` del
    // filtro se ignora ahí (no leaks de otras sesiones).
    const search = new URLSearchParams();
    if (filter.mode) search.set("mode", filter.mode);
    if (filter.status) search.set("status", filter.status);
    const items = await api
      .get("sessions", { searchParams: search })
      .json<AgentSession[]>();
    return items.map(toSummary);
  }
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
  if (USE_REAL_API) {
    try {
      return await api.get(`sessions/${id}`).json<AgentSession>();
    } catch (err) {
      if (isHttp404(err)) return null;
      throw err;
    }
  }
  return delay(sessionsStore.get(id));
}

export async function pauseSession(id: string): Promise<AgentSession | null> {
  if (USE_REAL_API) {
    try {
      return await api
        .patch(`sessions/${id}/status`, { json: { status: "paused" } })
        .json<AgentSession>();
    } catch (err) {
      if (isHttp404(err)) return null;
      throw err;
    }
  }
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
  if (USE_REAL_API) {
    try {
      return await api
        .patch(`sessions/${id}/status`, { json: { status: "active" } })
        .json<AgentSession>();
    } catch (err) {
      if (isHttp404(err)) return null;
      throw err;
    }
  }
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
  if (USE_REAL_API) {
    await api.delete(`sessions/${id}`);
    // Limpiar mensajes/attachments locales asociados (si quedaron del modo
    // stub) — sin red para que el flujo offline siga consistente.
    messagesStore.remove(id);
    attachmentsStore.removeSession(id);
    return;
  }
  sessionsStore.remove(id);
  messagesStore.remove(id);
  attachmentsStore.removeSession(id);
  return delay(undefined);
}

/**
 * Restaura una sesión + sus mensajes — usado para undo de borrado accidental.
 * En el backend real (Fase 1) el borrado es DELETE definitivo; el undo
 * recrea la sesión vía POST. En modo stub revierte al sessionsStore directo.
 */
export async function restoreSession(
  session: AgentSession,
  messages: AgentMessage[],
): Promise<AgentSession> {
  if (USE_REAL_API) {
    const recreated = await api
      .post("sessions", {
        json: { mode: session.mode, title: session.title },
      })
      .json<AgentSession>();
    // Mensajes siguen en local hasta que Fase 2 los persista server-side.
    if (messages.length > 0) messagesStore.save(recreated.id, messages);
    return recreated;
  }
  sessionsStore.upsert(session);
  if (messages.length > 0) messagesStore.save(session.id, messages);
  return delay(session);
}

export async function getMessages(sessionId: string): Promise<AgentMessage[]> {
  if (USE_REAL_API) {
    // Backend devuelve `Message[]` (domain entity). Hasta que Fase 2 los
    // popule vía streaming SSE, la lista viene vacía — fallback al store
    // local para que sesiones creadas en stub conserven su historial.
    try {
      const remote = await api
        .get(`sessions/${sessionId}/messages`)
        .json<AgentMessage[]>();
      if (remote.length > 0) return remote;
      return messagesStore.get(sessionId);
    } catch (err) {
      if (isHttp404(err)) return [];
      throw err;
    }
  }
  return delay(messagesStore.get(sessionId));
}

/**
 * Persiste mensajes y mantiene en sync `messageCount` + `currentStage` +
 * `updatedAt` de la sesión. El caller filtra los mensajes en curso
 * (`status === "streaming"`) — solo se persiste estado terminal.
 *
 * Con backend real el persistido server-side llega vía SSE (Fase 2). Acá
 * seguimos guardando en local para que un refresh recupere la conversación
 * sin volver a transmitirla.
 */
export async function saveMessages(
  sessionId: string,
  messages: AgentMessage[],
): Promise<void> {
  messagesStore.save(sessionId, messages);
  if (!USE_REAL_API) {
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
  }
  return delay(undefined);
}

// ===========================================================================
// Helpers
// ===========================================================================

function isHttp404(err: unknown): boolean {
  if (typeof err !== "object" || err === null) return false;
  const e = err as { response?: { status?: number } };
  return e.response?.status === 404;
}
