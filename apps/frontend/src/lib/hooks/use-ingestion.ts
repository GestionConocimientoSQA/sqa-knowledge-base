/**
 * Hooks TanStack Query para la cola de ingesta (Fase 8.3).
 *
 * Encapsula el contrato `lib/api/ingestion` detrás de React Query: cache
 * compartida, refetch en background y mutaciones que invalidan la lista.
 * La UI nunca llama al api directo — siempre pasa por estos hooks (SRP +
 * DIP: el día que migremos a SWR o a websockets solo cambia este archivo).
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import {
  approveIngestion,
  classifyIngestion,
  getIngestion,
  listIngestion,
  rejectIngestion,
} from "@/lib/api/ingestion";
import type {
  IngestionItem,
  IngestionStatus,
  TraceabilityInput,
} from "@/types/domain";

const INGESTION_KEY = ["ingestion"] as const;

/** Refetch cada 15 s — la cola es de baja escritura y alto valor de frescura. */
const REFETCH_INTERVAL_MS = 15_000;

export function useIngestionList(
  statuses?: IngestionStatus[],
): UseQueryResult<IngestionItem[]> {
  return useQuery({
    queryKey: [...INGESTION_KEY, "list", statuses ?? []],
    queryFn: () => listIngestion(statuses),
    refetchInterval: REFETCH_INTERVAL_MS,
    staleTime: 5_000,
  });
}

export function useIngestionItem(
  itemId: string | null | undefined,
): UseQueryResult<IngestionItem> {
  return useQuery({
    queryKey: [...INGESTION_KEY, "item", itemId],
    queryFn: () => getIngestion(itemId as string),
    enabled: Boolean(itemId),
    staleTime: 5_000,
  });
}

function useInvalidateList() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: INGESTION_KEY });
}

export function useClassifyIngestion(): UseMutationResult<
  IngestionItem,
  Error,
  string
> {
  const invalidate = useInvalidateList();
  return useMutation({
    mutationFn: (itemId: string) => classifyIngestion(itemId),
    onSuccess: () => {
      void invalidate();
    },
  });
}

export interface ApproveArgs {
  itemId: string;
  traceability: TraceabilityInput;
}

export function useApproveIngestion(): UseMutationResult<
  IngestionItem,
  Error,
  ApproveArgs
> {
  const invalidate = useInvalidateList();
  return useMutation({
    mutationFn: ({ itemId, traceability }: ApproveArgs) =>
      approveIngestion(itemId, traceability),
    onSuccess: () => {
      void invalidate();
    },
  });
}

export interface RejectArgs {
  itemId: string;
  reason: string;
}

export function useRejectIngestion(): UseMutationResult<
  IngestionItem,
  Error,
  RejectArgs
> {
  const invalidate = useInvalidateList();
  return useMutation({
    mutationFn: ({ itemId, reason }: RejectArgs) =>
      rejectIngestion(itemId, reason),
    onSuccess: () => {
      void invalidate();
    },
  });
}
