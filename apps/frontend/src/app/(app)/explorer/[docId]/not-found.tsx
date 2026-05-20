import Link from "next/link";
import { ArrowLeft, LibraryBig } from "lucide-react";
import { PageContainer } from "@/components/shared/page-container";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";

export default function DocumentNotFound() {
  return (
    <PageContainer>
      <EmptyState
        icon={LibraryBig}
        title="Documento no encontrado"
        description="El documento que buscás no existe o fue archivado. Volvé al catálogo para explorar otros."
        action={
          <Button asChild variant="outline">
            <Link href={"/explorer" as never}>
              <ArrowLeft className="h-4 w-4" />
              Volver al catálogo
            </Link>
          </Button>
        }
      />
    </PageContainer>
  );
}
