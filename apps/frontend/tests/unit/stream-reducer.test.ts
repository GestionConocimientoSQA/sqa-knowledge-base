import { describe, it, expect } from "vitest";
import {
  initialStreamState,
  streamReducer,
  type StreamState,
} from "@/lib/streaming/reducer";
import type { AgentEvent } from "@/lib/streaming/sse-events";

function makeEvent<E extends AgentEvent>(event: E): E {
  return event;
}

describe("streamReducer", () => {
  it("starts with idle status and no messages", () => {
    expect(initialStreamState.status).toBe("idle");
    expect(initialStreamState.messages).toEqual([]);
    expect(initialStreamState.currentMessageId).toBeNull();
  });

  it("user-send appends a user message and flips status to connecting", () => {
    const next = streamReducer(initialStreamState, {
      type: "user-send",
      messageId: "u1",
      content: "Hola Aria",
      at: "2026-05-19T12:00:00.000Z",
    });
    expect(next.messages).toHaveLength(1);
    expect(next.messages[0]?.role).toBe("user");
    expect(next.messages[0]?.content).toBe("Hola Aria");
    expect(next.status).toBe("connecting");
  });

  it("message-start creates a streaming agent message", () => {
    const next = streamReducer(
      initialStreamState,
      makeEvent({
        id: "e1",
        event: "message-start",
        data: { messageId: "m1", sessionId: "s1" },
      }),
    );
    expect(next.messages).toHaveLength(1);
    expect(next.messages[0]?.role).toBe("agent");
    expect(next.messages[0]?.status).toBe("streaming");
    expect(next.currentMessageId).toBe("m1");
    expect(next.status).toBe("streaming");
  });

  it("text-delta accumulates content on the current message", () => {
    let state: StreamState = streamReducer(
      initialStreamState,
      makeEvent({
        id: "e1",
        event: "message-start",
        data: { messageId: "m1", sessionId: "s1" },
      }),
    );
    state = streamReducer(
      state,
      makeEvent({ id: "e2", event: "text-delta", data: { delta: "Hola" } }),
    );
    state = streamReducer(
      state,
      makeEvent({ id: "e3", event: "text-delta", data: { delta: " Aria" } }),
    );
    expect(state.messages[0]?.content).toBe("Hola Aria");
  });

  it("stage-change updates both global currentStage and message stage", () => {
    let state: StreamState = streamReducer(
      initialStreamState,
      makeEvent({
        id: "e1",
        event: "message-start",
        data: { messageId: "m1", sessionId: "s1" },
      }),
    );
    state = streamReducer(
      state,
      makeEvent({
        id: "e2",
        event: "stage-change",
        data: { from: 0, to: 1, reason: "topic-identified" },
      }),
    );
    expect(state.currentStage).toBe(1);
    expect(state.messages[0]?.stage).toBe(1);
  });

  it("classification, scoring and artifacts land on the current agent message", () => {
    let state: StreamState = streamReducer(
      initialStreamState,
      makeEvent({
        id: "e1",
        event: "message-start",
        data: { messageId: "m1", sessionId: "s1" },
      }),
    );
    state = streamReducer(
      state,
      makeEvent({
        id: "e2",
        event: "classification",
        data: { category: "TEC", documentType: "MTEC", confidence: 0.9 },
      }),
    );
    state = streamReducer(
      state,
      makeEvent({
        id: "e3",
        event: "scoring",
        data: {
          specificity: 4,
          depth: 4,
          reusability: 3.5,
          uniqueness: 4.2,
          valueScore: 3.9,
        },
      }),
    );
    state = streamReducer(
      state,
      makeEvent({
        id: "e4",
        event: "document-generated",
        data: {
          documentId: "d1",
          filename: "out.docx",
          downloadUrl: "/x",
          blobPath: "blob://x",
        },
      }),
    );
    const msg = state.messages[0];
    expect(msg?.classification?.category).toBe("TEC");
    expect(msg?.scoring?.valueScore).toBe(3.9);
    expect(msg?.artifacts).toHaveLength(1);
  });

  it("citation accumulates into an array", () => {
    let state: StreamState = streamReducer(
      initialStreamState,
      makeEvent({
        id: "e1",
        event: "message-start",
        data: { messageId: "m1", sessionId: "s1" },
      }),
    );
    state = streamReducer(
      state,
      makeEvent({
        id: "e2",
        event: "citation",
        data: {
          documentId: "d1",
          filename: "a.docx",
          section: "§1",
          snippet: "...",
        },
      }),
    );
    state = streamReducer(
      state,
      makeEvent({
        id: "e3",
        event: "citation",
        data: {
          documentId: "d2",
          filename: "b.docx",
          section: "§2",
          snippet: "...",
        },
      }),
    );
    expect(state.messages[0]?.citations).toHaveLength(2);
  });

  it("message-end marks the current message complete and clears the pointer", () => {
    let state: StreamState = streamReducer(
      initialStreamState,
      makeEvent({
        id: "e1",
        event: "message-start",
        data: { messageId: "m1", sessionId: "s1" },
      }),
    );
    state = streamReducer(
      state,
      makeEvent({
        id: "e2",
        event: "message-end",
        data: { messageId: "m1", durationMs: 1234 },
      }),
    );
    expect(state.messages[0]?.status).toBe("complete");
    expect(state.messages[0]?.durationMs).toBe(1234);
    expect(state.currentMessageId).toBeNull();
    expect(state.status).toBe("done");
  });

  it("error sets retryable payload on message and global state", () => {
    let state: StreamState = streamReducer(
      initialStreamState,
      makeEvent({
        id: "e1",
        event: "message-start",
        data: { messageId: "m1", sessionId: "s1" },
      }),
    );
    state = streamReducer(
      state,
      makeEvent({
        id: "e2",
        event: "error",
        data: { type: "transport", message: "boom", retryable: true },
      }),
    );
    expect(state.status).toBe("error");
    expect(state.error?.retryable).toBe(true);
    expect(state.messages[0]?.status).toBe("error");
  });

  it("ping updates lastPingAt without mutating messages", () => {
    const state = streamReducer(
      initialStreamState,
      makeEvent({
        id: "e1",
        event: "ping",
        data: { timestamp: "2026-05-19T12:00:00.000Z" },
      }),
    );
    expect(state.lastPingAt).toBe("2026-05-19T12:00:00.000Z");
    expect(state.messages).toEqual([]);
  });

  it("kb-search-result stores hits at the top level", () => {
    const state = streamReducer(
      initialStreamState,
      makeEvent({
        id: "e1",
        event: "kb-search-result",
        data: {
          existingDocuments: [
            { documentId: "d1", filename: "x.docx", score: 0.8, snippet: "..." },
          ],
        },
      }),
    );
    expect(state.kbSearchHits).toHaveLength(1);
  });

  it("cancel marks the current message complete and flips status", () => {
    let state: StreamState = streamReducer(
      initialStreamState,
      makeEvent({
        id: "e1",
        event: "message-start",
        data: { messageId: "m1", sessionId: "s1" },
      }),
    );
    state = streamReducer(state, {
      type: "cancel",
      at: "2026-05-19T12:00:01.000Z",
    });
    expect(state.status).toBe("cancelled");
    expect(state.currentMessageId).toBeNull();
    expect(state.messages[0]?.status).toBe("complete");
  });

  it("hydrate restores messages and derives currentStage from last agent message", () => {
    const hydrated: StreamState = streamReducer(initialStreamState, {
      type: "hydrate",
      messages: [
        {
          id: "u-1",
          role: "user",
          content: "Pregunta",
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
          id: "a-1",
          role: "agent",
          content: "Respuesta",
          stage: 3,
          status: "complete",
          startedAt: "2026-05-19T12:00:01.000Z",
          endedAt: "2026-05-19T12:00:02.000Z",
          durationMs: 1200,
          classification: null,
          citations: [],
          scoring: null,
          artifacts: [],
          tokenUsage: null,
          error: null,
        },
      ],
    });
    expect(hydrated.messages).toHaveLength(2);
    expect(hydrated.currentStage).toBe(3);
  });

  it("hydrate leaves currentStage null when no agent message has a stage", () => {
    const hydrated: StreamState = streamReducer(initialStreamState, {
      type: "hydrate",
      messages: [
        {
          id: "u-1",
          role: "user",
          content: "Pregunta",
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
      ],
    });
    expect(hydrated.currentStage).toBeNull();
  });

  it("reset returns to initialState", () => {
    let state: StreamState = streamReducer(
      initialStreamState,
      makeEvent({
        id: "e1",
        event: "message-start",
        data: { messageId: "m1", sessionId: "s1" },
      }),
    );
    state = streamReducer(state, { type: "reset" });
    expect(state).toEqual(initialStreamState);
  });
});
