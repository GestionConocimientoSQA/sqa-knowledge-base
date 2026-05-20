"use client";

import { useQuery } from "@tanstack/react-query";
import { LibraryBig, SearchX } from "lucide-react";
import { PageContainer } from "@/components/shared/page-container";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { SearchInput } from "@/components/explorer/search-input";
import { FilterBar } from "@/components/explorer/filter-bar";
import { Pagination } from "@/components/explorer/pagination";
import { DocumentCard } from "@/components/explorer/document-card";
import { useExplorerFilters } from "@/lib/hooks/use-explorer-filters";
import { searchDocuments } from "@/lib/api/documents";

export default function ExplorerPage() {
  const {
    params,
    searchParams,
    activeFilterCount,
    setQuery,
    patchFilters,
    setPage,
    setSort,
    reset,
  } = useExplorerFilters();

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: ["documents", "search", searchParams],
    queryFn: () => searchDocuments(searchParams),
    placeholderData: (prev) => prev,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const hasAnyFilter = activeFilterCount > 0 || params.query.length > 0;

  return (
    <PageContainer>
      <div className="mb-4">
        <div className="eyebrow">Catálogo</div>
        <h2 className="font-display text-2xl font-extrabold">
          Documentos indexados
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Explorá la base de conocimiento con filtros, búsqueda y ordenamiento.
        </p>
      </div>

      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center">
        <SearchInput
          value={params.query}
          onDebouncedChange={setQuery}
          placeholder="Buscar por título, tags o autor…"
          className="md:max-w-md"
        />
        <div className="text-[12px] text-muted-foreground md:ml-auto">
          {isLoading ? (
            <span aria-live="polite">Cargando…</span>
          ) : (
            <span aria-live="polite">
              <span className="font-mono">{total}</span>{" "}
              {total === 1 ? "resultado" : "resultados"}
              {isFetching && !isLoading ? " · actualizando…" : ""}
            </span>
          )}
        </div>
      </div>

      <FilterBar
        filters={params.filters}
        sortBy={params.sortBy}
        activeFilterCount={activeFilterCount}
        onPatchFilters={patchFilters}
        onSortChange={setSort}
        onClear={reset}
      />

      <div className="mt-6">
        {isLoading ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        ) : isError ? (
          <EmptyState
            icon={LibraryBig}
            title="No se pudo cargar el catálogo"
            description="Reintentá la consulta en unos minutos."
          />
        ) : items.length === 0 ? (
          hasAnyFilter ? (
            <EmptyState
              icon={SearchX}
              title="Sin resultados con esos filtros"
              description="Probá ampliar los criterios o limpiar todos los filtros."
              action={
                <Button onClick={reset} variant="outline">
                  Limpiar filtros
                </Button>
              }
            />
          ) : (
            <EmptyState
              icon={LibraryBig}
              title="No hay documentos indexados todavía"
              description="Cuando capturen o ingieran su primer documento, aparecerá acá."
            />
          )
        ) : (
          <>
            <div className="grid gap-3 lg:grid-cols-2">
              {items.map((d) => (
                <DocumentCard key={d.id} document={d} />
              ))}
            </div>
            <div className="mt-6">
              <Pagination
                page={params.page}
                limit={params.limit}
                total={total}
                onPageChange={setPage}
              />
            </div>
          </>
        )}
      </div>
    </PageContainer>
  );
}
