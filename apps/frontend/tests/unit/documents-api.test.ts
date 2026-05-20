import { describe, it, expect } from "vitest";
import {
  getDocument,
  getDocumentDetail,
  listCategories,
  listDocuments,
  listHotTopics,
  listMyCaptures,
  listRecentActivity,
  searchDocuments,
} from "@/lib/api/documents";
import { AUTHOR_OIDS, DOCS, FOLDERS } from "@/lib/mocks/data";

describe("documents API (stub) — listas base", () => {
  it("listDocuments devuelve todos los mocks", async () => {
    const docs = await listDocuments();
    expect(docs.length).toBe(DOCS.length);
    expect(docs.length).toBeGreaterThanOrEqual(40);
  });

  it("listCategories devuelve las 8 carpetas", async () => {
    const cats = await listCategories();
    expect(cats.length).toBe(FOLDERS.length);
    expect(cats.map((c) => c.code)).toContain("TEC");
  });

  it("getDocument por id existente devuelve el doc", async () => {
    const doc = await getDocument("TEC-flakiness-detection-2026-04-22");
    expect(doc).not.toBeNull();
    expect(doc?.titulo).toContain("flaky");
  });

  it("getDocument por id inexistente devuelve null", async () => {
    expect(await getDocument("no-existe-123")).toBeNull();
  });
});

describe("documents API (stub) — searchDocuments", () => {
  it("sin params: pagina con limit por defecto (20)", async () => {
    const res = await searchDocuments();
    expect(res.page).toBe(1);
    expect(res.limit).toBe(20);
    expect(res.items.length).toBe(Math.min(20, DOCS.length));
    expect(res.total).toBe(DOCS.length);
    expect(res.hasMore).toBe(DOCS.length > 20);
  });

  it("paginación: page=2 devuelve la página siguiente sin overlap con page=1", async () => {
    const p1 = await searchDocuments({ page: 1, limit: 10 });
    const p2 = await searchDocuments({ page: 2, limit: 10 });
    const ids1 = new Set(p1.items.map((d) => d.id));
    const overlap = p2.items.filter((d) => ids1.has(d.id));
    expect(overlap).toHaveLength(0);
    expect(p2.items.length).toBeGreaterThan(0);
  });

  it("filtra por carpetas", async () => {
    const res = await searchDocuments({ filters: { carpetas: ["TEC"] }, limit: 100 });
    expect(res.items.length).toBeGreaterThan(0);
    expect(res.items.every((d) => d.carpeta === "TEC")).toBe(true);
  });

  it("filtra por múltiples carpetas (OR semántico)", async () => {
    const res = await searchDocuments({
      filters: { carpetas: ["TEC", "ARQ"] },
      limit: 100,
    });
    expect(res.items.every((d) => d.carpeta === "TEC" || d.carpeta === "ARQ")).toBe(
      true,
    );
  });

  it("filtra por tipo de documento", async () => {
    const res = await searchDocuments({ filters: { tipos: ["POL"] }, limit: 100 });
    expect(res.items.every((d) => d.tipo === "POL")).toBe(true);
  });

  it("filtra por autoritativo=true", async () => {
    const res = await searchDocuments({
      filters: { autoritativo: true },
      limit: 100,
    });
    expect(res.items.every((d) => d.autoritativo === true)).toBe(true);
  });

  it("filtra por minScore", async () => {
    const res = await searchDocuments({ filters: { minScore: 4.5 }, limit: 100 });
    expect(res.items.every((d) => d.score >= 4.5)).toBe(true);
  });

  it("filtra por rango de fecha", async () => {
    const res = await searchDocuments({
      filters: { dateFrom: "2026-01-01", dateTo: "2026-04-30" },
      limit: 100,
    });
    expect(
      res.items.every((d) => d.fecha >= "2026-01-01" && d.fecha <= "2026-04-30"),
    ).toBe(true);
  });

  it("query textual matchea por título o tags (case-insensitive)", async () => {
    const res = await searchDocuments({ query: "playwright", limit: 100 });
    expect(res.items.length).toBeGreaterThan(0);
    expect(
      res.items.every((d) =>
        `${d.titulo} ${d.tags.join(" ")} ${d.autor}`
          .toLowerCase()
          .includes("playwright"),
      ),
    ).toBe(true);
  });

  it("query vacía o whitespace no aplica filtro textual", async () => {
    const all = await searchDocuments({ limit: 100 });
    const empty = await searchDocuments({ query: "   ", limit: 100 });
    expect(empty.total).toBe(all.total);
  });

  it("sort date_desc devuelve fechas en orden descendente", async () => {
    const res = await searchDocuments({ sortBy: "date_desc", limit: 100 });
    for (let i = 1; i < res.items.length; i++) {
      expect(res.items[i - 1]!.fecha >= res.items[i]!.fecha).toBe(true);
    }
  });

  it("sort score_desc devuelve scores en orden descendente", async () => {
    const res = await searchDocuments({ sortBy: "score_desc", limit: 100 });
    for (let i = 1; i < res.items.length; i++) {
      expect(res.items[i - 1]!.score >= res.items[i]!.score).toBe(true);
    }
  });

  it("sort citations_desc devuelve citas en orden descendente", async () => {
    const res = await searchDocuments({ sortBy: "citations_desc", limit: 100 });
    for (let i = 1; i < res.items.length; i++) {
      expect(res.items[i - 1]!.citas >= res.items[i]!.citas).toBe(true);
    }
  });

  it("default sort: date_desc cuando no hay query", async () => {
    const res = await searchDocuments({ limit: 100 });
    for (let i = 1; i < res.items.length; i++) {
      expect(res.items[i - 1]!.fecha >= res.items[i]!.fecha).toBe(true);
    }
  });

  it("filtros combinados se aplican en AND", async () => {
    const res = await searchDocuments({
      filters: { carpetas: ["TEC"], autoritativo: true, minScore: 4.0 },
      limit: 100,
    });
    expect(
      res.items.every(
        (d) => d.carpeta === "TEC" && d.autoritativo && d.score >= 4.0,
      ),
    ).toBe(true);
  });

  it("hasMore=false cuando la página es la última", async () => {
    const all = await searchDocuments({ limit: 1000 });
    expect(all.hasMore).toBe(false);
  });

  it("listas vacías de filtros se interpretan como sin filtrar", async () => {
    const sinFiltros = await searchDocuments({ limit: 100 });
    const conListasVacias = await searchDocuments({
      filters: { carpetas: [], tipos: [], estados: [] },
      limit: 100,
    });
    expect(conListasVacias.total).toBe(sinFiltros.total);
  });
});

describe("documents API (stub) — getDocumentDetail", () => {
  it("devuelve detail con incomingCitations + resumen para doc con datos", async () => {
    const detail = await getDocumentDetail("ARQ-microservicios-checkout-2026-02-11");
    expect(detail).not.toBeNull();
    expect(detail!.incomingCitations.length).toBeGreaterThan(0);
    expect(detail!.resumen.length).toBeGreaterThan(0);
  });

  it("devuelve detail con citations vacías para doc sin datos", async () => {
    const detail = await getDocumentDetail("CONT-vertical-retail-2025-06-22");
    expect(detail).not.toBeNull();
    expect(detail!.incomingCitations).toEqual([]);
  });

  it("devuelve null para id inexistente", async () => {
    expect(await getDocumentDetail("no-existe-456")).toBeNull();
  });
});

describe("documents API (stub) — listHotTopics", () => {
  it("devuelve la lista completa por defecto", async () => {
    const topics = await listHotTopics();
    expect(topics.length).toBeGreaterThan(0);
  });

  it("respeta el limit", async () => {
    const topics = await listHotTopics({ limit: 3 });
    expect(topics).toHaveLength(3);
  });

  it("marca al menos un topic como gap (isGap=true)", async () => {
    const topics = await listHotTopics();
    expect(topics.some((t) => t.isGap)).toBe(true);
  });
});

describe("documents API (stub) — listRecentActivity", () => {
  it("ordena por fecha descendente", async () => {
    const items = await listRecentActivity();
    for (let i = 1; i < items.length; i++) {
      expect(items[i - 1]!.at >= items[i]!.at).toBe(true);
    }
  });

  it("filtra por since (ISO)", async () => {
    const since = "2026-05-18T00:00:00.000Z";
    const items = await listRecentActivity({ since });
    expect(items.every((a) => a.at >= since)).toBe(true);
  });

  it("respeta el limit", async () => {
    const items = await listRecentActivity({ limit: 5 });
    expect(items).toHaveLength(5);
  });
});

describe("documents API (stub) — listMyCaptures (scoping por autor)", () => {
  it("filtra docs solo del autor solicitado", async () => {
    const res = await listMyCaptures(AUTHOR_OIDS.lucia);
    expect(res.items.length).toBeGreaterThan(0);
    expect(res.items.every((d) => d.autorOid === AUTHOR_OIDS.lucia)).toBe(true);
  });

  it("devuelve resultado vacío para oid sin docs", async () => {
    const res = await listMyCaptures("oid-inexistente");
    expect(res.items).toEqual([]);
    expect(res.stats.totalCaptures).toBe(0);
    expect(res.stats.totalCitationsReceived).toBe(0);
    expect(res.stats.avgScore).toBe(0);
    expect(res.stats.lastCapturedAt).toBeNull();
  });

  it("stats agregadas son consistentes con los items", async () => {
    const res = await listMyCaptures(AUTHOR_OIDS.lucia);
    const sumCitas = res.items.reduce((s, d) => s + d.citas, 0);
    expect(res.stats.totalCaptures).toBe(res.items.length);
    expect(res.stats.totalCitationsReceived).toBe(sumCitas);
    const avg = res.items.reduce((s, d) => s + d.score, 0) / res.items.length;
    expect(res.stats.avgScore).toBeCloseTo(avg, 2);
  });

  it("lastCapturedAt corresponde a la fecha más reciente de los items", async () => {
    const res = await listMyCaptures(AUTHOR_OIDS.lucia);
    const max = res.items.map((d) => d.fecha).sort().pop();
    expect(res.stats.lastCapturedAt).toBe(max);
  });

  it("ordena items por fecha descendente", async () => {
    const res = await listMyCaptures(AUTHOR_OIDS.lucia);
    for (let i = 1; i < res.items.length; i++) {
      expect(res.items[i - 1]!.fecha >= res.items[i]!.fecha).toBe(true);
    }
  });
});
