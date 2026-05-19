"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { PageContainer } from "@/components/shared/page-container";
import { ModeSelectorCard } from "@/components/chat/mode-selector-card";
import { SessionHistoryPanel } from "@/components/chat/session-history-panel";
import { useAuth } from "@/lib/auth/auth-provider";
import {
  createSession,
  deleteSession,
  getMessages,
  getSession,
  listSessions,
  restoreSession,
} from "@/lib/api/sessions";
import {
  MODE_COPY,
  ORDERED_MODES,
  isSessionMode,
} from "@/lib/chat/mode-copy";
import type { SessionMode } from "@/types/domain";

function ModeSelector() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [pendingMode, setPendingMode] = useState<SessionMode | null>(null);

  const queryMode = searchParams.get("mode");
  const preselected = isSessionMode(queryMode) ? queryMode : null;

  const { data: sessions, isLoading } = useQuery({
    queryKey: ["sessions", user?.oid],
    queryFn: () => listSessions({ ownerOid: user?.oid }),
    enabled: Boolean(user?.oid),
  });

  const handleStart = async (mode: SessionMode) => {
    if (!user) return;
    if (pendingMode) return;
    setPendingMode(mode);
    try {
      const session = await createSession({ mode, ownerOid: user.oid });
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      router.push(`/chat/${session.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Error desconocido";
      toast.error(`No se pudo crear la sesión: ${message}`);
      setPendingMode(null);
    }
  };

  const handleDelete = async (sessionId: string) => {
    const [session, messages] = await Promise.all([
      getSession(sessionId),
      getMessages(sessionId),
    ]);
    if (!session) return;
    await deleteSession(sessionId);
    queryClient.invalidateQueries({ queryKey: ["sessions"] });
    toast.success(`"${session.title}" eliminada`, {
      duration: 8000,
      action: {
        label: "Deshacer",
        onClick: async () => {
          await restoreSession(session, messages);
          queryClient.invalidateQueries({ queryKey: ["sessions"] });
        },
      },
    });
  };

  return (
    <PageContainer>
      <header className="mb-8 max-w-2xl">
        <p className="eyebrow text-[10px] text-muted-foreground">
          Trabajo · Nueva conversación
        </p>
        <h2 className="mt-2 font-display text-2xl font-extrabold tracking-tight text-foreground">
          ¿Cómo querés trabajar con Aria hoy?
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Elegí el modo que mejor describe tu intención. Vas a poder pausar y
          retomar la sesión en cualquier momento desde el sidebar.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        {ORDERED_MODES.map((mode) => (
          <ModeSelectorCard
            key={mode}
            copy={MODE_COPY[mode]}
            selected={mode === preselected || mode === pendingMode}
            pending={pendingMode !== null}
            onStart={() => handleStart(mode)}
          />
        ))}
      </div>

      <div className="mt-10">
        <SessionHistoryPanel
          sessions={sessions}
          isLoading={isLoading}
          onDelete={handleDelete}
        />
      </div>
    </PageContainer>
  );
}

export default function ChatSelectorPage() {
  return (
    <Suspense fallback={null}>
      <ModeSelector />
    </Suspense>
  );
}
