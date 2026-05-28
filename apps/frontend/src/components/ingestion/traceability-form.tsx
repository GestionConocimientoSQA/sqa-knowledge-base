"use client";

/**
 * Formulario de trazabilidad para aprobar un item (Fase 8.4).
 *
 * Captura los 6 campos obligatorios que el backend espera en
 * `POST /ingestion/{id}/approve`: aprobador, fecha, fuente, versión,
 * carpeta (CategoryCode) y tipo (DocTypeCode). Sin trazabilidad no se aprueba
 * — es el contrato explícito del KB SQA (todo doc indexado tiene autoridad).
 *
 * SRP: solo presentación + validación + emisión del callback. La mutación
 * (`useApproveIngestion`) la dispara el contenedor de la página, no el form.
 */
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  CATEGORY_CODES,
  CATEGORY_LABELS,
  DOC_TYPE_CODES,
  DOC_TYPE_LABELS,
} from "@/lib/taxonomy";
import type {
  CategoryCode,
  DocTypeCode,
  IngestionItem,
  TraceabilityInput,
} from "@/types/domain";

interface TraceabilityFormProps {
  /** Item base — se usan los valores sugeridos como defaults. */
  item: IngestionItem;
  /** Nombre del usuario que aprueba; default para `approvedBy`. */
  approverName: string;
  /** True mientras la mutación está en vuelo. */
  isSubmitting?: boolean;
  onSubmit: (input: TraceabilityInput) => void;
  onCancel?: () => void;
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function isISODate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value);
}

export function TraceabilityForm({
  item,
  approverName,
  isSubmitting = false,
  onSubmit,
  onCancel,
}: TraceabilityFormProps) {
  const [approvedBy, setApprovedBy] = useState(
    item.aprobadorName || approverName,
  );
  const [approvalDate, setApprovalDate] = useState(
    item.fechaAprobacion ?? today(),
  );
  const [sourceOrigin, setSourceOrigin] = useState(item.fuenteOriginal);
  const [version, setVersion] = useState(item.version || "1.0");
  const [category, setCategory] = useState<CategoryCode | "">(
    item.carpetaSugerida ?? "",
  );
  const [documentType, setDocumentType] = useState<DocTypeCode | "">(
    item.tipoSugerido ?? "",
  );
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!approvedBy.trim()) return setError("El aprobador es obligatorio.");
    if (!isISODate(approvalDate))
      return setError("La fecha debe tener formato AAAA-MM-DD.");
    if (!sourceOrigin.trim())
      return setError("La fuente de origen es obligatoria.");
    if (!version.trim()) return setError("La versión es obligatoria.");
    if (!category) return setError("Seleccioná la carpeta temática.");
    if (!documentType) return setError("Seleccioná el tipo de documento.");
    setError(null);
    onSubmit({
      approvedBy: approvedBy.trim(),
      approvalDate,
      sourceOrigin: sourceOrigin.trim(),
      version: version.trim(),
      category,
      documentType,
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      aria-label="Formulario de trazabilidad"
      className="space-y-4 rounded-lg border border-border bg-card p-5"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="trace-approver">Aprobado por</Label>
          <Input
            id="trace-approver"
            value={approvedBy}
            onChange={(e) => setApprovedBy(e.target.value)}
            required
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="trace-date">Fecha de aprobación</Label>
          <Input
            id="trace-date"
            type="date"
            value={approvalDate}
            onChange={(e) => setApprovalDate(e.target.value)}
            required
          />
        </div>

        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="trace-source">Fuente original</Label>
          <Input
            id="trace-source"
            placeholder="SharePoint/QA/Plantillas/"
            value={sourceOrigin}
            onChange={(e) => setSourceOrigin(e.target.value)}
            required
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="trace-version">Versión</Label>
          <Input
            id="trace-version"
            placeholder="1.0"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            required
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="trace-category">Carpeta temática</Label>
          <select
            id="trace-category"
            value={category}
            onChange={(e) => setCategory(e.target.value as CategoryCode | "")}
            required
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="">Seleccionar…</option>
            {CATEGORY_CODES.map((code) => (
              <option key={code} value={code}>
                {code} — {CATEGORY_LABELS[code]}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="trace-doctype">Tipo de documento</Label>
          <select
            id="trace-doctype"
            value={documentType}
            onChange={(e) =>
              setDocumentType(e.target.value as DocTypeCode | "")
            }
            required
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="">Seleccionar…</option>
            {DOC_TYPE_CODES.map((code) => (
              <option key={code} value={code}>
                {code} — {DOC_TYPE_LABELS[code]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <p
          role="alert"
          className="rounded-md border border-error/40 bg-error/5 px-3 py-2 text-sm text-error"
        >
          {error}
        </p>
      )}

      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancelar
          </Button>
        )}
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Aprobando…" : "Aprobar e indexar"}
        </Button>
      </div>
    </form>
  );
}
