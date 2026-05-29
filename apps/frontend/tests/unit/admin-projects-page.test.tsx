import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminProjectsPage from "@/app/(app)/admin/projects/page";
import { __resetProjectsStub } from "@/lib/api/projects";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const useAuthMock = vi.fn();
vi.mock("@/lib/auth/auth-provider", () => ({
  useAuth: () => useAuthMock(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/admin/projects",
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

describe("AdminProjectsPage", () => {
  beforeEach(() => {
    __resetProjectsStub();
    useAuthMock.mockReset();
  });

  it("gating: capturador ve acceso restringido", () => {
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
    render(<AdminProjectsPage />, { wrapper: makeWrapper() });
    expect(screen.getByText(/acceso restringido/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /nuevo proyecto/i }),
    ).toBeNull();
  });

  it("gating: owner global tampoco accede (solo gk_lead)", () => {
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
    render(<AdminProjectsPage />, { wrapper: makeWrapper() });
    expect(screen.getByText(/acceso restringido/i)).toBeInTheDocument();
  });

  it("gklead: lista los proyectos del seed", async () => {
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
    render(<AdminProjectsPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId("projects-list")).toBeInTheDocument();
    });
    expect(screen.getByText(/GK General/)).toBeInTheDocument();
    expect(screen.getByText(/Cliente ACME/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /nuevo proyecto/i }),
    ).toBeInTheDocument();
  });
});
