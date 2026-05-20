"use client";

import Link from "next/link";
import { ArrowRight, Mic } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/shared/stat-card";
import { Skeleton } from "@/components/ui/skeleton";
import type { MyCapturesStats } from "@/types/domain";

interface MyCapturesSummaryProps {
  stats: MyCapturesStats | undefined;
  isLoading?: boolean;
}

/**
 * Resumen personal del Capturador. Muestra sus métricas sin exponer las
 * globales del KB (esas son para Owner/GK Lead). Linkea a `/my-captures`
 * (sub-fase 7.5) para detalle.
 */
export function MyCapturesSummary({ stats, isLoading }: MyCapturesSummaryProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  if (!stats) return null;

  const empty = stats.totalCaptures === 0;

  if (empty) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tus capturas</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Aún no tenés capturas registradas. Iniciá una conversación en modo A
            para empezar.
          </p>
          <Button asChild className="mt-3" variant="outline">
            <Link href={"/chat?mode=captura" as never}>
              <Mic className="h-4 w-4" />
              Iniciar captura
            </Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Mis capturas" value={stats.totalCaptures} tone="pass" />
        <StatCard
          label="Citas recibidas"
          value={stats.totalCitationsReceived}
          tone="pass"
        />
        <StatCard
          label="Score promedio"
          value={stats.avgScore.toFixed(2)}
          tone="pass"
        />
        <StatCard
          label="Última captura"
          value={stats.lastCapturedAt ?? "—"}
          tone="neutral"
        />
      </div>
      <div className="mt-4 flex justify-end">
        <Button asChild variant="ghost" size="sm">
          <Link href={"/my-captures" as never}>
            Ver todas mis capturas
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Button>
      </div>
    </>
  );
}
