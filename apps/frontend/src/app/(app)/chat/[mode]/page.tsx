"use client";

import { MessageSquarePlus } from "lucide-react";
import { notFound } from "next/navigation";
import { use } from "react";
import { PageContainer } from "@/components/shared/page-container";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import type { SessionMode } from "@/types/domain";

const VALID_MODES = ["captura", "consulta", "ingesta"] as const satisfies readonly SessionMode[];

const MODE_COPY: Record<SessionMode, { title: string; description: string }> = {
  captura: {
    title: "Iniciar captura conversacional",
    description:
      "Aria te guiará por las etapas 0–5 para dejar registro estructurado de conocimiento nuevo.",
  },
  consulta: {
    title: "Consultar la base",
    description:
      "Preguntá en lenguaje natural. Aria responde solo con citaciones de documentos indexados.",
  },
  ingesta: {
    title: "Ingerir documento aprobado",
    description:
      "Subí un documento oficial y Aria lo clasifica, anonimiza y propone su trazabilidad.",
  },
};

export default function ChatModePage({
  params,
}: {
  params: Promise<{ mode: string }>;
}) {
  const { mode } = use(params);
  if (!VALID_MODES.includes(mode as SessionMode)) notFound();
  const copy = MODE_COPY[mode as SessionMode];

  return (
    <PageContainer>
      <EmptyState
        icon={MessageSquarePlus}
        title={copy.title}
        description={copy.description}
        action={
          <Button variant="accent" disabled>
            Disponible en Fase 6
          </Button>
        }
      />
    </PageContainer>
  );
}
