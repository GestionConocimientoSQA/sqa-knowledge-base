/**
 * Etiquetas legibles de la taxonomía (Fase 8.4).
 *
 * Espejo de `documents/doc_types.py` del backend. La fuente de verdad sigue
 * siendo el backend (los códigos viajan por la wire en mayúsculas); este
 * módulo solo provee los labels para la UI.
 *
 * En Fase 9 (multi-tenant) la taxonomía pasa a ser por-proyecto con
 * herencia + override: estos labels seguirán siendo el fallback global.
 */
import type { CategoryCode, DocTypeCode } from "@/types/domain";

export const CATEGORY_LABELS: Record<CategoryCode, string> = {
  PROC: "Procesos de Pruebas",
  TEC: "Conocimiento Técnico",
  ARQ: "Arquitectura y Decisiones Técnicas",
  HERR: "Herramientas y Accesos",
  NEG: "Reglas de Negocio del Cliente",
  ENV: "Ambientes y Datos de Prueba",
  EST: "Estrategia y Metodología de Pruebas",
  CONT: "Contactos y Estructura del Cliente",
};

export const DOC_TYPE_LABELS: Record<DocTypeCode, string> = {
  POL: "Política",
  PROC: "Procedimiento",
  GUIA: "Guía",
  INST: "Instructivo",
  SERV: "Servicio",
  MTEC: "Memoria técnica",
  ACEL: "Acelerador",
  UEN: "UEN",
  ARCL: "Arquetipo cliente",
  FORM: "Formato",
  PRES: "Presentación",
};

export const CATEGORY_CODES = Object.keys(CATEGORY_LABELS) as CategoryCode[];
export const DOC_TYPE_CODES = Object.keys(DOC_TYPE_LABELS) as DocTypeCode[];

export function categoryLabel(code: CategoryCode | null | undefined): string {
  if (!code) return "—";
  return CATEGORY_LABELS[code] ?? code;
}

export function docTypeLabel(code: DocTypeCode | null | undefined): string {
  if (!code) return "—";
  return DOC_TYPE_LABELS[code] ?? code;
}
