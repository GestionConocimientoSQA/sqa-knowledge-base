/**
 * Discriminated union de los 14 eventos SSE definidos en ROADMAP §15.2.
 *
 * El nombre del evento usa la convención `kebab-case` del wire format SSE.
 * El campo `id` permite reconexión con `Last-Event-ID` (Fase 6 backend real).
 *
 * En modo mock (sub-fase 6.1) los eventos se generan localmente; en backend
 * real se parsean desde `text/event-stream`. La forma de los payloads es
 * idéntica para que el swap mock→real sea cambio de implementación, no de
 * contrato (DIP).
 */
import type {
  AgentErrorPayload,
  CitationPayload,
  ClassificationPayload,
  DocumentArtifactPayload,
  KbSearchResultPayload,
  MessageEndPayload,
  MessageStartPayload,
  PingPayload,
  ScoringPayload,
  StageChangePayload,
  TextDeltaPayload,
  TokenUsagePayload,
  ToolResultPayload,
  ToolUsePayload,
} from "@/types/agent";

interface BaseEvent<TName extends string, TData> {
  id: string;
  event: TName;
  data: TData;
}

export type MessageStartEvent = BaseEvent<"message-start", MessageStartPayload>;
export type StageChangeEvent = BaseEvent<"stage-change", StageChangePayload>;
export type ClassificationEvent = BaseEvent<
  "classification",
  ClassificationPayload
>;
export type KbSearchResultEvent = BaseEvent<
  "kb-search-result",
  KbSearchResultPayload
>;
export type TextDeltaEvent = BaseEvent<"text-delta", TextDeltaPayload>;
export type ToolUseEvent = BaseEvent<"tool-use", ToolUsePayload>;
export type ToolResultEvent = BaseEvent<"tool-result", ToolResultPayload>;
export type CitationEvent = BaseEvent<"citation", CitationPayload>;
export type ScoringEvent = BaseEvent<"scoring", ScoringPayload>;
export type DocumentGeneratedEvent = BaseEvent<
  "document-generated",
  DocumentArtifactPayload
>;
export type TokenUsageEvent = BaseEvent<"token-usage", TokenUsagePayload>;
export type MessageEndEvent = BaseEvent<"message-end", MessageEndPayload>;
export type AgentErrorEvent = BaseEvent<"error", AgentErrorPayload>;
export type PingEvent = BaseEvent<"ping", PingPayload>;

export type AgentEvent =
  | MessageStartEvent
  | StageChangeEvent
  | ClassificationEvent
  | KbSearchResultEvent
  | TextDeltaEvent
  | ToolUseEvent
  | ToolResultEvent
  | CitationEvent
  | ScoringEvent
  | DocumentGeneratedEvent
  | TokenUsageEvent
  | MessageEndEvent
  | AgentErrorEvent
  | PingEvent;

export type AgentEventName = AgentEvent["event"];
