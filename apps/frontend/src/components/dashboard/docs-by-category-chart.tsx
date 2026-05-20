"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";
import { PieChart as PieIcon } from "lucide-react";
import type { Category } from "@/types/domain";

interface DocsByCategoryChartProps {
  folders: Category[];
}

/**
 * Mapa estable de color por carpeta. Tomado de los acentos de la paleta
 * SQA. Si se agrega una carpeta sin entrada, recharts asigna el primer
 * fallback gris.
 */
const COLOR_BY_FOLDER: Record<string, string> = {
  PROC: "#F26C2A",
  TEC: "#3B82F6",
  ARQ: "#8B5CF6",
  HERR: "#10B981",
  NEG: "#EAB308",
  ENV: "#06B6D4",
  EST: "#EC4899",
  CONT: "#94A3B8",
};

const FALLBACK_COLOR = "#94A3B8";

/**
 * Distribución de documentos por carpeta temática. Útil para que GK Lead
 * detecte desbalance del KB (ej: muchos docs en HERR vs pocos en EST).
 *
 * En backend Fase 3 los counts se actualizarán desde la vista materializada
 * `mv_dashboard_stats` (ROADMAP §7); por ahora vienen del mock-stub.
 */
export function DocsByCategoryChart({ folders }: DocsByCategoryChartProps) {
  const data = folders.filter((f) => f.docs > 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <PieIcon className="h-4 w-4 text-sqa-naranja" aria-hidden />
          Distribución por carpeta
        </CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <EmptyState
            icon={PieIcon}
            title="Sin datos"
            description="No hay documentos para graficar."
            className="border-0 py-4"
          />
        ) : (
          <div
            className="h-72 w-full"
            role="img"
            aria-label="Gráfico de torta con la distribución de documentos por carpeta temática"
          >
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  dataKey="docs"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  innerRadius={55}
                  paddingAngle={2}
                  label={(entry: { label?: string; docs?: number }) =>
                    `${entry.label ?? ""} (${entry.docs ?? 0})`
                  }
                  labelLine={false}
                  isAnimationActive={false}
                >
                  {data.map((f) => (
                    <Cell
                      key={f.code}
                      fill={COLOR_BY_FOLDER[f.code] ?? FALLBACK_COLOR}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number, _name, payload) => {
                    const f = payload?.payload as Category | undefined;
                    return [
                      `${value} docs · ${f?.autoritativos ?? 0} autoritativos · score ${f?.scoreAvg ?? 0}`,
                      f?.label ?? "",
                    ];
                  }}
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
