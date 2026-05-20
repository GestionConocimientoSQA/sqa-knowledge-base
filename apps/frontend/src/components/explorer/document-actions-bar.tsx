"use client";

import { Download, BadgeCheck, ShieldOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth/auth-provider";
import type { DocumentDetail } from "@/types/domain";

interface DocumentActionsBarProps {
  document: DocumentDetail;
  /**
   * Callback al togglear autoritativo. Mock por ahora; en backend Fase 1
   * será `PATCH /documents/{id}` con audit log según [[project-security-idor-check]].
   */
  onToggleAuthoritative?: (next: boolean) => void;
  /** Callback de descarga (mock — Fase 4 conecta blob storage). */
  onDownload?: () => void;
}

/**
 * Barra de acciones del detalle. La descarga está disponible para todos
 * los roles autenticados; "Marcar autoritativo" solo para `isAdmin`
 * (Owner + GK Lead) según la matriz [[project-roles-capacidades]].
 *
 * En Fase 1 (backend real) el flag `isAdmin` se reemplaza por el objeto
 * de permisos del User y la decisión se afina: Owner sólo puede marcar
 * autoritativo en sus `carpetas_owned`; GK Lead en cualquier carpeta.
 * Por ahora con isAdmin alcanza para el cliente.
 */
export function DocumentActionsBar({
  document: d,
  onToggleAuthoritative,
  onDownload,
}: DocumentActionsBarProps) {
  const { user } = useAuth();
  const canEditAuthoritative = Boolean(user?.isAdmin);

  return (
    <div
      className="flex flex-wrap items-center gap-2"
      aria-label="Acciones del documento"
    >
      <Button
        type="button"
        onClick={onDownload}
        aria-label={`Descargar ${d.titulo}`}
      >
        <Download className="h-4 w-4" />
        Descargar
      </Button>

      {canEditAuthoritative && (
        <Button
          type="button"
          variant={d.autoritativo ? "outline" : "default"}
          onClick={() => onToggleAuthoritative?.(!d.autoritativo)}
          aria-label={
            d.autoritativo ? "Quitar autoritativo" : "Marcar autoritativo"
          }
        >
          {d.autoritativo ? (
            <>
              <ShieldOff className="h-4 w-4" />
              Quitar autoritativo
            </>
          ) : (
            <>
              <BadgeCheck className="h-4 w-4" />
              Marcar autoritativo
            </>
          )}
        </Button>
      )}
    </div>
  );
}
