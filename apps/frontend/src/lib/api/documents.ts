/**
 * API del catálogo de documentos.
 *
 * Implementa el contrato `lib/api/documents.ts` que la UI consume desde Fase 5.
 * El swap mock → backend real es automático: cuando se setea
 * `NEXT_PUBLIC_API_URL` (`USE_REAL_API=true`) cada función hace HTTP contra
 * `client.ts` (ky); sin variable cae a los mocks-stub para que tests y la
 * navegación sin backend sigan funcionando.
 *
 * No abstraemos un `DocumentRepository` interface: este archivo es el único
 * lugar donde el dispatch mock/real existe, y la UI sigue dependiendo solo
 * de las funciones exportadas (DIP).
 */
import { api, USE_REAL_API } from "@/lib/api/client";
import {
  DOCS,
  DOCUMENT_RESUMES,
  FOLDERS,
  INCOMING_CITATIONS,
  MOCK_HOT_TOPICS,
  MOCK_RECENT_ACTIVITY,
} from "@/lib/mocks/data";
import type {
  Category,
  DocumentDetail,
  DocumentItem,
  DocumentSearchParams,
  DocumentSortBy,
  HotTopic,
  MyCapturesResult,
  PaginatedResult,
  RecentActivityItem,
} from "@/types/domain";

const STUB_DELAY_MS = 200;

function delay<T>(value: T, ms = STUB_DELAY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

const DEFAULT_PAGE = 1;
const DEFAULT_LIMIT = 20;

// ===========================================================================
// Catálogo
// ===========================================================================

/**
 * Lista plana del catálogo. Mantenida por compatibilidad con el esqueleto
 * de Fase 5 (Explorer sin filtros). Las pantallas nuevas de Fase 7
 * consumen `searchDocuments`.
 */
export async function listDocuments(): Promise<DocumentItem[]> {
  if (USE_REAL_API) {
    const res = await searchDocuments({ limit: 100 });
    return res.items;
  }
  return delay(DOCS);
}

export async function listCategories(): Promise<Category[]> {
  if (USE_REAL_API) {
    return api.get("categories").json<Category[]>();
  }
  return delay(FOLDERS);
}

/**
 * Búsqueda paginada del catálogo. Aplica filtros, sort y paginación. Con
 * backend real, el server hace el trabajo; con stub se ejecuta en memoria.
 */
export async function searchDocuments(
  params: DocumentSearchParams = {},
): Promise<PaginatedResult<DocumentItem>> {
  if (USE_REAL_API) {
    return searchDocumentsViaApi(params);
  }
  return searchDocumentsViaMock(params);
}

async function searchDocumentsViaApi(
  params: DocumentSearchParams,
): Promise<PaginatedResult<DocumentItem>> {
  const {
    query,
    filters = {},
    page = DEFAULT_PAGE,
    limit = DEFAULT_LIMIT,
    sortBy,
  } = params;
  const search = new URLSearchParams();
  if (query && query.trim()) search.set("q", query.trim());
  if (filters.carpetas) {
    for (const c of filters.carpetas) search.append("carpetas", c);
  }
  if (filters.tipos) {
    for (const t of filters.tipos) search.append("tipos", t);
  }
  if (filters.estados) {
    for (const s of filters.estados) search.append("estados", s);
  }
  if (typeof filters.autoritativo === "boolean") {
    search.set("autoritativo", String(filters.autoritativo));
  }
  if (typeof filters.anonimizado === "boolean") {
    search.set("anonimizado", String(filters.anonimizado));
  }
  if (typeof filters.minScore === "number") {
    search.set("min_score", String(filters.minScore));
  }
  if (filters.dateFrom) search.set("date_from", filters.dateFrom);
  if (filters.dateTo) search.set("date_to", filters.dateTo);
  if (filters.autorOid) search.set("author_oid", filters.autorOid);
  if (sortBy) search.set("sort_by", sortBy);
  search.set("page", String(page));
  search.set("limit", String(limit));

  return api
    .get("documents", { searchParams: search })
    .json<PaginatedResult<DocumentItem>>();
}

async function searchDocumentsViaMock(
  params: DocumentSearchParams,
): Promise<PaginatedResult<DocumentItem>> {
  const {
    query,
    filters = {},
    page = DEFAULT_PAGE,
    limit = DEFAULT_LIMIT,
    sortBy,
  } = params;

  let items = DOCS.slice();

  if (query && query.trim().length > 0) {
    const needle = query.trim().toLowerCase();
    items = items.filter((d) => {
      const haystack = `${d.titulo} ${d.tags.join(" ")} ${d.autor}`.toLowerCase();
      return haystack.includes(needle);
    });
  }
  if (filters.carpetas && filters.carpetas.length > 0) {
    const set = new Set(filters.carpetas);
    items = items.filter((d) => set.has(d.carpeta));
  }
  if (filters.tipos && filters.tipos.length > 0) {
    const set = new Set(filters.tipos);
    items = items.filter((d) => set.has(d.tipo));
  }
  if (filters.estados && filters.estados.length > 0) {
    const set = new Set(filters.estados);
    items = items.filter((d) => set.has(d.estado));
  }
  if (typeof filters.autoritativo === "boolean") {
    items = items.filter((d) => d.autoritativo === filters.autoritativo);
  }
  if (typeof filters.anonimizado === "boolean") {
    items = items.filter((d) => d.anonimizado === filters.anonimizado);
  }
  if (typeof filters.minScore === "number") {
    items = items.filter((d) => d.score >= filters.minScore!);
  }
  if (filters.dateFrom) {
    items = items.filter((d) => d.fecha >= filters.dateFrom!);
  }
  if (filters.dateTo) {
    items = items.filter((d) => d.fecha <= filters.dateTo!);
  }
  if (filters.autorOid) {
    items = items.filter((d) => d.autorOid === filters.autorOid);
  }

  const effectiveSort: DocumentSortBy =
    sortBy ?? (query && query.trim().length > 0 ? "relevance" : "date_desc");
  items = sortItems(items, effectiveSort);

  const total = items.length;
  const safeLimit = Math.max(1, limit);
  const safePage = Math.max(1, page);
  const start = (safePage - 1) * safeLimit;
  const end = start + safeLimit;
  const sliced = items.slice(start, end);

  return delay({
    items: sliced,
    total,
    page: safePage,
    limit: safeLimit,
    hasMore: end < total,
  });
}

function sortItems(
  items: DocumentItem[],
  sortBy: DocumentSortBy,
): DocumentItem[] {
  const copy = items.slice();
  switch (sortBy) {
    case "date_desc":
      copy.sort((a, b) => b.fecha.localeCompare(a.fecha));
      break;
    case "score_desc":
      copy.sort((a, b) => b.score - a.score);
      break;
    case "citations_desc":
      copy.sort((a, b) => b.citas - a.citas);
      break;
    case "relevance":
      // Stub: score*0.6 + citations normalizadas*0.4. Backend Fase 3
      // calcula con ranking vectorial real.
      copy.sort((a, b) => relevanceOf(b) - relevanceOf(a));
      break;
  }
  return copy;
}

function relevanceOf(d: DocumentItem): number {
  return d.score * 0.6 + Math.min(d.citas, 60) * 0.04;
}

/**
 * Devuelve un documento por id. Con backend real cae al endpoint de detalle
 * y proyecta los campos comunes; con stub busca en memoria.
 */
export async function getDocument(id: string): Promise<DocumentItem | null> {
  if (USE_REAL_API) {
    return (await getDocumentDetail(id)) as DocumentItem | null;
  }
  return delay(DOCS.find((d) => d.id === id) ?? null);
}

export async function getDocumentDetail(
  id: string,
): Promise<DocumentDetail | null> {
  if (USE_REAL_API) {
    try {
      return await api.get(`documents/${id}`).json<DocumentDetail>();
    } catch (err) {
      if (isHttp404(err)) return null;
      throw err;
    }
  }
  const doc = DOCS.find((d) => d.id === id);
  if (!doc) return delay(null);
  const detail: DocumentDetail = {
    ...doc,
    incomingCitations: INCOMING_CITATIONS[id] ?? [],
    resumen: DOCUMENT_RESUMES[id] ?? "",
  };
  return delay(detail);
}

// ===========================================================================
// Dashboard
// ===========================================================================

/**
 * Top de temas demandados en los últimos 30 días. `isGap=true` señala
 * temas con demanda alta pero poca cobertura → contenido faltante.
 */
export async function listHotTopics(
  options: { limit?: number } = {},
): Promise<HotTopic[]> {
  const { limit } = options;
  if (USE_REAL_API) {
    const search = new URLSearchParams();
    if (typeof limit === "number") search.set("limit", String(limit));
    return api.get("dashboard/hot-topics", { searchParams: search }).json<HotTopic[]>();
  }
  const items = MOCK_HOT_TOPICS.slice();
  return delay(typeof limit === "number" ? items.slice(0, limit) : items);
}

/**
 * Feed de actividad reciente. `since` (ISO date) filtra acciones más
 * antiguas; `limit` recorta resultados.
 */
export async function listRecentActivity(
  options: { limit?: number; since?: string } = {},
): Promise<RecentActivityItem[]> {
  const { limit, since } = options;
  if (USE_REAL_API) {
    const search = new URLSearchParams();
    if (typeof limit === "number") search.set("limit", String(limit));
    if (since) search.set("since", since);
    return api
      .get("dashboard/activity", { searchParams: search })
      .json<RecentActivityItem[]>();
  }
  let items = MOCK_RECENT_ACTIVITY.slice();
  if (since) {
    items = items.filter((a) => a.at >= since);
  }
  items.sort((a, b) => b.at.localeCompare(a.at));
  if (typeof limit === "number") items = items.slice(0, limit);
  return delay(items);
}

// ===========================================================================
// My captures
// ===========================================================================

/**
 * Capturas del usuario actual + stats agregadas. Con backend real el filtrado
 * por `author_oid = current_user.oid` lo hace el endpoint `/my-captures`.
 * El parámetro `ownerOid` se mantiene en la firma para que el stub siga
 * funcionando sin auth real.
 */
export async function listMyCaptures(ownerOid: string): Promise<MyCapturesResult> {
  if (USE_REAL_API) {
    return api.get("my-captures").json<MyCapturesResult>();
  }
  const items = DOCS.filter((d) => d.autorOid === ownerOid);
  const totalCaptures = items.length;
  const totalCitationsReceived = items.reduce((sum, d) => sum + d.citas, 0);
  const avgScore =
    totalCaptures === 0
      ? 0
      : Math.round((items.reduce((sum, d) => sum + d.score, 0) / totalCaptures) * 100) / 100;
  const sortedByDate = items.slice().sort((a, b) => b.fecha.localeCompare(a.fecha));
  const lastCapturedAt = sortedByDate[0]?.fecha ?? null;

  return delay({
    items: sortedByDate,
    stats: {
      totalCaptures,
      totalCitationsReceived,
      avgScore,
      lastCapturedAt,
    },
  });
}

// ===========================================================================
// Mutaciones (solo backend real — los mocks no las exponen porque no las
// hay UI todavía; cuando Fase 9 admin las use, se agrega el stub)
// ===========================================================================

/**
 * Marca/desmarca un documento como autoritativo. Solo Owner sobre sus
 * carpetas o GK Lead. El backend valida el rol — el frontend solo expone
 * la acción cuando `isAdmin=true`.
 */
export async function setDocumentAuthoritative(
  documentId: string,
  value: boolean,
): Promise<DocumentItem> {
  if (!USE_REAL_API) {
    // En modo stub no hay persistencia — devolvemos el doc en memoria con
    // el flag flipeado para que la UI optimista funcione en demos.
    const found = DOCS.find((d) => d.id === documentId);
    if (!found) throw new Error(`Documento ${documentId} no existe`);
    return delay({ ...found, autoritativo: value });
  }
  return api
    .patch(`documents/${documentId}/authoritative`, { json: { value } })
    .json<DocumentItem>();
}

// ===========================================================================
// Helpers
// ===========================================================================

function isHttp404(err: unknown): boolean {
  if (typeof err !== "object" || err === null) return false;
  const e = err as { response?: { status?: number } };
  return e.response?.status === 404;
}
