"use client";

import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MessageContentProps {
  content: string;
  isStreaming: boolean;
}

/**
 * Render del Markdown del mensaje del agente. Extraído de message-bubble
 * para permitir dynamic-import (react-markdown + remark-gfm pesan ~30 kB
 * combinados). Cargar bajo demanda solo cuando el usuario abre un chat.
 */
export function MessageContent({ content, isStreaming }: MessageContentProps) {
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
