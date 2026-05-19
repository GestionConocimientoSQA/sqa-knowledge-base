"use client";

import { MessageSquareDashed } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { PageContainer } from "@/components/shared/page-container";

export default function SessionNotFound() {
  return (
    <PageContainer>
      <EmptyState
        icon={MessageSquareDashed}
        title="Sesión no encontrada"
        description="Esta conversación fue eliminada o nunca existió. Podés iniciar una nueva desde el selector."
        action={
          <Button asChild variant="accent">
            <Link href="/chat">Volver al selector</Link>
          </Button>
        }
      />
    </PageContainer>
  );
}
