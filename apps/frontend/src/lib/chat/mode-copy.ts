/**
 * SSOT de copy + iconografía + descripciones para los 3 modos del agente.
 *
 * Aislar este mapping en su propio módulo permite reusarlo desde el selector,
 * el header de sesión, el sidebar de sesiones (sub-fase 6.5) y el indicador
 * de modo en URLs compartidas — sin duplicar literales.
 */
import { Inbox, Mic, SearchCode, type LucideIcon } from "lucide-react";
import type { SessionMode } from "@/types/domain";

export interface ModeCopy {
  mode: SessionMode;
  title: string;
  short: string;
  description: string;
  cta: string;
  icon: LucideIcon;
  /** Letra de modo según ROADMAP §10 (A captura, B consulta, C ingesta). */
  letter: "A" | "B" | "C";
}

export const MODE_COPY: Record<SessionMode, ModeCopy> = {
  captura: {
    mode: "captura",
    title: "Captura conversacional",
    short: "Captura",
    description:
      "Aria te guía por las etapas 0-5 para dejar registro estructurado del conocimiento que estás resolviendo.",
    cta: "Iniciar nueva captura",
    icon: Mic,
    letter: "A",
  },
  consulta: {
    mode: "consulta",
    title: "Consulta a la base",
    short: "Consulta",
    description:
      "Preguntá en lenguaje natural. Aria responde solo con citaciones de documentos indexados y autoritativos.",
    cta: "Iniciar nueva consulta",
    icon: SearchCode,
    letter: "B",
  },
  ingesta: {
    mode: "ingesta",
    title: "Ingesta aprobada",
    short: "Ingesta",
    description:
      "Subí un documento oficial validado. Aria lo clasifica, anonimiza y propone su trazabilidad.",
    cta: "Iniciar nueva ingesta",
    icon: Inbox,
    letter: "C",
  },
};

const VALID_MODES = ["captura", "consulta", "ingesta"] as const satisfies readonly SessionMode[];

export function isSessionMode(value: unknown): value is SessionMode {
  return typeof value === "string" && (VALID_MODES as readonly string[]).includes(value);
}

export const ORDERED_MODES: SessionMode[] = ["captura", "consulta", "ingesta"];
