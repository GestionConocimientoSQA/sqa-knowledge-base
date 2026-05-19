import { describe, it, expect } from "vitest";
import { MockMessageTransport } from "@/lib/streaming/mock-transport";
import type { AgentEvent } from "@/lib/streaming/sse-events";
import type { SessionMode } from "@/types/domain";

async function collect(
  transport: MockMessageTransport,
  mode: SessionMode,
  signal?: AbortSignal,
): Promise<AgentEvent[]> {
  const events: AgentEvent[] = [];
  for await (const ev of transport.sendMessage({
    sessionId: "s1",
    mode,
    outgoing: { content: "test" },
    signal,
  })) {
    events.push(ev);
  }
  return events;
}

describe("MockMessageTransport", () => {
  const transport = new MockMessageTransport({ speedFactor: 200 });

  it("starts with message-start and ends with message-end", async () => {
    const events = await collect(transport, "captura");
    expect(events.at(0)?.event).toBe("message-start");
    expect(events.at(-1)?.event).toBe("message-end");
  });

  it("modo captura emits the six stages in order (0→5)", async () => {
    const events = await collect(transport, "captura");
    const stages = events
      .filter((e) => e.event === "stage-change")
      .map((e) => (e.event === "stage-change" ? e.data.to : null));
    expect(stages).toEqual([0, 1, 2, 3, 4, 5]);
  });

  it("modo captura includes classification, citation, scoring and document-generated", async () => {
    const events = await collect(transport, "captura");
    const names = events.map((e) => e.event);
    expect(names).toContain("classification");
    expect(names).toContain("citation");
    expect(names).toContain("scoring");
    expect(names).toContain("document-generated");
    expect(names).toContain("token-usage");
  });

  it("modo consulta uses stage C and emits kb-search-result", async () => {
    const events = await collect(transport, "consulta");
    const stageChange = events.find((e) => e.event === "stage-change");
    expect(stageChange?.event === "stage-change" && stageChange.data.to).toBe(
      "C",
    );
    const names = events.map((e) => e.event);
    expect(names).toContain("kb-search-result");
    expect(names).not.toContain("document-generated");
  });

  it("modo ingesta uses stage I and emits classification without generation", async () => {
    const events = await collect(transport, "ingesta");
    const stageChange = events.find((e) => e.event === "stage-change");
    expect(stageChange?.event === "stage-change" && stageChange.data.to).toBe(
      "I",
    );
    const names = events.map((e) => e.event);
    expect(names).toContain("classification");
    expect(names).not.toContain("document-generated");
  });

  it("event ids are monotonic and unique", async () => {
    const events = await collect(transport, "consulta");
    const ids = events.map((e) => e.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("aborts cleanly when signal is fired mid-stream", async () => {
    const controller = new AbortController();
    const events: AgentEvent[] = [];
    const iter = transport.sendMessage({
      sessionId: "s1",
      mode: "captura",
      outgoing: { content: "x" },
      signal: controller.signal,
    });
    let count = 0;
    for await (const ev of iter) {
      events.push(ev);
      count++;
      if (count === 3) controller.abort();
    }
    expect(events.length).toBeGreaterThanOrEqual(3);
    expect(events.length).toBeLessThan(40);
  });
});
