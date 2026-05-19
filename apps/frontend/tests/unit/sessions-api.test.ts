import { describe, it, expect, beforeEach } from "vitest";
import {
  createSession,
  deleteSession,
  getMessages,
  getSession,
  listSessions,
  pauseSession,
  restoreSession,
  resumeSession,
  saveMessages,
} from "@/lib/api/sessions";
import { sessionsStore } from "@/lib/api/sessions-store";
import { messagesStore } from "@/lib/api/messages-store";
import type { AgentMessage } from "@/types/agent";

function makeAgentMessage(
  id: string,
  partial: Partial<AgentMessage> = {},
): AgentMessage {
  return {
    id,
    role: "agent",
    content: "",
    stage: null,
    status: "complete",
    startedAt: "2026-05-19T12:00:00.000Z",
    endedAt: "2026-05-19T12:00:01.000Z",
    durationMs: 1000,
    classification: null,
    citations: [],
    scoring: null,
    artifacts: [],
    tokenUsage: null,
    error: null,
    ...partial,
  };
}

describe("sessions API (stub)", () => {
  beforeEach(() => {
    sessionsStore.clear();
    messagesStore.clear();
  });

  it("createSession persists and returns with id + timestamps", async () => {
    const s = await createSession({ mode: "captura", ownerOid: "oid-1" });
    expect(s.id).toBeTruthy();
    expect(s.status).toBe("active");
    expect(s.createdAt).toBe(s.updatedAt);
    expect(s.title).toBe("Nueva captura");
    expect(s.messageCount).toBe(0);

    const fetched = await getSession(s.id);
    expect(fetched?.id).toBe(s.id);
  });

  it("createSession honors custom title", async () => {
    const s = await createSession({
      mode: "consulta",
      ownerOid: "oid-1",
      title: "Investigación flaky tests",
    });
    expect(s.title).toBe("Investigación flaky tests");
  });

  it("listSessions filters by ownerOid and orders by updatedAt desc", async () => {
    const a = await createSession({ mode: "captura", ownerOid: "owner-A" });
    await new Promise((r) => setTimeout(r, 5));
    const b = await createSession({ mode: "consulta", ownerOid: "owner-A" });
    await createSession({ mode: "ingesta", ownerOid: "owner-B" });

    const ownerA = await listSessions({ ownerOid: "owner-A" });
    expect(ownerA).toHaveLength(2);
    expect(ownerA[0]?.id).toBe(b.id);
    expect(ownerA[1]?.id).toBe(a.id);
  });

  it("listSessions filters by mode and status", async () => {
    await createSession({ mode: "captura", ownerOid: "oid-1" });
    const consulta = await createSession({
      mode: "consulta",
      ownerOid: "oid-1",
    });
    await pauseSession(consulta.id);

    const onlyConsulta = await listSessions({ mode: "consulta" });
    expect(onlyConsulta).toHaveLength(1);

    const onlyPaused = await listSessions({ status: "paused" });
    expect(onlyPaused).toHaveLength(1);
    expect(onlyPaused[0]?.id).toBe(consulta.id);
  });

  it("pauseSession + resumeSession toggle status and bump updatedAt", async () => {
    const s = await createSession({ mode: "captura", ownerOid: "oid-1" });
    const created = s.updatedAt;

    await new Promise((r) => setTimeout(r, 5));
    const paused = await pauseSession(s.id);
    expect(paused?.status).toBe("paused");
    expect(paused?.updatedAt.localeCompare(created)).toBeGreaterThan(0);

    await new Promise((r) => setTimeout(r, 5));
    const resumed = await resumeSession(s.id);
    expect(resumed?.status).toBe("active");
  });

  it("pauseSession returns null when id does not exist", async () => {
    const result = await pauseSession("does-not-exist");
    expect(result).toBeNull();
  });

  it("deleteSession removes the session", async () => {
    const s = await createSession({ mode: "ingesta", ownerOid: "oid-1" });
    await deleteSession(s.id);
    expect(await getSession(s.id)).toBeNull();
  });

  it("saveMessages persists messages and updates messageCount + currentStage", async () => {
    const s = await createSession({ mode: "captura", ownerOid: "oid-1" });
    const initialUpdatedAt = s.updatedAt;
    await new Promise((r) => setTimeout(r, 5));

    await saveMessages(s.id, [
      makeAgentMessage("a-1", { role: "agent", stage: 1, content: "Hola" }),
      makeAgentMessage("a-2", { role: "agent", stage: 3, content: "Sigamos" }),
    ]);

    const persisted = await getMessages(s.id);
    expect(persisted).toHaveLength(2);

    const updated = await getSession(s.id);
    expect(updated?.messageCount).toBe(2);
    expect(updated?.currentStage).toBe(3);
    expect(updated?.updatedAt.localeCompare(initialUpdatedAt)).toBeGreaterThan(0);
  });

  it("getMessages returns empty array when no messages persisted", async () => {
    const s = await createSession({ mode: "consulta", ownerOid: "oid-1" });
    expect(await getMessages(s.id)).toEqual([]);
  });

  it("deleteSession also wipes its messages", async () => {
    const s = await createSession({ mode: "captura", ownerOid: "oid-1" });
    await saveMessages(s.id, [makeAgentMessage("a-1")]);
    await deleteSession(s.id);
    expect(await getMessages(s.id)).toEqual([]);
  });

  it("restoreSession brings session + messages back", async () => {
    const s = await createSession({ mode: "ingesta", ownerOid: "oid-1" });
    const messages = [
      makeAgentMessage("a-1", { content: "First" }),
      makeAgentMessage("a-2", { content: "Second" }),
    ];
    await saveMessages(s.id, messages);
    const fullSession = await getSession(s.id);
    expect(fullSession).not.toBeNull();

    await deleteSession(s.id);
    expect(await getSession(s.id)).toBeNull();

    await restoreSession(fullSession!, messages);
    const restored = await getSession(s.id);
    expect(restored?.id).toBe(s.id);
    const restoredMessages = await getMessages(s.id);
    expect(restoredMessages).toHaveLength(2);
    expect(restoredMessages[0]?.content).toBe("First");
  });

  it("saveMessages keeps last currentStage when newer messages have no stage", async () => {
    const s = await createSession({ mode: "captura", ownerOid: "oid-1" });
    await saveMessages(s.id, [
      makeAgentMessage("a-1", { role: "agent", stage: 2 }),
      makeAgentMessage("u-1", { role: "user", stage: null }),
    ]);
    const updated = await getSession(s.id);
    expect(updated?.currentStage).toBe(2);
  });
});
