"use client";

import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { notFound } from "next/navigation";
import { toast } from "sonner";
import { Upload } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { SessionHeader } from "@/components/chat/session-header";
import { StageIndicator } from "@/components/chat/stage-indicator";
import { ChatWindow } from "@/components/chat/chat-window";
import { Composer } from "@/components/chat/composer";
import { useAuth } from "@/lib/auth/auth-provider";
import {
  getMessages,
  getSession,
  pauseSession,
  resumeSession,
  saveMessages,
} from "@/lib/api/sessions";
import {
  AttachmentValidationError,
  listAttachments,
  removeAttachment,
  uploadAttachment,
} from "@/lib/api/attachments";
import { getDefaultTransport } from "@/lib/streaming/transport-factory";
import { useChatStream } from "@/lib/streaming/use-chat-stream";
import { useFileDropZone } from "@/lib/hooks/use-file-drop-zone";
import type { SessionMode } from "@/types/domain";

function getInitials(name: string | undefined): string {
  if (!name) return "U";
  return name
    .split(" ")
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

interface ChatSessionPageProps {
  params: Promise<{ sessionId: string }>;
}

export default function ChatSessionPage({ params }: ChatSessionPageProps) {
  const { sessionId } = use(params);
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [pendingAction, setPendingAction] = useState(false);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  const { data: session, isLoading: isLoadingSession } = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => getSession(sessionId),
  });

  const { data: initialMessages } = useQuery({
    queryKey: ["session-messages", sessionId],
    queryFn: () => getMessages(sessionId),
  });

  const { data: attachments } = useQuery({
    queryKey: ["attachments", sessionId],
    queryFn: () => listAttachments(sessionId),
  });

  const mode: SessionMode = session?.mode ?? "captura";
  const transport = useMemo(() => getDefaultTransport(), []);
  const { state, send, cancel, retry } = useChatStream({
    sessionId,
    mode,
    transport,
    initialMessages,
  });

  const lastPersistedCountRef = useRef<number>(initialMessages?.length ?? 0);
  useEffect(() => {
    const completed = state.messages.filter((m) => m.status !== "streaming");
    if (completed.length === lastPersistedCountRef.current) return;
    lastPersistedCountRef.current = completed.length;
    void saveMessages(sessionId, completed).then(() => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    });
  }, [state.messages, sessionId, queryClient]);

  useEffect(() => {
    if (state.status !== "error" || !state.error) return;
    toast.error(state.error.message, {
      duration: 8000,
      action: state.error.retryable
        ? { label: "Reintentar", onClick: () => void retry() }
        : undefined,
    });
  }, [state.status, state.error, retry]);

  const handleFilesSelected = useCallback(
    async (files: File[]) => {
      for (const file of files) {
        try {
          await uploadAttachment({
            sessionId,
            file,
            onProgress: () => {
              queryClient.invalidateQueries({
                queryKey: ["attachments", sessionId],
              });
            },
          });
        } catch (err) {
          if (err instanceof AttachmentValidationError) {
            toast.error(`${file.name}: ${err.message}`);
          } else {
            const msg = err instanceof Error ? err.message : "Error desconocido";
            toast.error(`No se pudo subir ${file.name}: ${msg}`);
          }
        }
      }
      queryClient.invalidateQueries({ queryKey: ["attachments", sessionId] });
    },
    [sessionId, queryClient],
  );

  const handleAttachmentRemove = useCallback(
    async (attachmentId: string) => {
      await removeAttachment(sessionId, attachmentId);
      queryClient.invalidateQueries({ queryKey: ["attachments", sessionId] });
    },
    [sessionId, queryClient],
  );

  const handleSend = useCallback(
    async (content: string) => {
      const uploaded = (attachments ?? []).filter(
        (a) => a.status === "uploaded",
      );
      const attachmentIds = uploaded.map((a) => a.id);
      await send(content, attachmentIds.length > 0 ? attachmentIds : undefined);
      // En el backend real el attachment queda asociado al mensaje en el POST
      // del envío; acá los limpiamos del store local para que el composer no
      // los siga mostrando como pendientes.
      await Promise.all(
        uploaded.map((a) => removeAttachment(sessionId, a.id)),
      );
      queryClient.invalidateQueries({ queryKey: ["attachments", sessionId] });
    },
    [attachments, send, sessionId, queryClient],
  );

  const { isDragging } = useFileDropZone({
    ref: dropZoneRef,
    enabled: session?.status === "active",
    onFiles: handleFilesSelected,
  });

  if (!isLoadingSession && session === null) notFound();

  const handlePause = async () => {
    setPendingAction(true);
    try {
      const updated = await pauseSession(sessionId);
      if (updated) {
        queryClient.setQueryData(["session", sessionId], updated);
        queryClient.invalidateQueries({ queryKey: ["sessions"] });
        toast.success("Sesión pausada");
      }
    } finally {
      setPendingAction(false);
    }
  };

  const handleResume = async () => {
    setPendingAction(true);
    try {
      const updated = await resumeSession(sessionId);
      if (updated) {
        queryClient.setQueryData(["session", sessionId], updated);
        queryClient.invalidateQueries({ queryKey: ["sessions"] });
        toast.success("Sesión reanudada");
      }
    } finally {
      setPendingAction(false);
    }
  };

  if (isLoadingSession || !session) {
    return (
      <div className="flex h-full flex-col">
        <div className="border-b border-border bg-card px-6 py-5">
          <Skeleton className="h-6 w-64" />
          <Skeleton className="mt-2 h-4 w-40" />
        </div>
        <div className="flex flex-1 items-center justify-center p-8">
          <Skeleton className="h-32 w-full max-w-lg" />
        </div>
      </div>
    );
  }

  const userInitials = getInitials(user?.name);
  const busy = state.status === "connecting" || state.status === "streaming";
  const composerDisabled = session.status !== "active";

  return (
    <div ref={dropZoneRef} className="relative flex h-full flex-col">
      <SessionHeader
        session={session}
        onPause={handlePause}
        onResume={handleResume}
        pendingAction={pendingAction}
      />
      <StageIndicator mode={session.mode} currentStage={state.currentStage} />
      <ChatWindow
        messages={state.messages}
        userInitials={userInitials}
        showTokenUsage={user?.isAdmin ?? false}
      />
      <Composer
        disabled={composerDisabled}
        busy={busy}
        placeholder={
          session.status === "paused"
            ? "Reanudá la sesión para escribir."
            : "Escribí tu mensaje a Aria..."
        }
        onSend={(content) => void handleSend(content)}
        onCancel={cancel}
        attachments={attachments ?? []}
        onAttachmentAdd={handleFilesSelected}
        onAttachmentRemove={(id) => void handleAttachmentRemove(id)}
      />

      {isDragging && (
        <div
          className="pointer-events-none absolute inset-0 z-40 flex items-center justify-center bg-sqa-naranja/10 backdrop-blur-sm"
          aria-hidden
        >
          <div className="flex flex-col items-center gap-3 rounded-lg border-2 border-dashed border-sqa-naranja bg-card px-8 py-6 shadow-xl">
            <Upload className="h-10 w-10 text-sqa-naranja" />
            <p className="font-display text-base font-extrabold text-foreground">
              Soltá para adjuntar
            </p>
            <p className="text-xs text-muted-foreground">
              Aria los va a procesar al enviar el próximo mensaje.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
