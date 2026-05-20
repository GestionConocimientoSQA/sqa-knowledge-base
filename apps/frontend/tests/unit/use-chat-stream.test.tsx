import { describe, it, expect, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useChatStream } from "@/lib/streaming/use-chat-stream";
import type {
  MessageTransport,
  SendMessageParams,
} from "@/lib/streaming/transport";
import type { AgentEvent } from "@/lib/streaming/sse-events";
import type { AgentMessage } from "@/types/agent";

function scriptedTransport(events: AgentEvent[]): {
  transport: MessageTransport;
  lastParams: { current: SendMessageParams | null };
} {
  const lastParams = { current: null as SendMessageParams | null };
  const transport: MessageTransport = {
    sendMessage(params) {
      lastParams.current = params;
      async function* run() {
        for (const evt of events) {
          if (params.signal?.aborted) return;
          yield evt;
        }
      }
      return run();
    },
  };
  return { transport, lastParams };
}

function throwingTransport(message: string): MessageTransport {
  return {
    sendMessage() {
      async function* run(): AsyncIterable<AgentEvent> {
        throw new Error(message);
      }
      return run();
    },
  };
}

function pendingTransport(): {
  transport: MessageTransport;
  abortedAt: { current: SendMessageParams["signal"] | null };
} {
  const abortedAt = {
    current: null as SendMessageParams["signal"] | null,
  };
  const transport: MessageTransport = {
    sendMessage(params) {
      abortedAt.current = params.signal ?? null;
      async function* run(): AsyncIterable<AgentEvent> {
        await new Promise<void>((resolve) => {
          if (!params.signal) return;
          params.signal.addEventListener("abort", () => resolve(), {
            once: true,
          });
        });
      }
      return run();
    },
  };
  return { transport, abortedAt };
}

const happyPath: AgentEvent[] = [
  {
    id: "e1",
    event: "message-start",
    data: { messageId: "m1", sessionId: "s1" },
  },
  { id: "e2", event: "text-delta", data: { delta: "Hola" } },
  { id: "e3", event: "text-delta", data: { delta: " Aria" } },
  { id: "e4", event: "message-end", data: { messageId: "m1", durationMs: 42 } },
];

describe("useChatStream", () => {
  it("send appends user message, consumes events and ends in done", async () => {
    const { transport, lastParams } = scriptedTransport(happyPath);
    const { result } = renderHook(() =>
      useChatStream({ sessionId: "s1", mode: "captura", transport }),
    );

    await act(async () => {
      await result.current.send("Hola Aria");
    });

    expect(lastParams.current?.sessionId).toBe("s1");
    expect(lastParams.current?.outgoing.content).toBe("Hola Aria");
    expect(result.current.state.status).toBe("done");
    expect(result.current.state.messages).toHaveLength(2);
    expect(result.current.state.messages[0]?.role).toBe("user");
    expect(result.current.state.messages[1]?.role).toBe("agent");
    expect(result.current.state.messages[1]?.content).toBe("Hola Aria");
    expect(result.current.state.currentMessageId).toBeNull();
  });

  it("send with only whitespace and no attachments does not invoke transport", async () => {
    const sendMessage = vi.fn();
    const transport: MessageTransport = {
      sendMessage,
    } as unknown as MessageTransport;
    const { result } = renderHook(() =>
      useChatStream({ sessionId: "s1", mode: "captura", transport }),
    );

    await act(async () => {
      await result.current.send("   ");
    });

    expect(sendMessage).not.toHaveBeenCalled();
    expect(result.current.state.messages).toHaveLength(0);
    expect(result.current.state.status).toBe("idle");
  });

  it("send forwards attachmentIds to the transport", async () => {
    const { transport, lastParams } = scriptedTransport(happyPath);
    const { result } = renderHook(() =>
      useChatStream({ sessionId: "s1", mode: "captura", transport }),
    );

    await act(async () => {
      await result.current.send("con archivos", ["att-1", "att-2"]);
    });

    expect(lastParams.current?.outgoing.attachments).toEqual([
      "att-1",
      "att-2",
    ]);
  });

  it("send allows empty content if there are attachments", async () => {
    const { transport, lastParams } = scriptedTransport(happyPath);
    const { result } = renderHook(() =>
      useChatStream({ sessionId: "s1", mode: "captura", transport }),
    );

    await act(async () => {
      await result.current.send("", ["att-1"]);
    });

    expect(lastParams.current?.outgoing.attachments).toEqual(["att-1"]);
    expect(result.current.state.messages[0]?.content).toBe("");
  });

  it("cancel aborts the transport signal and flips status to cancelled", async () => {
    const { transport, abortedAt } = pendingTransport();
    const { result } = renderHook(() =>
      useChatStream({ sessionId: "s1", mode: "captura", transport }),
    );

    let sendPromise: Promise<void> = Promise.resolve();
    act(() => {
      sendPromise = result.current.send("Hola Aria");
    });

    await waitFor(() => expect(abortedAt.current).not.toBeNull());

    act(() => {
      result.current.cancel();
    });
    await act(async () => {
      await sendPromise;
    });

    expect(abortedAt.current?.aborted).toBe(true);
    expect(result.current.state.status).toBe("cancelled");
    expect(result.current.state.currentMessageId).toBeNull();
  });

  it("transport throwing maps to error status with retryable=true", async () => {
    const transport = throwingTransport("boom");
    const { result } = renderHook(() =>
      useChatStream({ sessionId: "s1", mode: "captura", transport }),
    );

    await act(async () => {
      await result.current.send("Hola");
    });

    expect(result.current.state.status).toBe("error");
    expect(result.current.state.error?.type).toBe("transport");
    expect(result.current.state.error?.message).toBe("boom");
    expect(result.current.state.error?.retryable).toBe(true);
  });

  it("retry re-runs the last outgoing payload", async () => {
    const sendMessage = vi.fn(
      (params: SendMessageParams): AsyncIterable<AgentEvent> => {
        void params;
        async function* run() {
          for (const evt of happyPath) yield evt;
        }
        return run();
      },
    );
    const transport: MessageTransport = { sendMessage };
    const { result } = renderHook(() =>
      useChatStream({ sessionId: "s1", mode: "captura", transport }),
    );

    await act(async () => {
      await result.current.send("primer intento", ["att-1"]);
    });
    await act(async () => {
      await result.current.retry();
    });

    expect(sendMessage).toHaveBeenCalledTimes(2);
    const second = sendMessage.mock.calls[1]?.[0];
    expect(second?.outgoing.content).toBe("primer intento");
    expect(second?.outgoing.attachments).toEqual(["att-1"]);
  });

  it("retry without prior send is a no-op", async () => {
    const sendMessage = vi.fn();
    const transport: MessageTransport = {
      sendMessage,
    } as unknown as MessageTransport;
    const { result } = renderHook(() =>
      useChatStream({ sessionId: "s1", mode: "captura", transport }),
    );

    await act(async () => {
      await result.current.retry();
    });

    expect(sendMessage).not.toHaveBeenCalled();
  });

  it("reset clears messages and returns to idle", async () => {
    const { transport } = scriptedTransport(happyPath);
    const { result } = renderHook(() =>
      useChatStream({ sessionId: "s1", mode: "captura", transport }),
    );

    await act(async () => {
      await result.current.send("Hola");
    });
    expect(result.current.state.messages.length).toBeGreaterThan(0);

    act(() => {
      result.current.reset();
    });

    expect(result.current.state.status).toBe("idle");
    expect(result.current.state.messages).toEqual([]);
  });

  it("hidrata initialMessages y deriva currentStage del último agente con stage", async () => {
    const { transport } = scriptedTransport([]);
    const initialMessages: AgentMessage[] = [
      {
        id: "u1",
        role: "user",
        content: "Hola",
        stage: null,
        status: "complete",
        startedAt: "2026-05-19T12:00:00.000Z",
        endedAt: "2026-05-19T12:00:00.000Z",
        durationMs: 0,
        classification: null,
        citations: [],
        scoring: null,
        artifacts: [],
        tokenUsage: null,
        error: null,
      },
      {
        id: "a1",
        role: "agent",
        content: "Iniciando",
        stage: 2,
        status: "complete",
        startedAt: "2026-05-19T12:00:01.000Z",
        endedAt: "2026-05-19T12:00:02.000Z",
        durationMs: 1000,
        classification: null,
        citations: [],
        scoring: null,
        artifacts: [],
        tokenUsage: null,
        error: null,
      },
    ];
    const { result } = renderHook(() =>
      useChatStream({
        sessionId: "s1",
        mode: "captura",
        transport,
        initialMessages,
      }),
    );

    await waitFor(() => {
      expect(result.current.state.messages).toHaveLength(2);
    });
    expect(result.current.state.currentStage).toBe(2);
  });
});
