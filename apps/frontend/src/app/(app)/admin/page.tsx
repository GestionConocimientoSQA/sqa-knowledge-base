"use client";

import { Shield } from "lucide-react";
import { PageContainer } from "@/components/shared/page-container";
import { EmptyState } from "@/components/shared/empty-state";
import { useAuth } from "@/lib/auth/auth-provider";

export default function AdminPage() {
  const { user } = useAuth();

  if (!user?.isAdmin) {
    return (
      <PageContainer>
        <EmptyState
          icon={Shield}
          title="Acceso restringido"
          description="Esta sección está disponible solo para roles GK Lead y Owner."
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <EmptyState
        icon={Shield}
        title="Taxonomía y gobierno"
        description="Gestión de usuarios, taxonomía, skills y audit log. Disponible en Fase 9."
      />
    </PageContainer>
  );
}
