/**
 * Reducer puro del stream del agente.
 *
 * Recibe un `StreamAction` (acción local o evento SSE) y devuelve el siguiente
 * estado de forma inmutable. No depende de React — `useReducer` lo monta en
 * `use-chat-stream`.
 *
 * Separar el reducer del hook (SRP) permite:
 *  - testearlo sin DOM ni async
 *  - reusarlo desde un SSR / replay de eventos persistidos
 *  - mantener un único punto de mutación del estado del chat
 */
import type {
  AgentErrorPayload,
  AgentMessage,
  KbSearchHit,
  StageId,
} from "@/types/agent";
import type { AgentEvent } from "@/lib/streaming/sse-events";

function deriveCurrentStage(messages: AgentMessage[]): StageId | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (msg?.role === "agent" && msg.stage !== null) return msg.stage;
  }
  return null;
}

export type StreamStatus =
  | "idle"
  | "connecting"
  | "streaming"
  | "done"
  | "error"
  | "cancelled";

export interface StreamState {
  messages: AgentMessage[];
  currentMessageId: string | null;
  currentStage: StageId | null;
  kbSearchHits: KbSearchHit[];
  status: StreamStatus;
  error: AgentErrorPayload | null;
  lastEventId: string | null;
  lastPingAt: string | null;
}

export type ClientAction =
  | { type: "user-send"; messageId: string; content: string; at: string }
  | { type: "connecting" }
  | { type: "cancel"; at: string }
  | { type: "reset" }
  | { type: "hydrate"; messages: AgentMessage[] };

export type StreamAction = ClientAction | AgentEvent;

export const initialStreamState: StreamState = {
  messages: [],
  currentMessageId: null,
  currentStage: null,
  kbSearchHits: [],
  status: "idle",
  error: null,
  lastEventId: null,
  lastPingAt: null,
};

function buildAgentMessage(id: string, startedAt: string): AgentMessage {
  return {
    id,
    role: "agent",
    content: "",
    stage: null,
    status: "streaming",
    startedAt,
    endedAt: null,
    durationMs: null,
    classification: null,
    citations: [],
    scoring: null,
    artifacts: [],
    tokenUsage: null,
    error: null,
  };
}

function buildUserMessage(
  id: string,
  content: string,
  startedAt: string,
): AgentMessage {
  return {
    id,
    role: "user",
    content,
    stage: null,
    status: "complete",
    startedAt,
    endedAt: startedAt,
    durationMs: 0,
    classification: null,
    citations: [],
    scoring: null,
    artifacts: [],
    tokenUsage: null,
    error: null,
  };
}

function updateCurrentAgentMessage(
  state: StreamState,
  patch: (msg: AgentMessage) => AgentMessage,
): StreamState {
  if (!state.currentMessageId) return state;
  const targetId = state.currentMessageId;
  return {
    ...state,
    messages: state.messages.map((m) => (m.id === targetId ? patch(m) : m)),
  };
}

function applyClientAction(
  state: StreamState,
  action: ClientAction,
): StreamState {
  switch (action.type) {
    case "user-send":
      return {
        ...state,
        messages: [
          ...state.messages,
          buildUserMessage(action.messageId, action.content, action.at),
        ],
        status: "connecting",
        error: null,
      };

    case "connecting":
      return { ...state, status: "connecting", error: null };

    case "cancel":
      return {
        ...updateCurrentAgentMessage(state, (m) => ({
          ...m,
          status: "complete",
          endedAt: action.at,
          durationMs: Date.parse(action.at) - Date.parse(m.startedAt),
        })),
        status: "cancelled",
        currentMessageId: null,
      };

    case "reset":
      return initialStreamState;

    case "hydrate":
      return {
        ...initialStreamState,
        messages: action.messages,
        currentStage: deriveCurrentStage(action.messages),
      };
  }
}

function applyAgentEvent(state: StreamState, event: AgentEvent): StreamState {
  const next: StreamState = { ...state, lastEventId: event.id };

  switch (event.event) {
    case "message-start": {
      const startedAt = new Date().toISOString();
      return {
        ...next,
        messages: [
          ...next.messages,
          buildAgentMessage(event.data.messageId, startedAt),
        ],
        currentMessageId: event.data.messageId,
        status: "streaming",
      };
    }

    case "stage-change": {
      return updateCurrentAgentMessage(
        { ...next, currentStage: event.data.to },
        (m) => ({ ...m, stage: event.data.to }),
      );
    }

    case "classification": {
      return updateCurrentAgentMessage(next, (m) => ({
        ...m,
        classification: event.data,
      }));
    }

    case "kb-search-result": {
      return { ...next, kbSearchHits: event.data.existingDocuments };
    }

    case "text-delta": {
      return updateCurrentAgentMessage(next, (m) => ({
        ...m,
        content: m.content + event.data.delta,
      }));
    }

    case "tool-use":
    case "tool-result": {
      // En sub-fase 6.1 no exponemos tools a la UI. El reducer reconoce los
      // eventos para no romper el discriminated union, sin mutar estado visible.
      return next;
    }

    case "citation": {
      return updateCurrentAgentMessage(next, (m) => ({
        ...m,
        citations: [...m.citations, event.data],
      }));
    }

    case "scoring": {
      return updateCurrentAgentMessage(next, (m) => ({
        ...m,
        scoring: event.data,
      }));
    }

    case "document-generated": {
      return updateCurrentAgentMessage(next, (m) => ({
        ...m,
        artifacts: [...m.artifacts, event.data],
      }));
    }

    case "token-usage": {
      return updateCurrentAgentMessage(next, (m) => ({
        ...m,
        tokenUsage: event.data,
      }));
    }

    case "message-end": {
      const endedAt = new Date().toISOString();
      return {
        ...updateCurrentAgentMessage(next, (m) => ({
          ...m,
          status: "complete",
          endedAt,
          durationMs: event.data.durationMs,
        })),
        currentMessageId: null,
        status: "done",
      };
    }

    case "error": {
      return {
        ...updateCurrentAgentMessage(next, (m) => ({
          ...m,
          status: "error",
          error: event.data,
        })),
        status: "error",
        error: event.data,
      };
    }

    case "ping": {
      return { ...next, lastPingAt: event.data.timestamp };
    }
  }
}

export function streamReducer(
  state: StreamState,
  action: StreamAction,
): StreamState {
  if ("type" in action) return applyClientAction(state, action);
  return applyAgentEvent(state, action);
}
