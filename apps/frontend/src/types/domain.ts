// === Roles ===
// Tres roles según la matriz operativa actual (2026-05-19): Capturador
// (Colaborador), Owner de carpeta, GK Lead. El antiguo "Curador" desaparece
// como rol de login — en Fase 2 será una asignación por carpeta que hace el
// Owner, no un usuario propio.
//
// Fase 9.1 (TODO — frontend pending para 9.6/9.7/9.8): el backend ya migró
// a un modelo de 2 ejes (`colaborador | gklead` global + `project_owner |
// member` per-proyecto). El frontend mantiene los 3 roles legacy en wire
// y mocks mientras no exista el selector global de proyecto activo. La
// migración se hace cuando se cablea Zustand + selector en navbar.
export type RoleId = "capturador" | "owner" | "gklead";

/** Rol per-proyecto (Fase 9). Wired completo en 9.6/9.7/9.8. */
export type ProjectMemberRole = "project_owner" | "member";

// === Proyectos multi-tenant (Fase 9) ===

/** Proyecto del KB. Cada proyecto tiene su propio knowledge aislado. */
export interface Project {
  id: string;
  slug: string;
  name: string;
  description: string;
  ownerOid: string;
  createdAt: string;
  archivedAt: string | null;
}

/** Membresía usuario↔proyecto. */
export interface ProjectMember {
  projectId: string;
  userOid: string;
  role: ProjectMemberRole;
  addedAt: string;
}

export interface Role {
  id: RoleId;
  label: string;
  sub: string;
  icon: string;
}

// === Usuario autenticado ===
export interface AuthUser {
  oid: string; // Entra Object ID
  email: string;
  name: string;
  roleId: RoleId;
  isAdmin: boolean;
}

// === Carpeta temática ===
export type CategoryCode =
  | "PROC"
  | "TEC"
  | "ARQ"
  | "HERR"
  | "NEG"
  | "ENV"
  | "EST"
  | "CONT";

export interface Category {
  code: CategoryCode;
  label: string;
  docs: number;
  vigentes: number;
  autoritativos: number;
  scoreAvg: number;
  obsolescencia: number;
}

// === Tipo de documento ===
export type DocTypeCode =
  | "POL"
  | "PROC"
  | "GUIA"
  | "INST"
  | "SERV"
  | "MTEC"
  | "ACEL"
  | "UEN"
  | "ARCL"
  | "FORM"
  | "PRES";

export interface DocType {
  code: DocTypeCode;
  label: string;
}

// === Estados ===
export type DocStatus =
  | "borrador"
  | "generado"
  | "en-revision"
  | "aprobado"
  | "vigente"
  | "obsoleto"
  | "reemplazado"
  | "archivado";

// === Documento ===
export interface DocumentItem {
  id: string;
  titulo: string;
  carpeta: CategoryCode;
  tipo: DocTypeCode;
  autoritativo: boolean;
  estado: DocStatus;
  autor: string;
  /** Entra Object ID del autor; en Fase 1 se llena del JWT. */
  autorOid?: string;
  rol: string;
  fecha: string;
  revision: string;
  version: string;
  citas: number;
  score: number;
  anonimizado: boolean;
  fragmentos: number;
  paginas: number;
  formato: string;
  aprobador?: string;
  fechaAprobacion?: string;
  tags: string[];
}

// === Detalle de documento (Explorer 7.3) ===

/**
 * Citación recibida por un documento desde otra pieza del KB.
 * El backend Fase 3 (RAG) la genera al indexar; este shape es el contrato
 * que el endpoint `GET /documents/{id}` debe respetar.
 */
export interface IncomingCitation {
  sourceDocId: string;
  sourceTitle: string;
  sourceFolder: CategoryCode;
  section: string;
  snippet: string;
  /** ISO date de cuándo se registró la citación (al indexar el doc origen). */
  citedAt: string;
}

export interface DocumentDetail extends DocumentItem {
  /** Citaciones recibidas desde otros docs del KB. */
  incomingCitations: IncomingCitation[];
  /** Resumen ejecutivo del doc (primer párrafo del content). */
  resumen: string;
}

// === Búsqueda y filtros (Explorer 7.2) ===

export type DocumentSortBy =
  | "relevance"
  | "date_desc"
  | "score_desc"
  | "citations_desc";

/**
 * Filtros del catálogo. Todos opcionales — `undefined` significa "no filtrar".
 * Listas vacías (`[]`) también significan "no filtrar" (alias semántico).
 * El contrato es estable: el backend Fase 1 lo recibe como query params.
 */
export interface DocumentSearchFilters {
  carpetas?: CategoryCode[];
  tipos?: DocTypeCode[];
  estados?: DocStatus[];
  autoritativo?: boolean;
  anonimizado?: boolean;
  /** Score mínimo inclusivo (escala 1.0–5.0). */
  minScore?: number;
  /** ISO date (YYYY-MM-DD). Filtra `fecha >= dateFrom`. */
  dateFrom?: string;
  /** ISO date (YYYY-MM-DD). Filtra `fecha <= dateTo`. */
  dateTo?: string;
  /** Filtra por `autorOid` exacto — usado por `/my-captures`. */
  autorOid?: string;
}

export interface DocumentSearchParams {
  /** Texto libre. Backend Fase 3 lo resuelve con hybrid search. */
  query?: string;
  filters?: DocumentSearchFilters;
  page?: number;
  limit?: number;
  sortBy?: DocumentSortBy;
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}

// === Dashboard interactivo (7.4) ===

/**
 * Tema "caliente" del KB: alta demanda de consulta. Si `isGap=true` el tema
 * tiene queries pero pocas/ninguna citación → señal de contenido faltante.
 * Lo genera el backend Fase 1 con queries agregadas; en Fase 3 mejora con
 * clustering vectorial.
 */
export interface HotTopic {
  topic: string;
  queries30d: number;
  citationCount: number;
  isGap: boolean;
}

export type RecentActivityType =
  | "captura"
  | "ingesta"
  | "consulta"
  | "taxonomia";

export interface RecentActivityItem {
  id: string;
  type: RecentActivityType;
  actor: { oid: string; name: string };
  at: string;
  summary: string;
  /** Deep-link opcional al recurso afectado (doc, sesión, taxonomía). */
  refUrl?: string;
}

// === My captures (7.5) ===

export interface MyCapturesStats {
  totalCaptures: number;
  totalCitationsReceived: number;
  avgScore: number;
  /** ISO date de la última captura del usuario, o null si nunca capturó. */
  lastCapturedAt: string | null;
}

export interface MyCapturesResult {
  items: DocumentItem[];
  stats: MyCapturesStats;
}

// === Modo de sesión ===
export type SessionMode = "captura" | "consulta" | "ingesta";

// === Etapas del agente ===
export interface Stage {
  id: number;
  label: string;
  short: string;
  icon: string;
}

// === Mensaje de chat ===
export interface ChatMessage {
  stage: number;
  who: "agent" | "user";
  text: string;
  chips?: string[];
  relatedDocs?: string[];
}

// === Scoring de captura ===
export interface CaptureScore {
  especificidad: number;
  profundidad: number;
  reutilizabilidad: number;
  unicidad: number;
}

// === Ingesta (modo C) — alineado al wire del backend Fase 4 (camelCase) ===

/** Estados del item de ingesta. Espejo del `IngestionStatus` del backend. */
export type IngestionStatus =
  | "pendiente-metadata"
  | "listo"
  | "en-revision"
  | "aprobado"
  | "rechazado"
  | "indexado";

export interface IngestionItem {
  id: string;
  filename: string;
  sizeBytes: number;
  paginas: number;
  carpetaSugerida: CategoryCode | null;
  tipoSugerido: DocTypeCode | null;
  aprobadorOid: string | null;
  aprobadorName: string;
  fechaAprobacion: string | null;
  fuenteOriginal: string;
  version: string;
  status: IngestionStatus;
  uploadedByOid: string;
  uploadedAt: string;
  blobPath: string | null;
  errorDetail: string | null;
}

/** Metadata de trazabilidad para aprobar un item (POST approve). */
export interface TraceabilityInput {
  approvedBy: string;
  approvalDate: string;
  sourceOrigin: string;
  version: string;
  category: CategoryCode;
  documentType: DocTypeCode;
}

