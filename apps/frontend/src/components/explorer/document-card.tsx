"use client";

import Link from "next/link";
import { BadgeCheck, EyeOff, Sparkles } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { DocumentItem } from "@/types/domain";

interface DocumentCardProps {
  document: DocumentItem;
}

/**
 * Card de documento del catálogo. Es interactivo (link al detalle),
 * accesible y reusable entre Explorer y MyCaptures (Fase 7.5).
 */
export function DocumentCard({ document: d }: DocumentCardProps) {
  return (
    <Link
      href={`/explorer/${d.id}` as never}
      className="block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      aria-label={`Abrir ${d.titulo}`}
    >
      <Card className="p-5 transition-colors hover:border-sqa-naranja/40">
        <div className="flex flex-wrap items-center gap-2">
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
          {d.estado !== "vigente" && (
            <Badge variant="outline" className="capitalize">
              {d.estado.replace("-", " ")}
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
            Score {d.score.toFixed(1)}
          </span>
          <span className="text-muted-foreground">
            {d.citas} citas · {d.fragmentos} fragmentos
          </span>
        </div>
      </Card>
    </Link>
  );
}
