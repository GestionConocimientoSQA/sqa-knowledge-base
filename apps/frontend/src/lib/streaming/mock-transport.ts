/**
 * Implementación mock del `MessageTransport`.
 *
 * Genera eventos del agente localmente con timing realista para validar la UX
 * de streaming sin depender del backend (Fase 2). Los flujos espejan los modos
 * A/B/C definidos en ROADMAP §10:
 *
 *   - Modo A (captura)  → ETAPAS 0→1→2→3→4→5 con citation + scoring + artifact
 *   - Modo B (consulta) → ETAPA C, kb-search, citations top-k
 *   - Modo C (ingesta)  → ETAPA I, classification, sin generación
 *
 * El generator respeta `AbortSignal`: si el consumidor aborta, `delay` rechaza
 * con `DOMException("aborted")` y el for-await termina limpiamente.
 */
import type { AgentEvent } from "@/lib/streaming/sse-events";
import type {
  MessageTransport,
  SendMessageParams,
} from "@/lib/streaming/transport";

const TEXT_DELTA_MS = 30;
const STAGE_TRANSITION_MS = 220;
const META_EVENT_MS = 140;

class AbortError extends Error {
  constructor() {
    super("aborted");
    this.name = "AbortError";
  }
}

function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new AbortError());
      return;
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    function onAbort() {
      clearTimeout(timer);
      reject(new AbortError());
    }
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

function nextEventId(messageId: string, index: number): string {
  return `${messageId}-${index.toString().padStart(4, "0")}`;
}

function splitInDeltas(text: string, chunkSize = 6): string[] {
  const chunks: string[] = [];
  for (let i = 0; i < text.length; i += chunkSize) {
    chunks.push(text.slice(i, i + chunkSize));
  }
  return chunks;
}

interface ScriptedStep {
  kind: "event" | "deltas";
  event?: Omit<AgentEvent, "id">;
  text?: string;
  delayBefore: number;
}

function captureScript(): ScriptedStep[] {
  return [
    {
      kind: "event",
      delayBefore: META_EVENT_MS,
      event: {
        event: "stage-change",
        data: { from: null, to: 0, reason: "session-start" },
      },
    },
    {
      kind: "deltas",
      delayBefore: META_EVENT_MS,
      text: "Hola. Soy Aria. Vamos a capturar este conocimiento. ",
    },
    {
      kind: "event",
      delayBefore: STAGE_TRANSITION_MS,
      event: {
        event: "stage-change",
        data: { from: 0, to: 1, reason: "user-identified-topic" },
      },
    },
    {
      kind: "deltas",
      delayBefore: META_EVENT_MS,
      text: "Identifiqué que el tema podría encajar en la carpeta técnica. ",
    },
    {
      kind: "event",
      delayBefore: META_EVENT_MS,
      event: {
        event: "classification",
        data: {
          category: "TEC",
          documentType: "MTEC",
          confidence: 0.86,
          rationale: "Patrón detectado: descripción de solución técnica reusable",
        },
      },
    },
    {
      kind: "event",
      delayBefore: META_EVENT_MS,
      event: {
        event: "kb-search-result",
        data: {
          existingDocuments: [
            {
              documentId: "TEC-flakiness-detection-2026-04-22",
              filename: "MTEC-flakiness-detection.docx",
              score: 0.74,
              snippet: "Detección y aislamiento de tests flaky...",
            },
          ],
        },
      },
    },
    {
      kind: "event",
      delayBefore: STAGE_TRANSITION_MS,
      event: {
        event: "stage-change",
        data: { from: 1, to: 2, reason: "ready-for-free-capture" },
      },
    },
    {
      kind: "deltas",
      delayBefore: META_EVENT_MS,
      text: "Contame con tus palabras qué descubriste y cómo lo resolviste. ",
    },
    {
      kind: "event",
      delayBefore: STAGE_TRANSITION_MS,
      event: {
        event: "stage-change",
        data: { from: 2, to: 3, reason: "free-capture-complete" },
      },
    },
    {
      kind: "deltas",
      delayBefore: META_EVENT_MS,
      text: "Profundicemos en el contexto del cliente y los trade-offs.",
    },
    {
      kind: "event",
      delayBefore: META_EVENT_MS,
      event: {
        event: "citation",
        data: {
          documentId: "ARQ-microservicios-checkout-2026-02-11",
          filename: "ARCL-microservicios-checkout.docx",
          section: "§3.2 Estrategia de contract testing",
          snippet: "Pact contracts publicados desde el consumidor...",
        },
      },
    },
    {
      kind: "event",
      delayBefore: STAGE_TRANSITION_MS,
      event: {
        event: "stage-change",
        data: { from: 3, to: 4, reason: "deep-dive-complete" },
      },
    },
    {
      kind: "deltas",
      delayBefore: META_EVENT_MS,
      text: "Validemos el resumen estructurado.",
    },
    {
      kind: "event",
      delayBefore: META_EVENT_MS,
      event: {
        event: "scoring",
        data: {
          specificity: 4.2,
          depth: 4.0,
          reusability: 3.8,
          uniqueness: 4.3,
          valueScore: 4.1,
        },
      },
    },
    {
      kind: "event",
      delayBefore: STAGE_TRANSITION_MS,
      event: {
        event: "stage-change",
        data: { from: 4, to: 5, reason: "validation-approved" },
      },
    },
    {
      kind: "event",
      delayBefore: META_EVENT_MS,
      event: {
        event: "document-generated",
        data: {
          documentId: "TEC-captura-mock-2026-05-19",
          filename: "MTEC-captura-mock-2026-05-19.docx",
          downloadUrl: "/mock/downloads/MTEC-captura-mock-2026-05-19.docx",
          blobPath: "blob://documents/mock/MTEC-captura-mock-2026-05-19.docx",
        },
      },
    },
  ];
}

function consultationScript(): ScriptedStep[] {
  return [
    {
      kind: "event",
      delayBefore: META_EVENT_MS,
      event: {
        event: "stage-change",
        data: { from: null, to: "C", reason: "consultation-mode" },
      },
    },
    {
      kind: "deltas",
      delayBefore: META_EVENT_MS,
      text: "Busqué en la base de conocimiento. Esto es lo que encontré:",
    },
    {
      kind: "event",
      delayBefore: META_EVENT_MS,
      event: {
        event: "kb-search-result",
        data: {
          existingDocuments: [
            {
              documentId: "PROC-incidentes-staging-2026-03-18",
              filename: "PROC-incidentes-staging.docx",
              score: 0.91,
              snippet: "Procedimiento de escalamiento ante caída de staging...",
            },
            {
              documentId: "NEG-criterios-go-nogo-2026-01-29",
              filename: "POL-criterios-go-nogo.docx",
              score: 0.78,
              snippet: "Criterios de Go/No-Go para releases con riesgo...",
            },
          ],
        },
      },
    },
    {
      kind: "event",
      delayBefore: META_EVENT_MS,
      event: {
        event: "citation",
        data: {
          documentId: "PROC-incidentes-staging-2026-03-18",
          filename: "PROC-incidentes-staging.docx",
          section: "§2 Roles y responsabilidades",
          snippet: "El Test Lead notifica al stakeholder principal en < 15 min.",
        },
      },
    },
    {
      kind: "deltas",
      delayBefore: META_EVENT_MS,
      text: " Te recomiendo arrancar por el procedimiento autoritativo.",
    },
  ];
}

function ingestionScript(): ScriptedStep[] {
  return [
    {
      kind: "event",
      delayBefore: META_EVENT_MS,
      event: {
        event: "stage-change",
        data: { from: null, to: "I", reason: "ingestion-mode" },
      },
    },
    {
      kind: "deltas",
      delayBefore: META_EVENT_MS,
      text: "Recibí el archivo. Lo voy a clasificar.",
    },
    {
      kind: "event",
      delayBefore: META_EVENT_MS,
      event: {
        event: "classification",
        data: {
          category: "EST",
          documentType: "POL",
          confidence: 0.92,
          rationale: "Documento marcado como política oficial",
        },
      },
    },
    {
      kind: "deltas",
      delayBefore: META_EVENT_MS,
      text: " Necesito que confirmes el aprobador y la fecha.",
    },
  ];
}

function pickScript(mode: SendMessageParams["mode"]): ScriptedStep[] {
  switch (mode) {
    case "captura":
      return captureScript();
    case "consulta":
      return consultationScript();
    case "ingesta":
      return ingestionScript();
  }
}

const FINAL_TOKEN_USAGE = {
  inputTokens: 1240,
  outputTokens: 380,
  costUsd: 0.0124,
  model: "claude-sonnet-4-6",
};

export interface MockTransportOptions {
  /** Multiplicador para acelerar/ralentizar el stream — útil en tests. */
  speedFactor?: number;
}

export class MockMessageTransport implements MessageTransport {
  private readonly speedFactor: number;

  constructor(options: MockTransportOptions = {}) {
    this.speedFactor = options.speedFactor ?? 1;
  }

  sendMessage(params: SendMessageParams): AsyncIterable<AgentEvent> {
    const { mode, signal } = params;
    const messageId = `msg-${Date.now().toString(36)}-${Math.random()
      .toString(36)
      .slice(2, 8)}`;
    const script = pickScript(mode);
    const speedFactor = this.speedFactor;
    const startedAt = Date.now();
    let counter = 0;

    const nextId = () => nextEventId(messageId, counter++);
    const sleep = (ms: number) => delay(ms / speedFactor, signal);

    async function* generate(): AsyncGenerator<AgentEvent> {
      try {
        await sleep(META_EVENT_MS);
        yield {
          id: nextId(),
          event: "message-start",
          data: { messageId, sessionId: params.sessionId },
        };

        for (const step of script) {
          await sleep(step.delayBefore);
          if (step.kind === "event" && step.event) {
            yield { id: nextId(), ...step.event } as AgentEvent;
            continue;
          }
          if (step.kind === "deltas" && step.text) {
            for (const delta of splitInDeltas(step.text)) {
              await sleep(TEXT_DELTA_MS);
              yield {
                id: nextId(),
                event: "text-delta",
                data: { delta },
              };
            }
          }
        }

        await sleep(META_EVENT_MS);
        yield {
          id: nextId(),
          event: "token-usage",
          data: FINAL_TOKEN_USAGE,
        };

        await sleep(META_EVENT_MS);
        yield {
          id: nextId(),
          event: "message-end",
          data: { messageId, durationMs: Date.now() - startedAt },
        };
      } catch (err) {
        if (err instanceof AbortError) return;
        throw err;
      }
    }

    return generate();
  }
}
