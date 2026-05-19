/**
 * Tipos del dominio del agente conversacional Aria.
 *
 * Espejo del modelo definido en ROADMAP §13 (sessions/messages) y §15.2 (SSE).
 * Estos tipos representan el estado expuesto a la UI; no son DTOs del backend
 * (los DTOs se generarán desde OpenAPI en Fase 1 al cerrar el contrato).
 */
import type {
  CategoryCode,
  DocTypeCode,
  SessionMode,
} from "@/types/domain";

/**
 * ETAPAS del agente. Numéricas 0-5 para modo A (captura), strings para B y C.
 * Espejo de los módulos definidos en ROADMAP §10 (welcome, identification,
 * free_capture, deep_dive, validation, generation, consultation, ingestion).
 */
export type StageId = 0 | 1 | 2 | 3 | 4 | 5 | "C" | "I";

export interface StageDefinition {
  id: StageId;
  label: string;
  short: string;
  icon: string;
}

export type SessionStatus = "active" | "paused" | "completed" | "abandoned";

export type MessageRole = "user" | "agent" | "system";

export type MessageStatus = "pending" | "streaming" | "complete" | "error";

/**
 * Resumen de sesión que se muestra en el sidebar y listados.
 * El detalle completo (con mensajes) se obtiene aparte por `getMessages`.
 */
export interface AgentSessionSummary {
  id: string;
  mode: SessionMode;
  title: string;
  status: SessionStatus;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  currentStage: StageId | null;
}

export interface AgentSession extends AgentSessionSummary {
  ownerOid: string;
}

// === Payloads de los 14 SSE events (ROADMAP §15.2) ===

export interface MessageStartPayload {
  messageId: string;
  sessionId: string;
}

export interface StageChangePayload {
  from: StageId | null;
  to: StageId;
  reason: string;
}

export interface ClassificationPayload {
  category: CategoryCode;
  documentType: DocTypeCode;
  confidence: number;
  rationale?: string;
}

export interface KbSearchResultPayload {
  existingDocuments: KbSearchHit[];
}

export interface KbSearchHit {
  documentId: string;
  filename: string;
  score: number;
  snippet: string;
}

export interface TextDeltaPayload {
  delta: string;
}

export interface ToolUsePayload {
  tool: string;
  input: Record<string, unknown>;
}

export interface ToolResultPayload {
  tool: string;
  output: Record<string, unknown>;
}

export interface CitationPayload {
  documentId: string;
  filename: string;
  section: string;
  snippet: string;
}

export interface ScoringPayload {
  specificity: number;
  depth: number;
  reusability: number;
  uniqueness: number;
  valueScore: number;
}

export interface DocumentArtifactPayload {
  documentId: string;
  filename: string;
  downloadUrl: string;
  blobPath: string;
}

export interface TokenUsagePayload {
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
  model: string;
}

export interface MessageEndPayload {
  messageId: string;
  durationMs: number;
}

export type AgentErrorType =
  | "transport"
  | "model"
  | "validation"
  | "auth"
  | "rate-limit"
  | "internal";

export interface AgentErrorPayload {
  type: AgentErrorType;
  message: string;
  retryable: boolean;
}

export interface PingPayload {
  timestamp: string;
}

/**
 * Mensaje del agente o usuario tal como lo consume la UI.
 * Se construye incrementalmente desde los eventos SSE en el reducer.
 */
export interface AgentMessage {
  id: string;
  role: MessageRole;
  content: string;
  stage: StageId | null;
  status: MessageStatus;
  startedAt: string;
  endedAt: string | null;
  durationMs: number | null;
  classification: ClassificationPayload | null;
  citations: CitationPayload[];
  scoring: ScoringPayload | null;
  artifacts: DocumentArtifactPayload[];
  tokenUsage: TokenUsagePayload | null;
  error: AgentErrorPayload | null;
}

/**
 * Mensaje saliente del usuario hacia el agente.
 * `attachments` es una lista de IDs de attachments ya subidos al backend.
 */
export interface OutgoingMessage {
  content: string;
  attachments?: string[];
}

// === Attachments ===

export type AttachmentStatus = "uploading" | "uploaded" | "error";

export interface AttachmentMetadata {
  id: string;
  sessionId: string;
  filename: string;
  size: number;
  mimeType: string;
  status: AttachmentStatus;
  progress: number;
  uploadedAt: string;
  blobPath?: string;
  error?: string;
}
