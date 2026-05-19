// === Roles ===
// Tres roles según la matriz operativa actual (2026-05-19): Capturador
// (Colaborador), Owner de carpeta, GK Lead. El antiguo "Curador" desaparece
// como rol de login — en Fase 2 será una asignación por carpeta que hace el
// Owner, no un usuario propio.
export type RoleId = "capturador" | "owner" | "gklead";

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

// === Ingesta pendiente ===
export interface IngestionItem {
  id: string;
  filename: string;
  size: string;
  paginas: number;
  sugerido: { carpeta: CategoryCode; tipo: DocTypeCode };
  aprobador: string;
  fechaAprobacion: string;
  fuenteOriginal: string;
  version: string;
  estado: "pendiente-metadata" | "listo" | "duplicado";
  duplicadoDe?: string;
}

