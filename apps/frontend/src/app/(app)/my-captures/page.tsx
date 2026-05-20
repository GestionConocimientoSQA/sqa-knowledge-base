"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Mic } from "lucide-react";
import { PageContainer } from "@/components/shared/page-container";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { DocumentCard } from "@/components/explorer/document-card";
import { MyCapturesSummary } from "@/components/dashboard/my-captures-summary";
import { useAuth } from "@/lib/auth/auth-provider";
import { listMyCaptures } from "@/lib/api/documents";

export default function MyCapturesPage() {
  const { user, isLoading: authLoading } = useAuth();

  const { data, isLoading } = useQuery({
    queryKey: ["my-captures", user?.oid ?? null],
    queryFn: () => listMyCaptures(user!.oid),
    enabled: Boolean(user?.oid),
  });

  if (authLoading || !user) {
    return (
      <PageContainer>
        <Skeleton className="mb-3 h-8 w-1/3" />
        <Skeleton className="mb-6 h-4 w-1/2" />
        <Skeleton className="h-24 w-full" />
      </PageContainer>
    );
  }

  const items = data?.items ?? [];
  const stats = data?.stats;
  const empty = !isLoading && items.length === 0;

  return (
    <PageContainer>
      <div className="mb-6">
        <div className="eyebrow">Mi catálogo personal</div>
        <h2 className="font-display text-2xl font-extrabold">
          Mis capturas
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Documentos que capturaste y métricas agregadas de tu aporte al KB.
        </p>
      </div>

      <MyCapturesSummary stats={stats} isLoading={isLoading} />

      <div className="mt-8">
        <div className="mb-3 flex items-baseline justify-between">
          <h3 className="font-display text-lg font-bold">Tus documentos</h3>
          {!empty && (
            <span className="text-[12px] text-muted-foreground" aria-live="polite">
              <span className="font-mono">{items.length}</span>{" "}
              {items.length === 1 ? "documento" : "documentos"}
            </span>
          )}
        </div>

        {isLoading ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        ) : empty ? (
          <EmptyState
            icon={Mic}
            title="Aún no capturaste nada"
            description="Iniciá una conversación en modo A para registrar tu primer aprendizaje."
            action={
              <Button asChild variant="default">
                <Link href={"/chat?mode=captura" as never}>
                  <Mic className="h-4 w-4" />
                  Iniciar captura
                </Link>
              </Button>
            }
          />
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            {items.map((d) => (
              <DocumentCard key={d.id} document={d} />
            ))}
          </div>
        )}
      </div>
    </PageContainer>
  );
}
