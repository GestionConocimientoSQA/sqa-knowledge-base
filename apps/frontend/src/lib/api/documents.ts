/**
 * API stub del catálogo de documentos. Implementa el contrato que el
 * backend Fase 1 (`GET /documents`, `GET /documents/{id}`, etc.) deberá
 * respetar. La UI consume solo estas funciones — el swap mock → backend
 * real es cambio del cuerpo de cada función, sin tocar la UI (DIP).
 *
 * No abstraemos un `DocumentRepository` interface ahora: en Fase 1
 * cuando llegue el backend, este archivo pasa a hacer `fetch` con
 * `lib/api/client.ts` (ky). No hay un segundo consumidor que justifique
 * la interfaz hoy.
 */
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

/**
 * Lista plana del catálogo. Mantenida por compatibilidad con el esqueleto
 * de Fase 5 (Explorer sin filtros). Las pantallas nuevas de Fase 7
 * consumen `searchDocuments`.
 */
export async function listDocuments(): Promise<DocumentItem[]> {
  return delay(DOCS);
}

export async function listCategories(): Promise<Category[]> {
  return delay(FOLDERS);
}

/**
 * Búsqueda paginada del catálogo. Aplica filtros, sort y paginación
 * sobre los mocks en memoria. La forma del response es estable.
 */
export async function searchDocuments(
  params: DocumentSearchParams = {},
): Promise<PaginatedResult<DocumentItem>> {
  const {
    query,
    filters = {},
    page = DEFAULT_PAGE,
    limit = DEFAULT_LIMIT,
    sortBy,
  } = params;

  let items = DOCS.slice();

  // 1) Filtro textual (mock-stub aproximado; backend Fase 3 usa hybrid).
  if (query && query.trim().length > 0) {
    const needle = query.trim().toLowerCase();
    items = items.filter((d) => {
      const haystack = `${d.titulo} ${d.tags.join(" ")} ${d.autor}`.toLowerCase();
      return haystack.includes(needle);
    });
  }

  // 2) Filtros estructurados.
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

  // 3) Ordenamiento.
  const effectiveSort: DocumentSortBy =
    sortBy ?? (query && query.trim().length > 0 ? "relevance" : "date_desc");
  items = sortItems(items, effectiveSort);

  // 4) Paginación.
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
 * Devuelve un documento por id, ya enriquecido con incoming citations
 * y resumen ejecutivo. `null` si no existe.
 */
export async function getDocument(id: string): Promise<DocumentItem | null> {
  return delay(DOCS.find((d) => d.id === id) ?? null);
}

export async function getDocumentDetail(
  id: string,
): Promise<DocumentDetail | null> {
  const doc = DOCS.find((d) => d.id === id);
  if (!doc) return delay(null);
  const detail: DocumentDetail = {
    ...doc,
    incomingCitations: INCOMING_CITATIONS[id] ?? [],
    resumen: DOCUMENT_RESUMES[id] ?? "",
  };
  return delay(detail);
}

/**
 * Top de temas demandados en los últimos 30 días. `isGap=true` señala
 * temas con demanda alta pero poca cobertura → contenido faltante.
 */
export async function listHotTopics(
  options: { limit?: number } = {},
): Promise<HotTopic[]> {
  const { limit } = options;
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
  let items = MOCK_RECENT_ACTIVITY.slice();
  if (since) {
    items = items.filter((a) => a.at >= since);
  }
  // Orden temporal estable: más reciente primero.
  items.sort((a, b) => b.at.localeCompare(a.at));
  if (typeof limit === "number") items = items.slice(0, limit);
  return delay(items);
}

/**
 * Capturas del usuario actual + stats agregadas. En backend Fase 1 se
 * filtra por `author_oid = current_user.oid` con índice sobre `autorOid`.
 */
export async function listMyCaptures(ownerOid: string): Promise<MyCapturesResult> {
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
