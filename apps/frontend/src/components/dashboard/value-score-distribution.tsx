"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";
import type { DocumentItem } from "@/types/domain";

interface ValueScoreDistributionProps {
  documents: DocumentItem[];
}

interface Bucket {
  range: string;
  count: number;
  tone: "low" | "mid" | "high";
}

/**
 * Buckets de score por rango de 1 punto. El último bucket incluye 5.0
 * exacto. `tone` controla el color visual — pasivo a buenos scores.
 */
function buildBuckets(documents: DocumentItem[]): Bucket[] {
  const ranges: Bucket[] = [
    { range: "1.0–1.9", count: 0, tone: "low" },
    { range: "2.0–2.9", count: 0, tone: "low" },
    { range: "3.0–3.9", count: 0, tone: "mid" },
    { range: "4.0–4.9", count: 0, tone: "high" },
    { range: "5.0", count: 0, tone: "high" },
  ];
  for (const d of documents) {
    const s = d.score;
    if (s >= 5.0) ranges[4]!.count++;
    else if (s >= 4.0) ranges[3]!.count++;
    else if (s >= 3.0) ranges[2]!.count++;
    else if (s >= 2.0) ranges[1]!.count++;
    else ranges[0]!.count++;
  }
  return ranges;
}

const TONE_COLOR: Record<Bucket["tone"], string> = {
  low: "#EF4444",
  mid: "#EAB308",
  high: "#10B981",
};

/**
 * Distribución del valueScore (1-5) del catálogo en buckets visuales.
 * Permite a GK Lead detectar la salud agregada del KB y a Owner ver
 * dónde concentrar esfuerzo de mejora.
 */
export function ValueScoreDistribution({
  documents,
}: ValueScoreDistributionProps) {
  const buckets = useMemo(() => buildBuckets(documents), [documents]);
  const hasData = buckets.some((b) => b.count > 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <BarChart3 className="h-4 w-4 text-sqa-naranja" aria-hidden />
          Distribución de score
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <EmptyState
            icon={BarChart3}
            title="Sin documentos"
            description="No hay scores para graficar todavía."
            className="border-0 py-4"
          />
        ) : (
          <div
            className="h-72 w-full"
            role="img"
            aria-label="Gráfico de barras con la cantidad de documentos por rango de score (1-5)"
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={buckets} margin={{ top: 10, right: 10, bottom: 0, left: -10 }}>
                <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" />
                <XAxis
                  dataKey="range"
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                  tickLine={false}
                />
                <Tooltip
                  formatter={(value: number) => [`${value} docs`, "Cantidad"]}
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  cursor={{ fill: "hsl(var(--muted) / 0.3)" }}
                />
                <Bar
                  dataKey="count"
                  isAnimationActive={false}
                  radius={[4, 4, 0, 0]}
                >
                  {buckets.map((b) => (
                    <Cell key={b.range} fill={TONE_COLOR[b.tone]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export { buildBuckets as __buildBucketsForTests };
