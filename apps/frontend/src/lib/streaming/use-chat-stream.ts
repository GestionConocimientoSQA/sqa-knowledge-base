/**
 * Hook React que pega el `MessageTransport` con el `streamReducer`.
 *
 * Responsabilidad única: orquestar el ciclo de vida de un stream del agente
 * (enviar, recibir, cancelar, reintentar). No conoce el transporte concreto
 * (DIP) ni la UI (la UI consume `state` y dispara `send/cancel/retry`).
 */
"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";
import type { AgentMessage } from "@/types/agent";
import type { SessionMode } from "@/types/domain";
import type { MessageTransport } from "@/lib/streaming/transport";
import {
  initialStreamState,
  streamReducer,
  type StreamState,
} from "@/lib/streaming/reducer";

export interface UseChatStreamOptions {
  sessionId: string;
  mode: SessionMode;
  transport: MessageTransport;
  initialMessages?: AgentMessage[];
}

export interface UseChatStreamResult {
  state: StreamState;
  send: (content: string, attachmentIds?: string[]) => Promise<void>;
  cancel: () => void;
  reset: () => void;
  retry: () => Promise<void>;
}

function generateUserMessageId(): string {
  return `usr-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 8)}`;
}

export function useChatStream(
  options: UseChatStreamOptions,
): UseChatStreamResult {
  const { sessionId, mode, transport, initialMessages } = options;

  const [state, dispatch] = useReducer(streamReducer, initialStreamState);
  const abortRef = useRef<AbortController | null>(null);
  const lastOutgoingRef = useRef<{
    content: string;
    attachmentIds?: string[];
  } | null>(null);
  const hydratedRef = useRef(false);

  useEffect(() => {
    if (hydratedRef.current) return;
    if (initialMessages && initialMessages.length > 0) {
      dispatch({ type: "hydrate", messages: initialMessages });
      hydratedRef.current = true;
    }
  }, [initialMessages]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const runStream = useCallback(
    async (content: string, attachmentIds?: string[]) => {
      const controller = new AbortController();
      abortRef.current?.abort();
      abortRef.current = controller;

      dispatch({
        type: "user-send",
        messageId: generateUserMessageId(),
        content,
        at: new Date().toISOString(),
      });

      try {
        const iterable = transport.sendMessage({
          sessionId,
          mode,
          outgoing: { content, attachments: attachmentIds },
          lastEventId: undefined,
          signal: controller.signal,
        });
        for await (const event of iterable) {
          if (controller.signal.aborted) break;
          dispatch(event);
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        const message = err instanceof Error ? err.message : "unknown error";
        dispatch({
          id: `local-error-${Date.now()}`,
          event: "error",
          data: { type: "transport", message, retryable: true },
        });
      }
    },
    [sessionId, mode, transport],
  );

  const send = useCallback(
    async (content: string, attachmentIds?: string[]) => {
      const trimmed = content.trim();
      const hasAttachments = (attachmentIds?.length ?? 0) > 0;
      if (!trimmed && !hasAttachments) return;
      lastOutgoingRef.current = { content: trimmed, attachmentIds };
      await runStream(trimmed, attachmentIds);
    },
    [runStream],
  );

  const cancel = useCallback(() => {
    if (!abortRef.current) return;
    abortRef.current.abort();
    abortRef.current = null;
    dispatch({ type: "cancel", at: new Date().toISOString() });
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    lastOutgoingRef.current = null;
    hydratedRef.current = false;
    dispatch({ type: "reset" });
  }, []);

  const retry = useCallback(async () => {
    const last = lastOutgoingRef.current;
    if (!last) return;
    await runStream(last.content, last.attachmentIds);
  }, [runStream]);

  return { state, send, cancel, reset, retry };
}
