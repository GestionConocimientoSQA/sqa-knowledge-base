"use client";

import { FileText } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { DocumentDetail } from "@/types/domain";

interface DocumentPreviewPlaceholderProps {
  document: DocumentDetail;
}

/**
 * Placeholder visual del preview de documento. El viewer real (con
 * páginas DOCX/PDF renderizadas) llega en Fase 4 con los extractores
 * y la integración con Blob Storage. Por ahora muestra metadata visual
 * + resumen para que la UI no se sienta vacía.
 */
export function DocumentPreviewPlaceholder({
  document: d,
}: DocumentPreviewPlaceholderProps) {
  return (
    <Card>
      <CardContent className="p-0">
        <div className="flex items-center justify-center border-b border-dashed border-border bg-gradient-to-br from-sqa-azul-medio/5 to-sqa-naranja/5 py-12">
          <div className="flex flex-col items-center gap-3 text-center">
            <div
              className="flex h-16 w-16 items-center justify-center rounded-2xl bg-card shadow-sm"
              aria-hidden
            >
              <FileText className="h-8 w-8 text-sqa-naranja" />
            </div>
            <div>
              <div className="font-display text-sm font-bold">
                {d.formato} · {d.paginas} páginas · v{d.version}
              </div>
              <div className="mt-1 text-[11px] text-muted-foreground">
                Vista previa inline disponible en Fase 4 (extracción).
              </div>
            </div>
          </div>
        </div>
        {d.resumen && (
          <div className="p-5">
            <div className="eyebrow mb-2">Resumen ejecutivo</div>
            <p className="text-[14px] leading-relaxed">{d.resumen}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
