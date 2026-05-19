"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { Send, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AttachmentChip } from "@/components/chat/attachment-chip";
import { AttachmentUploader } from "@/components/chat/attachment-uploader";
import { cn } from "@/lib/utils";
import type { AttachmentMetadata } from "@/types/agent";

const MAX_HEIGHT_PX = 200;
const MAX_CHARS = 4000;

interface ComposerProps {
  disabled?: boolean;
  busy?: boolean;
  placeholder?: string;
  onSend: (content: string) => void;
  onCancel?: () => void;
  /** Attachments pre-envío (se limpian al enviar — lo decide el padre). */
  attachments?: AttachmentMetadata[];
  onAttachmentAdd?: (files: File[]) => void;
  onAttachmentRemove?: (id: string) => void;
}

export function Composer({
  disabled = false,
  busy = false,
  placeholder = "Escribí tu mensaje a Aria...",
  onSend,
  onCancel,
  attachments = [],
  onAttachmentAdd,
  onAttachmentRemove,
}: ComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const trimmed = value.trim();
  const overLimit = value.length > MAX_CHARS;
  const hasUploadingAttachment = attachments.some(
    (a) => a.status === "uploading",
  );
  const canSend =
    !disabled &&
    !busy &&
    !hasUploadingAttachment &&
    (trimmed.length > 0 || attachments.some((a) => a.status === "uploaded")) &&
    !overLimit;

  const supportsAttachments = Boolean(onAttachmentAdd);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`;
  }, [value]);

  const handleSubmit = useCallback(
    (event?: FormEvent) => {
      event?.preventDefault();
      if (!canSend) return;
      onSend(trimmed);
      setValue("");
    },
    [canSend, onSend, trimmed],
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-border bg-card px-4 py-3 sm:px-6"
      aria-label="Composer del chat"
    >
      <div className="mx-auto max-w-3xl">
        {attachments.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {attachments.map((attachment) => (
              <AttachmentChip
                key={attachment.id}
                attachment={attachment}
                onRemove={onAttachmentRemove}
              />
            ))}
          </div>
        )}

        <div className="flex items-end gap-2">
          {supportsAttachments && (
            <AttachmentUploader
              disabled={disabled || busy}
              onFilesSelected={onAttachmentAdd!}
            />
          )}
          <div className="relative flex-1">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled}
              rows={1}
              className={cn(
                "block w-full resize-none rounded-xl border border-input bg-background px-3.5 py-2.5 text-[14px] leading-relaxed shadow-sm transition-colors focus:border-sqa-naranja focus:outline-none focus:ring-1 focus:ring-sqa-naranja disabled:cursor-not-allowed disabled:opacity-50",
                overLimit && "border-destructive focus:border-destructive focus:ring-destructive",
              )}
              aria-label="Mensaje para Aria"
              aria-invalid={overLimit}
            />
            {value.length > 0 && (
              <span
                className={cn(
                  "pointer-events-none absolute bottom-1.5 right-3 font-mono text-[10px]",
                  overLimit ? "text-destructive" : "text-muted-foreground",
                )}
                aria-hidden
              >
                {value.length}/{MAX_CHARS}
              </span>
            )}
          </div>
          {busy ? (
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={onCancel}
              aria-label="Detener respuesta"
            >
              <Square className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              type="submit"
              variant="accent"
              size="icon"
              disabled={!canSend}
              aria-label="Enviar mensaje"
            >
              <Send className="h-4 w-4" />
            </Button>
          )}
        </div>

        <p className="mt-1.5 text-[10.5px] text-muted-foreground">
          Enter para enviar · Shift+Enter para salto de línea
          {supportsAttachments && " · Arrastrá archivos para adjuntar"}
        </p>
      </div>
    </form>
  );
}
