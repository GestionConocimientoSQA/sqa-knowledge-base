import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { IngestionItemRow } from "@/components/ingestion/ingestion-item-row";
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
    status: "pendiente-metadata",
    uploadedByOid: "oid-x",
    uploadedAt: "2026-05-18T09:30:00.000Z",
    blobPath: "stub/documento.docx",
    errorDetail: null,
    ...overrides,
  };
}

describe("IngestionItemRow", () => {
  it("pendiente-metadata: muestra Clasificar y Rechazar, no Revisar", () => {
    const onClassify = vi.fn();
    const onReject = vi.fn();
    render(
      <IngestionItemRow
        item={baseItem({ status: "pendiente-metadata" })}
        onClassify={onClassify}
        onReject={onReject}
      />,
    );
    expect(screen.getByRole("button", { name: /clasificar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /rechazar/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /revisar/i })).toBeNull();
  });

  it("en-revision: muestra link Revisar y Rechazar, no Clasificar", () => {
    render(
      <IngestionItemRow
        item={baseItem({ status: "en-revision" })}
        onClassify={vi.fn()}
        onReject={vi.fn()}
      />,
    );
    const reviewLink = screen.getByRole("link", { name: /revisar/i });
    expect(reviewLink).toHaveAttribute("href", "/ingestion/ing-test");
    expect(screen.queryByRole("button", { name: /clasificar/i })).toBeNull();
    expect(screen.getByRole("button", { name: /rechazar/i })).toBeInTheDocument();
  });

  it("indexado: solo muestra Ver (sin acciones de mutación)", () => {
    render(
      <IngestionItemRow
        item={baseItem({ status: "indexado" })}
        onClassify={vi.fn()}
        onReject={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: /clasificar/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /rechazar/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /revisar/i })).toBeNull();
    expect(screen.getByRole("link", { name: /ver detalle/i })).toBeInTheDocument();
  });

  it("rechazado: muestra Ver + errorDetail visible como alerta", () => {
    render(
      <IngestionItemRow
        item={baseItem({
          status: "rechazado",
          errorDetail: "No cumple el estándar.",
        })}
        onClassify={vi.fn()}
        onReject={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("No cumple el estándar.");
    expect(screen.getByRole("link", { name: /ver detalle/i })).toBeInTheDocument();
  });

  it("dispara onClassify con el id correcto", () => {
    const onClassify = vi.fn();
    render(
      <IngestionItemRow
        item={baseItem({ id: "ing-42", status: "listo" })}
        onClassify={onClassify}
        onReject={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /clasificar/i }));
    expect(onClassify).toHaveBeenCalledWith("ing-42");
  });

  it("isMutating deshabilita los botones de acción", () => {
    render(
      <IngestionItemRow
        item={baseItem({ status: "pendiente-metadata" })}
        onClassify={vi.fn()}
        onReject={vi.fn()}
        isMutating
      />,
    );
    expect(screen.getByRole("button", { name: /clasificar/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /rechazar/i })).toBeDisabled();
  });

  it("muestra metadata: tamaño, páginas y carpeta/tipo sugeridos", () => {
    const { container } = render(
      <IngestionItemRow
        item={baseItem({
          sizeBytes: 1024 * 1024,
          paginas: 12,
          carpetaSugerida: "TEC",
          tipoSugerido: "MTEC",
        })}
        onClassify={vi.fn()}
        onReject={vi.fn()}
      />,
    );
    const text = container.textContent ?? "";
    expect(text).toContain("1.0 MB");
    expect(text).toContain("12 pág.");
    expect(text).toContain("TEC/MTEC");
  });
});
