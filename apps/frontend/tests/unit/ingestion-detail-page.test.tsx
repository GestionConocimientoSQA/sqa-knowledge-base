import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import IngestionDetailPage from "@/app/(app)/ingestion/[itemId]/page";
import { __resetIngestionStub } from "@/lib/api/ingestion";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const useAuthMock = vi.fn();
vi.mock("@/lib/auth/auth-provider", () => ({
  useAuth: () => useAuthMock(),
}));

const pushMock = vi.fn();
const paramsMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
  useParams: () => paramsMock(),
  usePathname: () => "/ingestion/x",
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

describe("IngestionDetailPage", () => {
  beforeEach(() => {
    __resetIngestionStub();
    useAuthMock.mockReset();
    paramsMock.mockReset();
    pushMock.mockClear();
  });

  it("gating: usuario no admin ve acceso restringido", () => {
    useAuthMock.mockReturnValue({
      user: {
        oid: "x",
        email: "x@sqa.co",
        name: "Lucía",
        roleId: "capturador",
        isAdmin: false,
      },
      isLoading: false,
    });
    paramsMock.mockReturnValue({ itemId: "ing-0002" });

    render(<IngestionDetailPage />, { wrapper: makeWrapper() });

    expect(screen.getByText(/acceso restringido/i)).toBeInTheDocument();
  });

  it("item revisable (en-revision): muestra el TraceabilityForm", async () => {
    useAuthMock.mockReturnValue({
      user: {
        oid: "y",
        email: "owner@sqa.co",
        name: "Camila Pereyra",
        roleId: "owner",
        isAdmin: true,
      },
      isLoading: false,
    });
    paramsMock.mockReturnValue({ itemId: "ing-0002" });

    render(<IngestionDetailPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Plantilla-Casos-Aceptacion.xlsx" }),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByRole("form", { name: /trazabilidad/i }),
    ).toBeInTheDocument();
    // Preview placeholder visible
    expect(screen.getByTestId("preview-placeholder")).toBeInTheDocument();
  });

  it("item indexado: NO muestra el form, muestra 'Item cerrado'", async () => {
    useAuthMock.mockReturnValue({
      user: {
        oid: "z",
        email: "gk@sqa.co",
        name: "Andrés",
        roleId: "gklead",
        isAdmin: true,
      },
      isLoading: false,
    });
    paramsMock.mockReturnValue({ itemId: "ing-0003" });

    render(<IngestionDetailPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Memoria-Tecnica-Migracion-PG.pdf" }),
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/item cerrado/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("form", { name: /trazabilidad/i }),
    ).toBeNull();
  });

  it("item rechazado: muestra errorDetail como alerta", async () => {
    useAuthMock.mockReturnValue({
      user: {
        oid: "z",
        email: "gk@sqa.co",
        name: "Andrés",
        roleId: "gklead",
        isAdmin: true,
      },
      isLoading: false,
    });
    paramsMock.mockReturnValue({ itemId: "ing-0004" });

    render(<IngestionDetailPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "borrador-sin-estructura.pdf" }),
      ).toBeInTheDocument();
    });
    const alerts = screen.getAllByRole("alert");
    expect(
      alerts.some((el) =>
        el.textContent?.includes("No se pudo extraer texto del archivo."),
      ),
    ).toBe(true);
  });

  it("id inexistente: muestra empty state 'Item no encontrado'", async () => {
    useAuthMock.mockReturnValue({
      user: {
        oid: "z",
        email: "gk@sqa.co",
        name: "Andrés",
        roleId: "gklead",
        isAdmin: true,
      },
      isLoading: false,
    });
    paramsMock.mockReturnValue({ itemId: "no-existe" });

    render(<IngestionDetailPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/item no encontrado/i)).toBeInTheDocument();
    });
  });
});
