import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { UploadZone } from "@/components/ingestion/upload-zone";
import { __resetIngestionStub } from "@/lib/api/ingestion";
import {
  MAX_UPLOAD_BYTES,
  validateIngestionFile,
} from "@/lib/ingestion-validation";

function makeFile(name: string, size: number): File {
  const file = new File([new Uint8Array(Math.min(size, 1024))], name);
  // El File real no nos deja setear size grande; lo parcheamos.
  Object.defineProperty(file, "size", { value: size });
  return file;
}

// ===========================================================================
// validateIngestionFile
// ===========================================================================

describe("validateIngestionFile", () => {
  it("acepta formatos soportados dentro del límite", () => {
    expect(validateIngestionFile(makeFile("a.docx", 1000)).ok).toBe(true);
    expect(validateIngestionFile(makeFile("a.pdf", 1000)).ok).toBe(true);
    expect(validateIngestionFile(makeFile("a.pptx", 1000)).ok).toBe(true);
    expect(validateIngestionFile(makeFile("a.xlsx", 1000)).ok).toBe(true);
  });

  it("rechaza formato no soportado", () => {
    const r = validateIngestionFile(makeFile("a.txt", 1000));
    expect(r.ok).toBe(false);
    expect(r.error).toContain("no soportado");
  });

  it("rechaza archivo sin extensión", () => {
    const r = validateIngestionFile(makeFile("sinext", 1000));
    expect(r.ok).toBe(false);
    expect(r.error).toContain("extensión");
  });

  it("rechaza archivo vacío", () => {
    const r = validateIngestionFile(makeFile("a.docx", 0));
    expect(r.ok).toBe(false);
    expect(r.error).toContain("vacío");
  });

  it("rechaza archivo que supera el límite", () => {
    const r = validateIngestionFile(makeFile("a.docx", MAX_UPLOAD_BYTES + 1));
    expect(r.ok).toBe(false);
    expect(r.error).toContain("límite");
  });

  it("es case-insensitive con la extensión", () => {
    expect(validateIngestionFile(makeFile("A.DOCX", 1000)).ok).toBe(true);
  });
});

// ===========================================================================
// UploadZone
// ===========================================================================

describe("UploadZone", () => {
  beforeEach(() => {
    __resetIngestionStub();
  });

  it("renderiza la zona con instrucciones", () => {
    render(<UploadZone />);
    expect(screen.getByTestId("upload-zone")).toBeInTheDocument();
    expect(screen.getByText(/Arrastrá documentos/)).toBeInTheDocument();
    expect(screen.getByText(/docx, pptx, pdf, xlsx/)).toBeInTheDocument();
  });

  it("sube un archivo válido y muestra estado done + notifica", async () => {
    const onUploaded = vi.fn();
    render(<UploadZone onUploaded={onUploaded} />);
    const input = screen.getByLabelText(
      "Seleccionar archivos para ingesta",
    ) as HTMLInputElement;

    fireEvent.change(input, { target: { files: [makeFile("memoria.docx", 2048)] } });

    expect(screen.getByText("memoria.docx")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByLabelText("Subido")).toBeInTheDocument();
    });
    expect(onUploaded).toHaveBeenCalledTimes(1);
  });

  it("muestra error para archivo de formato inválido sin subirlo", async () => {
    const onUploaded = vi.fn();
    render(<UploadZone onUploaded={onUploaded} />);
    const input = screen.getByLabelText(
      "Seleccionar archivos para ingesta",
    ) as HTMLInputElement;

    fireEvent.change(input, { target: { files: [makeFile("notas.txt", 500)] } });

    expect(screen.getByLabelText("Error")).toBeInTheDocument();
    expect(screen.getByText(/no soportado/)).toBeInTheDocument();
    expect(onUploaded).not.toHaveBeenCalled();
  });
});
