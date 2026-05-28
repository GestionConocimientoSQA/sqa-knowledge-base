import { beforeEach, describe, expect, it } from "vitest";

import {
  __resetIngestionStub,
  approveIngestion,
  classifyIngestion,
  listIngestion,
  rejectIngestion,
  uploadIngestion,
} from "@/lib/api/ingestion";
import type { TraceabilityInput } from "@/types/domain";

const TRACE: TraceabilityInput = {
  approvedBy: "Camila Pereyra",
  approvalDate: "2026-05-20",
  sourceOrigin: "SharePoint/QA",
  version: "2.0",
  category: "TEC",
  documentType: "MTEC",
};

describe("ingestion API (mock-stub)", () => {
  beforeEach(() => {
    __resetIngestionStub();
  });

  it("lista todos los items sin filtro", async () => {
    const items = await listIngestion();
    expect(items.length).toBeGreaterThanOrEqual(4);
  });

  it("filtra por status", async () => {
    const enRevision = await listIngestion(["en-revision"]);
    expect(enRevision.every((i) => i.status === "en-revision")).toBe(true);
    expect(enRevision.length).toBe(1);
  });

  it("filtra por múltiples status", async () => {
    const items = await listIngestion(["indexado", "rechazado"]);
    expect(items.length).toBe(2);
    expect(items.map((i) => i.status).sort()).toEqual(["indexado", "rechazado"]);
  });

  it("upload crea un item pendiente-metadata", async () => {
    const file = new File([new Uint8Array(1234)], "nuevo.docx");
    const item = await uploadIngestion(file, "Drive/x");
    expect(item.status).toBe("pendiente-metadata");
    expect(item.filename).toBe("nuevo.docx");
    expect(item.sizeBytes).toBe(1234);
    expect(item.fuenteOriginal).toBe("Drive/x");
    // Aparece en el listado.
    const all = await listIngestion();
    expect(all.some((i) => i.id === item.id)).toBe(true);
  });

  it("classify pasa el item a en-revision con sugerencias", async () => {
    const classified = await classifyIngestion("ing-0001");
    expect(classified.status).toBe("en-revision");
    expect(classified.carpetaSugerida).not.toBeNull();
    expect(classified.tipoSugerido).not.toBeNull();
  });

  it("approve pasa el item a indexado con trazabilidad", async () => {
    const approved = await approveIngestion("ing-0002", TRACE);
    expect(approved.status).toBe("indexado");
    expect(approved.aprobadorName).toBe("Camila Pereyra");
    expect(approved.version).toBe("2.0");
    expect(approved.carpetaSugerida).toBe("TEC");
  });

  it("reject pasa el item a rechazado con motivo", async () => {
    const rejected = await rejectIngestion("ing-0001", "No cumple el estándar");
    expect(rejected.status).toBe("rechazado");
    expect(rejected.errorDetail).toBe("No cumple el estándar");
  });

  it("las mutaciones persisten entre llamadas en el stub", async () => {
    await classifyIngestion("ing-0001");
    const enRevision = await listIngestion(["en-revision"]);
    // ing-0001 (recién clasificado) + ing-0002 (ya estaba) = 2.
    expect(enRevision.some((i) => i.id === "ing-0001")).toBe(true);
  });

  it("mutar un item inexistente lanza error", async () => {
    await expect(classifyIngestion("ing-noexiste")).rejects.toThrow(
      "no encontrado",
    );
  });
});
