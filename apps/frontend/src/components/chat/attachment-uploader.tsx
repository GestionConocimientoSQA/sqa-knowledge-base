"use client";

import { useRef, type ChangeEvent } from "react";
import { Paperclip } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ALLOWED_EXTENSIONS } from "@/lib/api/attachments";

interface AttachmentUploaderProps {
  disabled?: boolean;
  onFilesSelected: (files: File[]) => void;
}

/**
 * Botón paperclip que abre el file picker nativo. Acepta multi-file.
 * La validación de tipo/tamaño la hace `uploadAttachment` — acá solo abrimos
 * el picker y pasamos los `File[]` al padre.
 */
export function AttachmentUploader({
  disabled = false,
  onFilesSelected,
}: AttachmentUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    onFilesSelected(Array.from(files));
    event.target.value = ""; // permite re-seleccionar el mismo archivo
  };

  return (
    <>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        aria-label="Adjuntar archivos"
      >
        <Paperclip className="h-4 w-4" />
      </Button>
      <input
        ref={inputRef}
        type="file"
        multiple
        hidden
        accept={ALLOWED_EXTENSIONS.join(",")}
        onChange={handleChange}
        aria-hidden
      />
    </>
  );
}
