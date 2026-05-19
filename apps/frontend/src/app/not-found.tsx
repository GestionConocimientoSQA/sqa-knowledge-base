import Link from "next/link";
import { FileQuestion } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";

export default function NotFound() {
  return (
    <div className="grid min-h-screen place-items-center bg-background p-6">
      <EmptyState
        icon={FileQuestion}
        title="Página no encontrada"
        description="La ruta que buscás no existe o se movió."
        action={
          <Button asChild>
            <Link href="/dashboard">Volver al panel</Link>
          </Button>
        }
      />
    </div>
  );
}
