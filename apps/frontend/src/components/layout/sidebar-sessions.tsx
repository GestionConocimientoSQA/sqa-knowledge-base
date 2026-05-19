"use client";

import { useQuery } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { History } from "lucide-react";
import { SessionListItem } from "@/components/chat/session-list-item";
import { Skeleton } from "@/components/ui/skeleton";
import { listSessions } from "@/lib/api/sessions";
import { useAuth } from "@/lib/auth/auth-provider";

const SIDEBAR_LIMIT = 5;

/**
 * Lista compacta de sesiones recientes del usuario para mostrar en el sidebar.
 * Limitado a 5 — el listado completo + filtros vive en `/chat` (selector).
 */
export function SidebarSessions() {
  const { user } = useAuth();
  const pathname = usePathname();
  const ownerOid = user?.oid;

  const { data, isLoading } = useQuery({
    queryKey: ["sessions", ownerOid],
    queryFn: () => listSessions({ ownerOid }),
    enabled: Boolean(ownerOid),
  });

  const sessions = (data ?? []).slice(0, SIDEBAR_LIMIT);
  const activeId = pathname.startsWith("/chat/")
    ? pathname.split("/")[2]
    : undefined;

  return (
    <div className="mb-[18px]">
      <div className="flex items-center justify-between px-3 pb-2 pt-1">
        <span className="font-display text-[9.5px] font-extrabold uppercase tracking-[0.14em] text-white/60">
          Mis sesiones
        </span>
        <Link
          href="/chat"
          className="font-display text-[9.5px] font-extrabold uppercase tracking-[0.08em] text-white/55 transition-colors hover:text-white"
        >
          Ver todo
        </Link>
      </div>

      <div className="space-y-0.5 px-1">
        {isLoading && (
          <>
            <Skeleton className="h-10 w-full bg-white/[0.05]" />
            <Skeleton className="h-10 w-full bg-white/[0.05]" />
          </>
        )}

        {!isLoading && sessions.length === 0 && (
          <div className="flex items-center gap-2 px-2 py-2 text-[11px] text-white/55">
            <History className="h-3.5 w-3.5" aria-hidden />
            <span>Aún no iniciaste ninguna sesión.</span>
          </div>
        )}

        {sessions.map((session) => (
          <SessionListItem
            key={session.id}
            session={session}
            active={session.id === activeId}
            compact
            dark
          />
        ))}
      </div>
    </div>
  );
}
