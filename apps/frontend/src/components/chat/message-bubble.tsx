"use client";

import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Coins, AlertTriangle } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { AriaMascot } from "@/components/brand/aria-mascot";
import { CitationChip } from "@/components/chat/citation-chip";
import { ClassificationCard } from "@/components/chat/classification-card";
import { ScoringPanel } from "@/components/chat/scoring-panel";
import { DocumentArtifactCard } from "@/components/chat/document-artifact-card";
import { cn } from "@/lib/utils";
import type { AgentMessage } from "@/types/agent";

interface MessageBubbleProps {
  message: AgentMessage;
  userInitials?: string;
  /**
   * Muestra el footer `tokens in/out · USD · model`. El backend persiste estos
   * datos para gobierno pero exponerlos al usuario final agrega ruido. Por
   * eso default `false` y el padre decide según `user.isAdmin`.
   */
  showTokenUsage?: boolean;
}

/**
 * Render de un mensaje del agente o del usuario.
 *
 * Compone los sub-componentes (classification, citations, scoring, artifacts)
 * según los campos presentes en el `AgentMessage`. El reducer es quien decide
 * qué se popula; este componente solo refleja el estado.
 */
export function MessageBubble({
  message,
  userInitials = "U",
  showTokenUsage = false,
}: MessageBubbleProps) {
  const isAgent = message.role === "agent";
  const isStreaming = message.status === "streaming";
  const hasError = message.status === "error";

  return (
    <article
      className={cn(
        "flex w-full gap-3",
        isAgent ? "justify-start" : "justify-end",
      )}
      aria-label={isAgent ? "Mensaje de Aria" : "Mensaje del usuario"}
    >
      {isAgent && <AriaMascot size={32} status={isStreaming ? "speaking" : "idle"} />}
      <div
        className={cn(
          "flex max-w-[680px] flex-col gap-2.5",
          isAgent ? "items-start" : "items-end",
        )}
      >
        <div
          className={cn(
            "w-full rounded-2xl px-4 py-3 text-[14px] leading-relaxed shadow-sm",
            isAgent
              ? "rounded-tl-md border border-border bg-card text-foreground"
              : "rounded-tr-md bg-sqa-azul-medio-claro/15 text-foreground",
            hasError && "border-destructive/40 bg-destructive/5",
          )}
        >
          <MessageContent content={message.content} isStreaming={isStreaming} />
          {hasError && message.error && (
            <div className="mt-3 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-2 text-[12px] text-destructive">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
              <span>{message.error.message}</span>
            </div>
          )}
        </div>

        {isAgent && message.classification && (
          <ClassificationCard classification={message.classification} />
        )}

        {isAgent && message.citations.length > 0 && (
          <div
            className="flex flex-wrap gap-1.5"
            aria-label={`${message.citations.length} citaciones`}
          >
            {message.citations.map((citation) => (
              <CitationChip key={citation.documentId} citation={citation} />
            ))}
          </div>
        )}

        {isAgent && message.scoring && <ScoringPanel scoring={message.scoring} />}

        {isAgent && message.artifacts.length > 0 && (
          <div className="flex w-full flex-col gap-2" aria-label="Documentos generados">
            {message.artifacts.map((artifact) => (
              <DocumentArtifactCard
                key={artifact.documentId}
                artifact={artifact}
              />
            ))}
          </div>
        )}

        {isAgent && showTokenUsage && message.tokenUsage && (
          <footer className="flex items-center gap-1.5 text-[10.5px] text-muted-foreground">
            <Coins className="h-3 w-3" aria-hidden />
            <span className="font-mono">
              {message.tokenUsage.inputTokens.toLocaleString()} in ·{" "}
              {message.tokenUsage.outputTokens.toLocaleString()} out · USD{" "}
              {message.tokenUsage.costUsd.toFixed(4)} · {message.tokenUsage.model}
            </span>
          </footer>
        )}
      </div>
      {!isAgent && (
        <Avatar className="h-8 w-8">
          <AvatarFallback className="text-xs">{userInitials}</AvatarFallback>
        </Avatar>
      )}
    </article>
  );
}

interface MessageContentProps {
  content: string;
  isStreaming: boolean;
}

function MessageContent({ content, isStreaming }: MessageContentProps) {
  const components = useMemo(
    () => ({
      p: ({ children }: { children?: React.ReactNode }) => (
        <p className="mb-2 last:mb-0">{children}</p>
      ),
      ul: ({ children }: { children?: React.ReactNode }) => (
        <ul className="mb-2 ml-5 list-disc space-y-1 last:mb-0">{children}</ul>
      ),
      ol: ({ children }: { children?: React.ReactNode }) => (
        <ol className="mb-2 ml-5 list-decimal space-y-1 last:mb-0">
          {children}
        </ol>
      ),
      li: ({ children }: { children?: React.ReactNode }) => (
        <li className="leading-snug">{children}</li>
      ),
      h3: ({ children }: { children?: React.ReactNode }) => (
        <h3 className="mb-1.5 mt-3 font-display text-[13.5px] font-extrabold uppercase tracking-wider text-foreground first:mt-0">
          {children}
        </h3>
      ),
      strong: ({ children }: { children?: React.ReactNode }) => (
        <strong className="font-bold text-foreground">{children}</strong>
      ),
      code: ({ children }: { children?: React.ReactNode }) => (
        <code className="rounded bg-muted px-1 py-0.5 font-mono text-[12.5px]">
          {children}
        </code>
      ),
      a: ({ href, children }: { href?: string; children?: React.ReactNode }) => {
        // Links externos del markdown del agente abren en nueva pestaña con
        // `rel="noopener noreferrer"` para cortar window.opener y leak de
        // referer (`Referrer-Policy: strict-origin-when-cross-origin` ya
        // limita el referer global, pero defensa en profundidad).
        const isExternal = /^https?:\/\//i.test(href ?? "");
        return (
          <a
            href={href}
            target={isExternal ? "_blank" : undefined}
            rel={isExternal ? "noopener noreferrer nofollow" : undefined}
            className="text-sqa-azul-medio-claro underline-offset-2 hover:underline"
          >
            {children}
          </a>
        );
      },
    }),
    [],
  );

  return (
    <div className="break-words">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
      {isStreaming && (
        <span
          aria-hidden
          className="ml-0.5 inline-block h-3.5 w-[2px] translate-y-0.5 animate-pulse bg-sqa-naranja"
        />
      )}
    </div>
  );
}
