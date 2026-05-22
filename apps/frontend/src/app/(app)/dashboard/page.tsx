"use client";

import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { PageContainer } from "@/components/shared/page-container";
import { StatCard } from "@/components/shared/stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { HotTopicsPanel } from "@/components/dashboard/hot-topics-panel";
import { RecentActivityFeed } from "@/components/dashboard/recent-activity-feed";
import { MyCapturesSummary } from "@/components/dashboard/my-captures-summary";
import {
  listCategories,
  listHotTopics,
  listMyCaptures,
  listRecentActivity,
  searchDocuments,
} from "@/lib/api/documents";
import { useAuth } from "@/lib/auth/auth-provider";
import { GK_KPIS } from "@/lib/mocks/data";

/**
 * Charts dynamic-imported para sacar recharts (~80 kB) del bundle inicial.
 * Solo se carga cuando el usuario aterriza en /dashboard como admin (los
 * Capturadores ni siquiera bajan el chunk). El skeleton mantiene la
 * altura del card mientras llega.
 */
const DocsByCategoryChart = dynamic(
  () =>
    import("@/components/dashboard/docs-by-category-chart").then(
      (m) => m.DocsByCategoryChart,
    ),
  {
    ssr: false,
    loading: () => <Skeleton className="h-72 w-full" />,
  },
);

const ValueScoreDistribution = dynamic(
  () =>
    import("@/components/dashboard/value-score-distribution").then(
      (m) => m.ValueScoreDistribution,
    ),
  {
    ssr: false,
    loading: () => <Skeleton className="h-72 w-full" />,
  },
);

/** 5 minutos en ms — usado como refetchInterval del dashboard. */
const FIVE_MINUTES_MS = 5 * 60 * 1000;

export default function DashboardPage() {
  const { user, isLoading: authLoading } = useAuth();
  const isAdmin = Boolean(user?.isAdmin);

  // Capturador → vista personal liviana.
  if (!authLoading && user && !isAdmin) {
    return <CapturadorDashboard userOid={user.oid} />;
  }

  return <AdminDashboard />;
}

function AdminDashboard() {
  const folders = useQuery({
    queryKey: ["dashboard", "categories"],
    queryFn: listCategories,
    refetchInterval: FIVE_MINUTES_MS,
  });

  const allDocs = useQuery({
    queryKey: ["dashboard", "all-docs"],
    queryFn: () => searchDocuments({ limit: 100 }),
    refetchInterval: FIVE_MINUTES_MS,
  });

  const hot = useQuery({
    queryKey: ["dashboard", "hot-topics"],
    queryFn: () => listHotTopics({ limit: 6 }),
    refetchInterval: FIVE_MINUTES_MS,
  });

  const activity = useQuery({
    queryKey: ["dashboard", "recent-activity"],
    queryFn: () => listRecentActivity({ limit: 8 }),
    refetchInterval: FIVE_MINUTES_MS,
  });

  return (
    <PageContainer>
      <KpiRow />

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        {folders.isLoading ? (
          <Skeleton className="h-72 w-full" />
        ) : (
          <DocsByCategoryChart folders={folders.data ?? []} />
        )}
        {allDocs.isLoading ? (
          <Skeleton className="h-72 w-full" />
        ) : (
          <ValueScoreDistribution documents={allDocs.data?.items ?? []} />
        )}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <HotTopicsPanel topics={hot.data} isLoading={hot.isLoading} />
        <RecentActivityFeed items={activity.data} isLoading={activity.isLoading} />
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Salud por carpeta temática</CardTitle>
        </CardHeader>
        <CardContent>
          {folders.isLoading ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {folders.data?.map((f) => (
                <div
                  key={f.code}
                  className="rounded-md border border-border bg-card p-4"
                >
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" className="font-mono">
                      {f.code}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      score {f.scoreAvg.toFixed(1)}
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

function KpiRow() {
  return (
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
  );
}

function CapturadorDashboard({ userOid }: { userOid: string }) {
  const my = useQuery({
    queryKey: ["dashboard", "my-captures", userOid],
    queryFn: () => listMyCaptures(userOid),
    refetchInterval: FIVE_MINUTES_MS,
  });

  const activity = useQuery({
    queryKey: ["dashboard", "recent-activity"],
    queryFn: () => listRecentActivity({ limit: 6 }),
    refetchInterval: FIVE_MINUTES_MS,
  });

  return (
    <PageContainer>
      <div className="mb-6">
        <div className="eyebrow">Tu actividad</div>
        <h2 className="font-display text-2xl font-extrabold">Resumen personal</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Tus capturas, citas recibidas y score promedio en la base de conocimiento.
        </p>
      </div>

      <MyCapturesSummary stats={my.data?.stats} isLoading={my.isLoading} />

      <div className="mt-6">
        <RecentActivityFeed items={activity.data} isLoading={activity.isLoading} />
      </div>
    </PageContainer>
  );
}
