import { Upload } from "lucide-react";
import { PageContainer } from "@/components/shared/page-container";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";

export default function IngestionPage() {
  return (
    <PageContainer>
      <EmptyState
        icon={Upload}
        title="Cola de ingesta"
        description="UI completa para clasificar, anonimizar y aprobar documentos oficiales. Disponible en Fase 8."
        action={<Button disabled>Subir documento</Button>}
      />
    </PageContainer>
  );
}
