import { describe, it, expect } from "vitest";
import {
  countActiveFilters,
  DEFAULT_EXPLORER_LIMIT,
  EMPTY_EXPLORER_PARAMS,
  parseExplorerSearchParams,
  serializeExplorerSearchParams,
  type ExplorerSearchParams,
} from "@/lib/hooks/use-explorer-filters";

function fromQs(qs: string) {
  return new URLSearchParams(qs);
}

describe("parseExplorerSearchParams", () => {
  it("string vacía → estado default", () => {
    const parsed = parseExplorerSearchParams(fromQs(""));
    expect(parsed.query).toBe("");
    expect(parsed.filters).toEqual({});
    expect(parsed.page).toBe(1);
    expect(parsed.limit).toBe(DEFAULT_EXPLORER_LIMIT);
    expect(parsed.sortBy).toBeUndefined();
  });

  it("parsea query y la recorta", () => {
    expect(parseExplorerSearchParams(fromQs("q=playwright")).query).toBe("playwright");
    expect(parseExplorerSearchParams(fromQs("q=%20%20hola%20")).query).toBe("hola");
  });

  it("parsea listas de carpetas separadas por coma", () => {
    const parsed = parseExplorerSearchParams(fromQs("carpetas=TEC,ARQ"));
    expect(parsed.filters.carpetas).toEqual(["TEC", "ARQ"]);
  });

  it("ignora valores inválidos en carpetas", () => {
    const parsed = parseExplorerSearchParams(fromQs("carpetas=TEC,XX,ARQ"));
    expect(parsed.filters.carpetas).toEqual(["TEC", "ARQ"]);
  });

  it("lista totalmente inválida → carpetas undefined", () => {
    const parsed = parseExplorerSearchParams(fromQs("carpetas=XX,YY"));
    expect(parsed.filters.carpetas).toBeUndefined();
  });

  it("parsea tipos y estados", () => {
    const parsed = parseExplorerSearchParams(
      fromQs("tipos=POL,PROC&estados=vigente,obsoleto"),
    );
    expect(parsed.filters.tipos).toEqual(["POL", "PROC"]);
    expect(parsed.filters.estados).toEqual(["vigente", "obsoleto"]);
  });

  it("parsea autoritativo/anonimizado tri-state", () => {
    expect(parseExplorerSearchParams(fromQs("auth=1")).filters.autoritativo).toBe(true);
    expect(parseExplorerSearchParams(fromQs("auth=0")).filters.autoritativo).toBe(false);
    expect(parseExplorerSearchParams(fromQs("auth=true")).filters.autoritativo).toBe(true);
    expect(parseExplorerSearchParams(fromQs("auth=xx")).filters.autoritativo).toBeUndefined();
  });

  it("parsea minScore solo dentro del rango [1,5]", () => {
    expect(parseExplorerSearchParams(fromQs("score=4.2")).filters.minScore).toBe(4.2);
    expect(parseExplorerSearchParams(fromQs("score=0.5")).filters.minScore).toBeUndefined();
    expect(parseExplorerSearchParams(fromQs("score=9")).filters.minScore).toBeUndefined();
    expect(parseExplorerSearchParams(fromQs("score=abc")).filters.minScore).toBeUndefined();
  });

  it("parsea fechas solo en formato YYYY-MM-DD", () => {
    expect(parseExplorerSearchParams(fromQs("from=2026-01-01")).filters.dateFrom).toBe(
      "2026-01-01",
    );
    expect(parseExplorerSearchParams(fromQs("from=01/01/2026")).filters.dateFrom).toBeUndefined();
  });

  it("parsea autorOid (autor)", () => {
    expect(
      parseExplorerSearchParams(fromQs("author=oid-capturador-lucia")).filters.autorOid,
    ).toBe("oid-capturador-lucia");
  });

  it("ignora sort inválido", () => {
    expect(parseExplorerSearchParams(fromQs("sort=date_desc")).sortBy).toBe("date_desc");
    expect(parseExplorerSearchParams(fromQs("sort=foo")).sortBy).toBeUndefined();
  });

  it("page y limit con validación y fallback", () => {
    expect(parseExplorerSearchParams(fromQs("page=3")).page).toBe(3);
    expect(parseExplorerSearchParams(fromQs("page=0")).page).toBe(1);
    expect(parseExplorerSearchParams(fromQs("page=-5")).page).toBe(1);
    expect(parseExplorerSearchParams(fromQs("page=abc")).page).toBe(1);
    expect(parseExplorerSearchParams(fromQs("limit=50")).limit).toBe(50);
    expect(parseExplorerSearchParams(fromQs("limit=999999")).limit).toBe(DEFAULT_EXPLORER_LIMIT);
  });
});

describe("serializeExplorerSearchParams", () => {
  it("estado vacío → URL vacía", () => {
    const qs = serializeExplorerSearchParams(EMPTY_EXPLORER_PARAMS).toString();
    expect(qs).toBe("");
  });

  it("escribe query, carpetas (comma-joined), sort y page>1", () => {
    const params: ExplorerSearchParams = {
      query: "playwright",
      filters: { carpetas: ["TEC", "ARQ"] },
      page: 3,
      limit: DEFAULT_EXPLORER_LIMIT,
      sortBy: "score_desc",
    };
    const qs = serializeExplorerSearchParams(params);
    expect(qs.get("q")).toBe("playwright");
    expect(qs.get("carpetas")).toBe("TEC,ARQ");
    expect(qs.get("sort")).toBe("score_desc");
    expect(qs.get("page")).toBe("3");
    expect(qs.has("limit")).toBe(false); // omite limit cuando es el default
  });

  it("omite filtros con listas vacías", () => {
    const params: ExplorerSearchParams = {
      ...EMPTY_EXPLORER_PARAMS,
      filters: { carpetas: [], tipos: [], estados: [] },
    };
    const qs = serializeExplorerSearchParams(params).toString();
    expect(qs).toBe("");
  });

  it("serializa booleanos como 1/0", () => {
    const qs = serializeExplorerSearchParams({
      ...EMPTY_EXPLORER_PARAMS,
      filters: { autoritativo: true, anonimizado: false },
    });
    expect(qs.get("auth")).toBe("1");
    expect(qs.get("anon")).toBe("0");
  });

  it("escribe limit solo cuando difiere del default", () => {
    const qs = serializeExplorerSearchParams({
      ...EMPTY_EXPLORER_PARAMS,
      limit: 50,
    });
    expect(qs.get("limit")).toBe("50");
  });
});

describe("round-trip parse → serialize → parse es estable", () => {
  it.each([
    "q=ci&carpetas=TEC,HERR&auth=1&sort=date_desc",
    "tipos=POL,PROC&score=4.2&from=2026-01-01&to=2026-04-30",
    "carpetas=ARQ&page=2&author=oid-gklead-andres",
  ])("%s", (qs) => {
    const parsed = parseExplorerSearchParams(fromQs(qs));
    const reSerialized = serializeExplorerSearchParams(parsed);
    const reParsed = parseExplorerSearchParams(reSerialized);
    expect(reParsed).toEqual(parsed);
  });
});

describe("countActiveFilters", () => {
  it("retorna 0 cuando no hay filtros", () => {
    expect(countActiveFilters({})).toBe(0);
  });

  it("listas vacías no cuentan", () => {
    expect(countActiveFilters({ carpetas: [], tipos: [] })).toBe(0);
  });

  it("cuenta cada dimensión activa una vez", () => {
    expect(
      countActiveFilters({
        carpetas: ["TEC"],
        tipos: ["POL"],
        autoritativo: true,
        minScore: 4.0,
      }),
    ).toBe(4);
  });

  it("dateFrom y dateTo cuentan como un solo filtro 'rango'", () => {
    expect(countActiveFilters({ dateFrom: "2026-01-01" })).toBe(1);
    expect(countActiveFilters({ dateTo: "2026-04-30" })).toBe(1);
    expect(
      countActiveFilters({ dateFrom: "2026-01-01", dateTo: "2026-04-30" }),
    ).toBe(1);
  });
});
