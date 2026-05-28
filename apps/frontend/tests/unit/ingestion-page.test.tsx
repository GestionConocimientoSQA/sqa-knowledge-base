import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import IngestionPage from "@/app/(app)/ingestion/page";
import { __resetIngestionStub } from "@/lib/api/ingestion";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// Mockeamos `useAuth` para controlar el rol entre tests sin depender del
// localStorage del stub MSAL.
const useAuthMock = vi.fn();
vi.mock("@/lib/auth/auth-provider", () => ({
  useAuth: () => useAuthMock(),
}));

// next/link en el test runner no necesita prefetch ni client-side nav.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/ingestion",
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

describe("IngestionPage", () => {
  beforeEach(() => {
    __resetIngestionStub();
    useAuthMock.mockReset();
  });

  it("gating: capturador (no admin) ve mensaje de acceso restringido", () => {
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

    render(<IngestionPage />, { wrapper: makeWrapper() });

    expect(screen.getByText(/acceso restringido/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /cola de ingesta/i }),
    ).toBeNull();
    expect(screen.queryByLabelText(/filtros por estado/i)).toBeNull();
  });

  it("owner: renderiza upload-zone + tabs + queue por defecto en Pendientes", async () => {
    useAuthMock.mockReturnValue({
      user: {
        oid: "y",
        email: "owner@sqa.co",
        name: "Camila",
        roleId: "owner",
        isAdmin: true,
      },
      isLoading: false,
    });

    render(<IngestionPage />, { wrapper: makeWrapper() });

    expect(screen.getByRole("heading", { name: /cola de ingesta/i })).toBeInTheDocument();
    expect(screen.getByTestId("upload-zone")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /pendientes/i })).toHaveAttribute(
      "data-state",
      "active",
    );

    // El seed tiene 1 item pendiente-metadata: Politica_Seguridad_QA_v3.docx
    await waitFor(() => {
      expect(
        screen.getByText(/Politica_Seguridad_QA_v3\.docx/),
      ).toBeInTheDocument();
    });
  });

  it("renderiza las 4 tabs canónicas", () => {
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

    render(<IngestionPage />, { wrapper: makeWrapper() });

    expect(screen.getByRole("tab", { name: /pendientes/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /en revisión/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /completados/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /rechazados/i })).toBeInTheDocument();
  });
});
