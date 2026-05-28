import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import { IngestionQueue } from "@/components/ingestion/ingestion-queue";
import { __resetIngestionStub } from "@/lib/api/ingestion";

// `sonner` toasts dependen del DOM portal — silenciarlos evita ruido visual.
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return Wrapper;
}

describe("IngestionQueue", () => {
  beforeEach(() => {
    __resetIngestionStub();
  });

  it("muestra skeletons mientras carga", () => {
    render(
      <IngestionQueue
        statuses={["en-revision"]}
        emptyMessage="sin items"
      />,
      { wrapper: makeWrapper() },
    );
    expect(screen.getByLabelText(/cargando cola/i)).toBeInTheDocument();
  });

  it("renderiza items en-revision desde el stub", async () => {
    render(
      <IngestionQueue
        statuses={["en-revision"]}
        emptyMessage="sin items"
      />,
      { wrapper: makeWrapper() },
    );
    await waitFor(() => {
      expect(screen.getByTestId("ingestion-queue")).toBeInTheDocument();
    });
    // El seed tiene 1 item en-revision: Plantilla-Casos-Aceptacion.xlsx
    expect(screen.getByText(/Plantilla-Casos-Aceptacion\.xlsx/)).toBeInTheDocument();
  });

  it("muestra empty state cuando no hay items para el filtro", async () => {
    render(
      <IngestionQueue
        statuses={["aprobado"]}
        emptyMessage="Todavía no hay items aprobados."
      />,
      { wrapper: makeWrapper() },
    );
    await waitFor(() => {
      expect(
        screen.getByText("Todavía no hay items aprobados."),
      ).toBeInTheDocument();
    });
  });

  it("filtra por múltiples estados (Completados = aprobado + indexado)", async () => {
    render(
      <IngestionQueue
        statuses={["aprobado", "indexado"]}
        emptyMessage="sin items"
      />,
      { wrapper: makeWrapper() },
    );
    await waitFor(() => {
      expect(screen.getByTestId("ingestion-queue")).toBeInTheDocument();
    });
    // El seed tiene 1 indexado: Memoria-Tecnica-Migracion-PG.pdf
    expect(
      screen.getByText(/Memoria-Tecnica-Migracion-PG\.pdf/),
    ).toBeInTheDocument();
  });

  it("rechazados: muestra item rechazado con su errorDetail", async () => {
    render(
      <IngestionQueue
        statuses={["rechazado"]}
        emptyMessage="sin items"
      />,
      { wrapper: makeWrapper() },
    );
    await waitFor(() => {
      expect(screen.getByTestId("ingestion-queue")).toBeInTheDocument();
    });
    expect(screen.getByText(/borrador-sin-estructura\.pdf/)).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "No se pudo extraer texto del archivo.",
    );
  });
});
