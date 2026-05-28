/**
 * API de la cola de ingesta (modo C) — Fase 8.
 *
 * Consume los endpoints `/ingestion` del backend (Fase 4). Mismo patrón
 * DIP que `documents.ts`: con `NEXT_PUBLIC_API_URL` seteada hace HTTP
 * real; sin ella cae a un mock-stub en memoria para que tests y la
 * navegación sin backend funcionen.
 *
 * El mock-stub mantiene una copia mutable de los items para que las
 * acciones (classify/approve/reject/upload) se reflejen entre llamadas
 * dentro de la misma sesión del navegador.
 */
import { api, USE_REAL_API } from "@/lib/api/client";
import { INGESTION_PENDING } from "@/lib/mocks/data";
import type {
  IngestionItem,
  IngestionStatus,
  TraceabilityInput,
} from "@/types/domain";

const STUB_DELAY_MS = 200;

function delay<T>(value: T, ms = STUB_DELAY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

// Copia mutable para el mock — las mutaciones persisten en memoria.
let stubItems: IngestionItem[] = INGESTION_PENDING.map((i) => ({ ...i }));

/** Resetea el estado del stub (para tests). */
export function __resetIngestionStub(): void {
  stubItems = INGESTION_PENDING.map((i) => ({ ...i }));
}

// ===========================================================================
// list
// ===========================================================================

export async function listIngestion(
  statuses?: IngestionStatus[],
): Promise<IngestionItem[]> {
  if (USE_REAL_API) {
    const search = new URLSearchParams();
    for (const s of statuses ?? []) search.append("status", s);
    const qs = search.toString();
    return api.get(`ingestion${qs ? `?${qs}` : ""}`).json<IngestionItem[]>();
  }
  const filtered = statuses?.length
    ? stubItems.filter((i) => statuses.includes(i.status))
    : stubItems;
  return delay(filtered.map((i) => ({ ...i })));
}

// ===========================================================================
// get by id
// ===========================================================================

/**
 * Fetch puntual de un item por su id.
 *
 * El backend Fase 4 aún no expone `GET /ingestion/{id}` (la lista filtra por
 * status pero no hay detail). Mientras tanto:
 *   - real-api: traemos la lista completa y filtramos client-side. Es
 *     aceptable para una cola de baja cardinalidad (<200 items). Cuando el
 *     backend exponga el endpoint detail, swap directo acá.
 *   - stub: busca en memoria.
 * Lanza si el id no existe.
 */
export async function getIngestion(itemId: string): Promise<IngestionItem> {
  if (USE_REAL_API) {
    const all = await api.get("ingestion").json<IngestionItem[]>();
    const found = all.find((i) => i.id === itemId);
    if (!found) {
      throw new Error(`Item de ingesta ${itemId} no encontrado`);
    }
    return found;
  }
  const found = stubItems.find((i) => i.id === itemId);
  if (!found) {
    throw new Error(`Item de ingesta ${itemId} no encontrado (stub)`);
  }
  return delay({ ...found });
}

// ===========================================================================
// upload
// ===========================================================================

export async function uploadIngestion(
  file: File,
  sourceOrigin = "",
): Promise<IngestionItem> {
  if (USE_REAL_API) {
    const form = new FormData();
    form.append("file", file);
    const qs = sourceOrigin
      ? `?sourceOrigin=${encodeURIComponent(sourceOrigin)}`
      : "";
    return api.post(`ingestion${qs}`, { body: form }).json<IngestionItem>();
  }
  const item: IngestionItem = {
    id: `ing-${Math.random().toString(36).slice(2, 10)}`,
    filename: file.name,
    sizeBytes: file.size,
    paginas: 0,
    carpetaSugerida: null,
    tipoSugerido: null,
    aprobadorOid: null,
    aprobadorName: "",
    fechaAprobacion: null,
    fuenteOriginal: sourceOrigin,
    version: "",
    status: "pendiente-metadata",
    uploadedByOid: "stub-user",
    uploadedAt: new Date().toISOString(),
    blobPath: `stub/${file.name}`,
    errorDetail: null,
  };
  stubItems = [item, ...stubItems];
  return delay(item);
}

// ===========================================================================
// classify
// ===========================================================================

export async function classifyIngestion(itemId: string): Promise<IngestionItem> {
  if (USE_REAL_API) {
    return api.post(`ingestion/${itemId}/classify`).json<IngestionItem>();
  }
  return delay(
    mutateStub(itemId, {
      status: "en-revision",
      carpetaSugerida: "TEC",
      tipoSugerido: "MTEC",
      paginas: 4,
    }),
  );
}

// ===========================================================================
// approve
// ===========================================================================

export async function approveIngestion(
  itemId: string,
  traceability: TraceabilityInput,
): Promise<IngestionItem> {
  if (USE_REAL_API) {
    return api
      .post(`ingestion/${itemId}/approve`, { json: traceability })
      .json<IngestionItem>();
  }
  return delay(
    mutateStub(itemId, {
      status: "indexado",
      aprobadorName: traceability.approvedBy,
      fechaAprobacion: traceability.approvalDate,
      fuenteOriginal: traceability.sourceOrigin,
      version: traceability.version,
      carpetaSugerida: traceability.category,
      tipoSugerido: traceability.documentType,
    }),
  );
}

// ===========================================================================
// reject
// ===========================================================================

export async function rejectIngestion(
  itemId: string,
  reason: string,
): Promise<IngestionItem> {
  if (USE_REAL_API) {
    return api
      .post(`ingestion/${itemId}/reject`, { json: { reason } })
      .json<IngestionItem>();
  }
  return delay(mutateStub(itemId, { status: "rechazado", errorDetail: reason }));
}

// ===========================================================================
// Helpers del stub
// ===========================================================================

function mutateStub(
  itemId: string,
  patch: Partial<IngestionItem>,
): IngestionItem {
  let updated: IngestionItem | undefined;
  stubItems = stubItems.map((i) => {
    if (i.id !== itemId) return i;
    updated = { ...i, ...patch };
    return updated;
  });
  if (!updated) {
    throw new Error(`Item de ingesta ${itemId} no encontrado (stub)`);
  }
  return { ...updated };
}
