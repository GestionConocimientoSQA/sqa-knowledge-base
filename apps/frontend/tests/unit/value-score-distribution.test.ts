import { describe, it, expect } from "vitest";
import { __buildBucketsForTests as buildBuckets } from "@/components/dashboard/value-score-distribution";
import type { DocumentItem } from "@/types/domain";

function makeDoc(score: number): DocumentItem {
  return {
    id: `doc-${score}`,
    titulo: "x",
    carpeta: "TEC",
    tipo: "MTEC",
    autoritativo: false,
    estado: "vigente",
    autor: "x",
    rol: "x",
    fecha: "2026-01-01",
    revision: "2026-01-01",
    version: "1.0",
    citas: 0,
    score,
    anonimizado: false,
    fragmentos: 0,
    paginas: 0,
    formato: "DOCX",
    tags: [],
  };
}

describe("buildBuckets (value-score-distribution)", () => {
  it("array vacío: todos los buckets en 0", () => {
    const b = buildBuckets([]);
    expect(b).toHaveLength(5);
    expect(b.every((x) => x.count === 0)).toBe(true);
  });

  it("clasifica scores en sus buckets correctos", () => {
    const docs = [
      makeDoc(1.0), // 1.0-1.9
      makeDoc(1.9), // 1.0-1.9
      makeDoc(2.5), // 2.0-2.9
      makeDoc(3.0), // 3.0-3.9
      makeDoc(3.9), // 3.0-3.9
      makeDoc(4.2), // 4.0-4.9
      makeDoc(4.999), // 4.0-4.9 (límite inferior del 5.0)
      makeDoc(5.0), // 5.0
    ];
    const b = buildBuckets(docs);
    expect(b[0]!.count).toBe(2);
    expect(b[1]!.count).toBe(1);
    expect(b[2]!.count).toBe(2);
    expect(b[3]!.count).toBe(2);
    expect(b[4]!.count).toBe(1);
  });

  it("asigna tone correcto por rango (low/mid/high)", () => {
    const b = buildBuckets([]);
    expect(b[0]!.tone).toBe("low");
    expect(b[1]!.tone).toBe("low");
    expect(b[2]!.tone).toBe("mid");
    expect(b[3]!.tone).toBe("high");
    expect(b[4]!.tone).toBe("high");
  });

  it("respeta el orden de buckets (low→high)", () => {
    const b = buildBuckets([]);
    expect(b.map((x) => x.range)).toEqual([
      "1.0–1.9",
      "2.0–2.9",
      "3.0–3.9",
      "4.0–4.9",
      "5.0",
    ]);
  });
});
