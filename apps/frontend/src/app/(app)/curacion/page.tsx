import { ShieldCheck } from "lucide-react";
import { PageContainer } from "@/components/shared/page-container";
import { EmptyState } from "@/components/shared/empty-state";

export default function CuracionPage() {
  return (
    <PageContainer>
      <EmptyState
        icon={ShieldCheck}
        title="Bandeja de curaduría"
        description="Promociones a autoritativo, obsolescencia y conflictos. Disponible en Fase 7."
      />
    </PageContainer>
  );
}
