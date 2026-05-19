"use client";

import { useEffect, useRef } from "react";
import { MessageSquare } from "lucide-react";
import { MessageBubble } from "@/components/chat/message-bubble";
import { EmptyState } from "@/components/shared/empty-state";
import type { AgentMessage } from "@/types/agent";

interface ChatWindowProps {
  messages: AgentMessage[];
  userInitials?: string;
  /** Propagado al MessageBubble — controla visibilidad del footer de tokens. */
  showTokenUsage?: boolean;
}

/**
 * Lista vertical scrolleable de mensajes. Auto-scroll al fondo cuando llega
 * uno nuevo o cuando el contenido del último crece (streaming).
 *
 * Sin virtualización en sub-fase 6.3 — el plan de la fase recomienda esperar
 * a tener métricas de jank con conversaciones largas (200+ mensajes) antes de
 * introducir react-virtual. Evitamos la abstracción prematura.
 */
export function ChatWindow({
  messages,
  userInitials,
  showTokenUsage = false,
}: ChatWindowProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastMessageId = messages.at(-1)?.id;
  const lastContentLength = messages.at(-1)?.content.length ?? 0;

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [lastMessageId, lastContentLength]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <EmptyState
          icon={MessageSquare}
          title="Conversación lista para empezar"
          description="Escribí tu mensaje abajo. Aria responde con streaming en tiempo real."
        />
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto"
      role="log"
      aria-live="polite"
      aria-label="Conversación con Aria"
    >
      <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-8 sm:px-6">
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            userInitials={userInitials}
            showTokenUsage={showTokenUsage}
          />
        ))}
      </div>
    </div>
  );
}
