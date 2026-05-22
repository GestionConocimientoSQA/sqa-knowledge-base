"use client";

import {
  CalendarDays,
  FileText,
  User,
  GitCommitVertical,
  ShieldCheck,
  Tag,
  Sparkles,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { DocumentDetail } from "@/types/domain";

interface DocumentMetaPanelProps {
  document: DocumentDetail;
}

/**
 * Panel de metadata visible debajo del header del detalle. Resume todos
 * los campos estructurales en formato definition-list para accesibilidad.
 */
export function DocumentMetaPanel({ document: d }: DocumentMetaPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Metadata</CardTitle>
      </CardHeader>
      <CardContent>
        {/*
         * Cada MetaField es un <div> hijo directo del <dl> con un <dt> y <dd>
         * adentro — axe acepta esa anidación (la regla permite <div> directos
         * dentro de <dl>). NO se mete un div entre el group div y el <dt>.
         */}
        <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
          <MetaField icon={User} label="Autor" value={`${d.autor} · ${d.rol}`} />
          <MetaField icon={GitCommitVertical} label="Versión" value={`v${d.version}`} />
          <MetaField icon={CalendarDays} label="Fecha" value={d.fecha} />
          <MetaField icon={CalendarDays} label="Última revisión" value={d.revision} />
          {d.aprobador && (
            <MetaField
              icon={ShieldCheck}
              label="Aprobado por"
              value={`${d.aprobador} · ${d.fechaAprobacion ?? "—"}`}
            />
          )}
          <MetaField
            icon={FileText}
            label="Formato"
            value={`${d.formato} · ${d.paginas} pág · ${d.fragmentos} fragmentos`}
          />
          <MetaField
            icon={Sparkles}
            label="Score"
            value={`${d.score.toFixed(1)} / 5 · ${d.citas} citas recibidas`}
          />
        </dl>

        {d.tags.length > 0 && (
          <>
            <Separator className="my-4" />
            <div>
              <div className="mb-2 flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
                <Tag className="h-3.5 w-3.5" aria-hidden />
                Tags
              </div>
              <div className="flex flex-wrap gap-1.5" aria-label="Tags del documento">
                {d.tags.map((tag) => (
                  <Badge key={tag} variant="outline" className="font-mono text-[11px]">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

interface MetaFieldProps {
  icon: typeof User;
  label: string;
  value: string;
}

function MetaField({ icon: Icon, label, value }: MetaFieldProps) {
  // Estructura: <div> (hijo directo del <dl>) contiene icon + <dt> + <dd>.
  // El icono va absoluto-flotante a la izquierda con un padding-left en el
  // <dt>/<dd> para no insertar un nodo no-permitido entre <dl> y <dt>/<dd>.
  return (
    <div className="relative pl-5">
      <Icon
        className="absolute left-0 top-0.5 h-3.5 w-3.5 text-muted-foreground"
        aria-hidden
      />
      <dt className="text-[11px] uppercase tracking-wider text-muted-foreground">
        {label}
      </dt>
      <dd className="font-display text-[13px] font-semibold">{value}</dd>
    </div>
  );
}
