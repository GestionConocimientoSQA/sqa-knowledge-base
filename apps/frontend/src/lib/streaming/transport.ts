/**
 * Contrato del transport de mensajes hacia el agente.
 *
 * El hook `use-chat-stream` depende de esta interfaz, no de su implementación
 * concreta (DIP). En sub-fase 6.1 la implementación es `MockMessageTransport`
 * (events locales); cuando llegue el backend real (Fase 2) se sustituye por
 * `SseMessageTransport` que parsea `text/event-stream`. El reducer y la UI no
 * cambian.
 */
import type { SessionMode } from "@/types/domain";
import type { OutgoingMessage } from "@/types/agent";
import type { AgentEvent } from "@/lib/streaming/sse-events";

export interface SendMessageParams {
  sessionId: string;
  mode: SessionMode;
  outgoing: OutgoingMessage;
  /** Último event-id recibido — habilita reconexión SSE en el backend real. */
  lastEventId?: string;
  signal?: AbortSignal;
}

export interface MessageTransport {
  /**
   * Inicia el stream y emite eventos del agente hasta `message-end` o `error`.
   * El consumidor itera con `for await` y aborta cerrando el `signal`.
   */
  sendMessage(params: SendMessageParams): AsyncIterable<AgentEvent>;
}
