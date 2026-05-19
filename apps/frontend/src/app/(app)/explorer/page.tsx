"use client";

import { useQuery } from "@tanstack/react-query";
import { LibraryBig, BadgeCheck, EyeOff, Sparkles } from "lucide-react";
import Link from "next/link";
import { PageContainer } from "@/components/shared/page-container";
import { EmptyState } from "@/components/shared/empty-state";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { listDocuments } from "@/lib/api/documents";

export default function ExplorerPage() {
  const { data: docs, isLoading, isError } = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
  });

  return (
    <PageContainer>
      <div className="mb-6 flex items-end justify-between">
        <div>
          <div className="eyebrow">Catálogo</div>
          <h2 className="font-display text-2xl font-extrabold">
            Documentos indexados
          </h2>
        </div>
        <span className="text-sm text-muted-foreground">
          {docs?.length ?? "—"} resultados
        </span>
      </div>

      {isLoading ? (
        <div className="grid gap-3 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : isError || !docs || docs.length === 0 ? (
        <EmptyState
          icon={LibraryBig}
          title="No hay documentos indexados todavía"
          description="Cuando capturen o ingieran su primer documento, aparecerá acá."
        />
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {docs.map((d) => (
            <Link
              key={d.id}
              href={`/explorer/${d.id}` as never}
              className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-lg"
            >
              <Card className="p-5 transition-colors hover:border-sqa-naranja/40">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono">
                    {d.carpeta}
                  </Badge>
                  <Badge variant="secondary" className="font-mono">
                    {d.tipo}
                  </Badge>
                  {d.autoritativo && (
                    <Badge variant="authoritative">
                      <BadgeCheck className="h-3 w-3" />
                      Autoritativo
                    </Badge>
                  )}
                  {d.anonimizado && (
                    <Badge variant="outline">
                      <EyeOff className="h-3 w-3" />
                      Anonimizado
                    </Badge>
                  )}
                </div>
                <h3 className="mt-3 font-display text-base font-bold leading-snug">
                  {d.titulo}
                </h3>
                <div className="mt-2 text-xs text-muted-foreground">
                  {d.autor} · {d.rol} · v{d.version} · {d.fecha}
                </div>
                <div className="mt-3 flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1 font-semibold text-success">
                    <Sparkles className="h-3 w-3" />
                    Score {d.score}
                  </span>
                  <span className="text-muted-foreground">
                    {d.citas} citas · {d.fragmentos} fragmentos
                  </span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </PageContainer>
  );
}
