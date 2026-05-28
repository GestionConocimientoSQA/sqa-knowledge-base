import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TraceabilityForm } from "@/components/ingestion/traceability-form";
import type { IngestionItem } from "@/types/domain";

function baseItem(overrides: Partial<IngestionItem> = {}): IngestionItem {
  return {
    id: "ing-test",
    filename: "documento.docx",
    sizeBytes: 2048,
    paginas: 4,
    carpetaSugerida: null,
    tipoSugerido: null,
    aprobadorOid: null,
    aprobadorName: "",
    fechaAprobacion: null,
    fuenteOriginal: "",
    version: "",
    status: "en-revision",
    uploadedByOid: "oid-x",
    uploadedAt: "2026-05-18T09:30:00.000Z",
    blobPath: "stub/documento.docx",
    errorDetail: null,
    ...overrides,
  };
}

describe("TraceabilityForm", () => {
  it("rellena el aprobador con el nombre del usuario por default", () => {
    render(
      <TraceabilityForm
        item={baseItem()}
        approverName="Camila Pereyra"
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByLabelText(/aprobado por/i)).toHaveValue(
      "Camila Pereyra",
    );
  });

  it("usa los sugeridos del item como defaults de carpeta y tipo", () => {
    render(
      <TraceabilityForm
        item={baseItem({ carpetaSugerida: "TEC", tipoSugerido: "MTEC" })}
        approverName="Andrés"
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByLabelText(/carpeta temática/i)).toHaveValue("TEC");
    expect(screen.getByLabelText(/tipo de documento/i)).toHaveValue("MTEC");
  });

  it("muestra error si faltan campos obligatorios (sin submit)", () => {
    const onSubmit = vi.fn();
    render(
      <TraceabilityForm
        item={baseItem()}
        approverName="Andrés"
        onSubmit={onSubmit}
      />,
    );
    // Sin elegir carpeta/tipo
    fireEvent.submit(screen.getByRole("form", { name: /trazabilidad/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(/fuente|carpeta|versión|tipo/i);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submit válido emite TraceabilityInput trimmed con todos los campos", () => {
    const onSubmit = vi.fn();
    render(
      <TraceabilityForm
        item={baseItem({
          carpetaSugerida: "PROC",
          tipoSugerido: "FORM",
        })}
        approverName="Camila"
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByLabelText(/aprobado por/i), {
      target: { value: "  Camila Pereyra  " },
    });
    fireEvent.change(screen.getByLabelText(/fecha de aprobación/i), {
      target: { value: "2026-05-20" },
    });
    fireEvent.change(screen.getByLabelText(/fuente original/i), {
      target: { value: "SharePoint/QA/Plantillas/" },
    });
    fireEvent.change(screen.getByLabelText(/versión/i), {
      target: { value: "2.1" },
    });

    fireEvent.submit(screen.getByRole("form", { name: /trazabilidad/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      approvedBy: "Camila Pereyra",
      approvalDate: "2026-05-20",
      sourceOrigin: "SharePoint/QA/Plantillas/",
      version: "2.1",
      category: "PROC",
      documentType: "FORM",
    });
  });

  it("isSubmitting deshabilita el botón principal y muestra label de progreso", () => {
    render(
      <TraceabilityForm
        item={baseItem({ carpetaSugerida: "TEC", tipoSugerido: "MTEC" })}
        approverName="Andrés"
        onSubmit={vi.fn()}
        isSubmitting
      />,
    );
    const submit = screen.getByRole("button", { name: /aprobando/i });
    expect(submit).toBeDisabled();
  });

  it("onCancel se ejecuta al hacer click en Cancelar (si está provisto)", () => {
    const onCancel = vi.fn();
    render(
      <TraceabilityForm
        item={baseItem()}
        approverName="Andrés"
        onSubmit={vi.fn()}
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /cancelar/i }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
