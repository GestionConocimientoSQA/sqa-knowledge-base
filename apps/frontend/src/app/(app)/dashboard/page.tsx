"use client";

import { useQuery } from "@tanstack/react-query";
import { LayoutDashboard } from "lucide-react";
import { PageContainer } from "@/components/shared/page-container";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { listCategories } from "@/lib/api/documents";
import { GK_KPIS } from "@/lib/mocks/data";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function DashboardPage() {
  const { data: folders, isLoading, isError } = useQuery({
    queryKey: ["categories"],
    queryFn: listCategories,
  });

  return (
    <PageContainer>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="Capturas · 30 días"
          value={GK_KPIS.capturas30.value}
          delta={GK_KPIS.capturas30.delta}
          tone={GK_KPIS.capturas30.tone}
        />
        <StatCard
          label="Consultas · 30 días"
          value={GK_KPIS.consultas30.value}
          delta={GK_KPIS.consultas30.delta}
          tone={GK_KPIS.consultas30.tone}
        />
        <StatCard
          label="Finalización"
          value={GK_KPIS.finalizacion.value}
          delta={GK_KPIS.finalizacion.delta}
          tone={GK_KPIS.finalizacion.tone}
        />
        <StatCard
          label="Sin resultado"
          value={GK_KPIS.sinResultado.value}
          delta={GK_KPIS.sinResultado.delta}
          tone={GK_KPIS.sinResultado.tone}
        />
        <StatCard
          label="Autoritativos"
          value={GK_KPIS.autoritativos.value}
          delta={GK_KPIS.autoritativos.delta}
          tone={GK_KPIS.autoritativos.tone}
        />
        <StatCard
          label="Score promedio"
          value={GK_KPIS.scorePromedio.value}
          delta={GK_KPIS.scorePromedio.delta}
          tone={GK_KPIS.scorePromedio.tone}
        />
      </div>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Salud por carpeta temática</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : isError || !folders ? (
            <EmptyState
              icon={LayoutDashboard}
              title="No se pudieron cargar las carpetas"
              description="Reintentá la consulta en unos minutos."
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {folders.map((f) => (
                <div
                  key={f.code}
                  className="rounded-md border border-border bg-card p-4"
                >
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" className="font-mono">
                      {f.code}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      score {f.scoreAvg}
                    </span>
                  </div>
                  <div className="mt-2 font-display text-sm font-bold">
                    {f.label}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {f.docs} docs · {f.autoritativos} autoritativos
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </PageContainer>
  );
}
