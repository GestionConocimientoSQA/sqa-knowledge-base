/**
 * Hook + parser/serializer del estado del Explorer en la URL.
 *
 * El estado vive en `URLSearchParams`. La página es shareable: copiar la
 * URL reproduce los mismos filtros, paginación y orden.
 *
 * Las funciones `parseExplorerSearchParams` y `serializeExplorerSearchParams`
 * son puras y se exportan aparte para poder testearlas sin montar React/Next.
 * El hook solo conecta esas funciones con `useSearchParams` + `useRouter`.
 */
"use client";

import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type {
  CategoryCode,
  DocStatus,
  DocTypeCode,
  DocumentSearchFilters,
  DocumentSearchParams,
  DocumentSortBy,
} from "@/types/domain";

const VALID_CATEGORIES: ReadonlySet<CategoryCode> = new Set<CategoryCode>([
  "PROC",
  "TEC",
  "ARQ",
  "HERR",
  "NEG",
  "ENV",
  "EST",
  "CONT",
]);

const VALID_DOC_TYPES: ReadonlySet<DocTypeCode> = new Set<DocTypeCode>([
  "POL",
  "PROC",
  "GUIA",
  "INST",
  "SERV",
  "MTEC",
  "ACEL",
  "UEN",
  "ARCL",
  "FORM",
  "PRES",
]);

const VALID_ESTADOS: ReadonlySet<DocStatus> = new Set<DocStatus>([
  "borrador",
  "generado",
  "en-revision",
  "aprobado",
  "vigente",
  "obsoleto",
  "reemplazado",
  "archivado",
]);

const VALID_SORTS: ReadonlySet<DocumentSortBy> = new Set<DocumentSortBy>([
  "relevance",
  "date_desc",
  "score_desc",
  "citations_desc",
]);

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Estado mínimo (URL-only) del Explorer. Se serializa a `?q=…&carpetas=TEC,ARQ&…`.
 */
export interface ExplorerSearchParams {
  query: string;
  filters: DocumentSearchFilters;
  page: number;
  limit: number;
  sortBy?: DocumentSortBy;
}

export const DEFAULT_EXPLORER_LIMIT = 20;

export const EMPTY_EXPLORER_PARAMS: ExplorerSearchParams = {
  query: "",
  filters: {},
  page: 1,
  limit: DEFAULT_EXPLORER_LIMIT,
};

interface URLSearchParamsLike {
  get(name: string): string | null;
}

function parseList<T>(
  raw: string | null,
  validator: ReadonlySet<T>,
): T[] | undefined {
  if (!raw) return undefined;
  const items = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0) as T[];
  const filtered = items.filter((item) => validator.has(item));
  return filtered.length > 0 ? filtered : undefined;
}

function parseTriState(raw: string | null): boolean | undefined {
  if (raw === "1" || raw === "true") return true;
  if (raw === "0" || raw === "false") return false;
  return undefined;
}

function parseFloatInRange(
  raw: string | null,
  min: number,
  max: number,
): number | undefined {
  if (raw === null) return undefined;
  const n = Number.parseFloat(raw);
  if (!Number.isFinite(n)) return undefined;
  if (n < min || n > max) return undefined;
  return n;
}

function parseIsoDate(raw: string | null): string | undefined {
  if (!raw || !DATE_RE.test(raw)) return undefined;
  return raw;
}

function parsePositiveInt(
  raw: string | null,
  fallback: number,
  max = 10_000,
): number {
  if (raw === null) return fallback;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n < 1 || n > max) return fallback;
  return n;
}

/**
 * Parsea una `URLSearchParams` a `ExplorerSearchParams`. Valores inválidos
 * se ignoran silenciosamente — la página no debe romper si la URL viene
 * tampered o si un viejo bookmark trae un sort que ya no existe.
 */
export function parseExplorerSearchParams(
  searchParams: URLSearchParamsLike,
): ExplorerSearchParams {
  const filters: DocumentSearchFilters = {};

  const carpetas = parseList<CategoryCode>(
    searchParams.get("carpetas"),
    VALID_CATEGORIES,
  );
  if (carpetas) filters.carpetas = carpetas;

  const tipos = parseList<DocTypeCode>(
    searchParams.get("tipos"),
    VALID_DOC_TYPES,
  );
  if (tipos) filters.tipos = tipos;

  const estados = parseList<DocStatus>(
    searchParams.get("estados"),
    VALID_ESTADOS,
  );
  if (estados) filters.estados = estados;

  const auth = parseTriState(searchParams.get("auth"));
  if (typeof auth === "boolean") filters.autoritativo = auth;

  const anon = parseTriState(searchParams.get("anon"));
  if (typeof anon === "boolean") filters.anonimizado = anon;

  const minScore = parseFloatInRange(searchParams.get("score"), 1, 5);
  if (typeof minScore === "number") filters.minScore = minScore;

  const dateFrom = parseIsoDate(searchParams.get("from"));
  if (dateFrom) filters.dateFrom = dateFrom;
  const dateTo = parseIsoDate(searchParams.get("to"));
  if (dateTo) filters.dateTo = dateTo;

  const author = searchParams.get("author");
  if (author && author.length > 0 && author.length < 256) {
    filters.autorOid = author;
  }

  const rawSort = searchParams.get("sort");
  const sortBy =
    rawSort && VALID_SORTS.has(rawSort as DocumentSortBy)
      ? (rawSort as DocumentSortBy)
      : undefined;

  const page = parsePositiveInt(searchParams.get("page"), 1);
  const limit = parsePositiveInt(
    searchParams.get("limit"),
    DEFAULT_EXPLORER_LIMIT,
    100,
  );

  return {
    query: (searchParams.get("q") ?? "").trim(),
    filters,
    page,
    limit,
    sortBy,
  };
}

/**
 * Serializa un `ExplorerSearchParams` a `URLSearchParams`. Solo escribe
 * claves con valor definido — la URL queda corta cuando no hay filtros.
 */
export function serializeExplorerSearchParams(
  params: ExplorerSearchParams,
): URLSearchParams {
  const out = new URLSearchParams();
  if (params.query) out.set("q", params.query);

  const { filters } = params;
  if (filters.carpetas && filters.carpetas.length > 0) {
    out.set("carpetas", filters.carpetas.join(","));
  }
  if (filters.tipos && filters.tipos.length > 0) {
    out.set("tipos", filters.tipos.join(","));
  }
  if (filters.estados && filters.estados.length > 0) {
    out.set("estados", filters.estados.join(","));
  }
  if (typeof filters.autoritativo === "boolean") {
    out.set("auth", filters.autoritativo ? "1" : "0");
  }
  if (typeof filters.anonimizado === "boolean") {
    out.set("anon", filters.anonimizado ? "1" : "0");
  }
  if (typeof filters.minScore === "number") {
    out.set("score", filters.minScore.toString());
  }
  if (filters.dateFrom) out.set("from", filters.dateFrom);
  if (filters.dateTo) out.set("to", filters.dateTo);
  if (filters.autorOid) out.set("author", filters.autorOid);

  if (params.page > 1) out.set("page", params.page.toString());
  if (params.limit !== DEFAULT_EXPLORER_LIMIT) {
    out.set("limit", params.limit.toString());
  }
  if (params.sortBy) out.set("sort", params.sortBy);

  return out;
}

/**
 * Devuelve true si el filtro `key` tiene un valor activo (no equivalente
 * a "sin filtrar"). Útil para contar filtros aplicados.
 */
function isFilterActive<K extends keyof DocumentSearchFilters>(
  filters: DocumentSearchFilters,
  key: K,
): boolean {
  const v = filters[key];
  if (v === undefined || v === null) return false;
  if (Array.isArray(v)) return v.length > 0;
  return true;
}

export function countActiveFilters(filters: DocumentSearchFilters): number {
  let n = 0;
  if (isFilterActive(filters, "carpetas")) n++;
  if (isFilterActive(filters, "tipos")) n++;
  if (isFilterActive(filters, "estados")) n++;
  if (isFilterActive(filters, "autoritativo")) n++;
  if (isFilterActive(filters, "anonimizado")) n++;
  if (isFilterActive(filters, "minScore")) n++;
  if (isFilterActive(filters, "dateFrom") || isFilterActive(filters, "dateTo")) {
    n++;
  }
  if (isFilterActive(filters, "autorOid")) n++;
  return n;
}

export interface UseExplorerFiltersResult {
  params: ExplorerSearchParams;
  /** Forma compatible con `searchDocuments(...)` del API stub. */
  searchParams: DocumentSearchParams;
  activeFilterCount: number;
  setQuery: (query: string) => void;
  setFilters: (next: DocumentSearchFilters) => void;
  patchFilters: (patch: Partial<DocumentSearchFilters>) => void;
  setPage: (page: number) => void;
  setSort: (sortBy: DocumentSortBy | undefined) => void;
  reset: () => void;
}

/**
 * Cualquier mutación del estado resetea `page` a 1 EXCEPTO `setPage` mismo
 * — cambiar un filtro mientras estás en la página 5 te dejaría con una
 * página vacía y confusión.
 */
export function useExplorerFilters(): UseExplorerFiltersResult {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const params = useMemo(
    () => parseExplorerSearchParams(searchParams),
    [searchParams],
  );

  const push = useCallback(
    (next: ExplorerSearchParams) => {
      const qs = serializeExplorerSearchParams(next).toString();
      const href = qs.length > 0 ? `${pathname}?${qs}` : pathname;
      router.replace(href as never, { scroll: false });
    },
    [router, pathname],
  );

  const setQuery = useCallback(
    (query: string) => {
      push({ ...params, query: query.trim(), page: 1 });
    },
    [params, push],
  );

  const setFilters = useCallback(
    (filters: DocumentSearchFilters) => {
      push({ ...params, filters, page: 1 });
    },
    [params, push],
  );

  const patchFilters = useCallback(
    (patch: Partial<DocumentSearchFilters>) => {
      push({
        ...params,
        filters: { ...params.filters, ...patch },
        page: 1,
      });
    },
    [params, push],
  );

  const setPage = useCallback(
    (page: number) => {
      push({ ...params, page: Math.max(1, page) });
    },
    [params, push],
  );

  const setSort = useCallback(
    (sortBy: DocumentSortBy | undefined) => {
      push({ ...params, sortBy, page: 1 });
    },
    [params, push],
  );

  const reset = useCallback(() => {
    push(EMPTY_EXPLORER_PARAMS);
  }, [push]);

  const activeFilterCount = useMemo(
    () => countActiveFilters(params.filters),
    [params.filters],
  );

  const apiParams: DocumentSearchParams = useMemo(() => {
    const out: DocumentSearchParams = {
      filters: params.filters,
      page: params.page,
      limit: params.limit,
    };
    if (params.query) out.query = params.query;
    if (params.sortBy) out.sortBy = params.sortBy;
    return out;
  }, [params]);

  return {
    params,
    searchParams: apiParams,
    activeFilterCount,
    setQuery,
    setFilters,
    patchFilters,
    setPage,
    setSort,
    reset,
  };
}
