"use client";

/**
 * Página /ingestion — cola de ingesta de documentos (Fase 8.3).
 *
 * Gated a roles que pueden gobernar el KB (Owner / GK Lead). Compone:
 *   - UploadZone para subir nuevos documentos al pipeline.
 *   - Tabs por agrupación de estado (Pendientes / En revisión /
 *     Completados / Rechazados).
 *   - IngestionQueue por tab, con auto-refresh cada 15 s.
 *
 * La aprobación full (formulario de trazabilidad) vive en
 * `/ingestion/[itemId]` (Fase 8.4) — desde acá se linkea con "Revisar".
 */
import { Shield } from "lucide-react";

import { IngestionQueue } from "@/components/ingestion/ingestion-queue";
import { UploadZone } from "@/components/ingestion/upload-zone";
import { EmptyState } from "@/components/shared/empty-state";
import { PageContainer } from "@/components/shared/page-container";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/lib/auth/auth-provider";
import type { IngestionStatus } from "@/types/domain";

interface TabSpec {
  value: string;
  label: string;
  statuses: IngestionStatus[];
  emptyMessage: string;
}

const TABS: TabSpec[] = [
  {
    value: "pendientes",
    label: "Pendientes",
    statuses: ["pendiente-metadata", "listo"],
    emptyMessage: "No hay items pendientes de clasificación.",
  },
  {
    value: "en-revision",
    label: "En revisión",
    statuses: ["en-revision"],
    emptyMessage: "No hay items esperando revisión.",
  },
  {
    value: "completados",
    label: "Completados",
    statuses: ["aprobado", "indexado"],
    emptyMessage: "Todavía no hay items indexados.",
  },
  {
    value: "rechazados",
    label: "Rechazados",
    statuses: ["rechazado"],
    emptyMessage: "Ningún item fue rechazado.",
  },
];

export default function IngestionPage() {
  const { user } = useAuth();

  if (!user?.isAdmin) {
    return (
      <PageContainer>
        <EmptyState
          icon={Shield}
          title="Acceso restringido"
          description="La cola de ingesta está disponible solo para Owner de carpeta y GK Lead."
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="mb-6">
        <div className="eyebrow">Gobierno del KB</div>
        <h2 className="font-display text-2xl font-extrabold">Cola de ingesta</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Subí documentos para incorporarlos al KB. Clasificá, revisá y aprobá
          con trazabilidad — la indexación corre en background.
        </p>
      </div>

      <section aria-labelledby="upload-heading" className="mb-8">
        <h3 id="upload-heading" className="sr-only">
          Subir documentos
        </h3>
        <UploadZone />
      </section>

      <section aria-labelledby="queue-heading">
        <h3
          id="queue-heading"
          className="mb-3 font-display text-lg font-bold"
        >
          Cola
        </h3>

        <Tabs defaultValue="pendientes">
          <TabsList aria-label="Filtros por estado">
            {TABS.map((tab) => (
              <TabsTrigger key={tab.value} value={tab.value}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
          {TABS.map((tab) => (
            <TabsContent key={tab.value} value={tab.value} className="mt-4">
              <IngestionQueue
                statuses={tab.statuses}
                emptyMessage={tab.emptyMessage}
              />
            </TabsContent>
          ))}
        </Tabs>
      </section>
    </PageContainer>
  );
}
