"use client";

import Link from "next/link";
import {
  Activity,
  Mic,
  Upload,
  Search,
  Tag,
  type LucideIcon,
} from "lucide-react";
import { formatDistanceToNow, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { RecentActivityItem, RecentActivityType } from "@/types/domain";

interface RecentActivityFeedProps {
  items: RecentActivityItem[] | undefined;
  isLoading?: boolean;
}

const ICON_BY_TYPE: Record<RecentActivityType, LucideIcon> = {
  captura: Mic,
  ingesta: Upload,
  consulta: Search,
  taxonomia: Tag,
};

const TONE_BY_TYPE: Record<RecentActivityType, string> = {
  captura: "text-sqa-naranja bg-sqa-naranja/10",
  ingesta: "text-blue-500 bg-blue-500/10",
  consulta: "text-emerald-500 bg-emerald-500/10",
  taxonomia: "text-purple-500 bg-purple-500/10",
};

const LABEL_BY_TYPE: Record<RecentActivityType, string> = {
  captura: "Captura",
  ingesta: "Ingesta",
  consulta: "Consulta",
  taxonomia: "Taxonomía",
};

function relativeTime(iso: string): string {
  try {
    return formatDistanceToNow(parseISO(iso), { addSuffix: true, locale: es });
  } catch {
    return iso;
  }
}

/**
 * Feed cronológico de actividad del KB. Usado en el dashboard del
 * GK Lead y Owner para tener un pulso del uso diario.
 */
export function RecentActivityFeed({
  items,
  isLoading,
}: RecentActivityFeedProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Activity className="h-4 w-4 text-sqa-naranja" aria-hidden />
          Actividad reciente
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div
            className="space-y-3"
            role="status"
            aria-live="polite"
            aria-label="Cargando actividad reciente"
          >
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : !items || items.length === 0 ? (
          <EmptyState
            icon={Activity}
            title="Sin actividad"
            description="Cuando alguien capture, consulte o ingiera algo, aparecerá acá."
            className="border-0 py-4"
          />
        ) : (
          <ul
            className="space-y-3"
            aria-label={`${items.length} eventos recientes`}
          >
            {items.map((a) => (
              <ActivityRow key={a.id} item={a} />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function ActivityRow({ item: a }: { item: RecentActivityItem }) {
  const Icon = ICON_BY_TYPE[a.type];
  const tone = TONE_BY_TYPE[a.type];
  const typeLabel = LABEL_BY_TYPE[a.type];

  const content = (
    <div className="flex items-start gap-3">
      <span
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${tone}`}
        aria-hidden
      >
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
          <span className="font-display font-semibold uppercase tracking-wider">
            {typeLabel}
          </span>
          <span aria-hidden>·</span>
          <span>{a.actor.name}</span>
          <span aria-hidden>·</span>
          <time dateTime={a.at}>{relativeTime(a.at)}</time>
        </div>
        <div className="mt-0.5 text-[13px] leading-snug">{a.summary}</div>
      </div>
    </div>
  );

  if (a.refUrl) {
    return (
      <li>
        <Link
          href={a.refUrl as never}
          className="block rounded-md p-2 transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {content}
        </Link>
      </li>
    );
  }
  return <li className="rounded-md p-2">{content}</li>;
}
