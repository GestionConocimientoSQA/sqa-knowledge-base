import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { DocumentActionsBar } from "@/components/explorer/document-actions-bar";
import type { DocumentDetail, AuthUser } from "@/types/domain";

// Mock del auth-provider para inyectar usuario por test.
const userRef: { current: AuthUser | null } = { current: null };
vi.mock("@/lib/auth/auth-provider", () => ({
  useAuth: () => ({
    user: userRef.current,
    isLoading: false,
    signIn: vi.fn(),
    signOut: vi.fn(),
  }),
}));

function makeUser(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    oid: "oid-test",
    email: "test@sqa.co",
    name: "Test User",
    roleId: "capturador",
    isAdmin: false,
    ...overrides,
  };
}

function makeDoc(overrides: Partial<DocumentDetail> = {}): DocumentDetail {
  return {
    id: "DOC-1",
    titulo: "Doc de prueba",
    carpeta: "TEC",
    tipo: "MTEC",
    autoritativo: false,
    estado: "vigente",
    autor: "Test",
    autorOid: "oid-test",
    rol: "QA",
    fecha: "2026-05-20",
    revision: "2026-05-20",
    version: "1.0",
    citas: 0,
    score: 4.0,
    anonimizado: false,
    fragmentos: 10,
    paginas: 5,
    formato: "DOCX",
    tags: [],
    incomingCitations: [],
    resumen: "",
    ...overrides,
  };
}

describe("DocumentActionsBar", () => {
  it("Capturador (isAdmin=false): ve Descargar pero NO 'Marcar autoritativo'", () => {
    userRef.current = makeUser({ roleId: "capturador", isAdmin: false });
    render(<DocumentActionsBar document={makeDoc()} />);
    expect(screen.getByRole("button", { name: /descargar/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /marcar autoritativo/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /quitar autoritativo/i })).toBeNull();
  });

  it("Owner (isAdmin=true): ve ambas acciones", () => {
    userRef.current = makeUser({ roleId: "owner", isAdmin: true });
    render(<DocumentActionsBar document={makeDoc()} />);
    expect(screen.getByRole("button", { name: /descargar/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /marcar autoritativo/i }),
    ).toBeInTheDocument();
  });

  it("GK Lead (isAdmin=true) en doc autoritativo: muestra 'Quitar autoritativo'", () => {
    userRef.current = makeUser({ roleId: "gklead", isAdmin: true });
    render(<DocumentActionsBar document={makeDoc({ autoritativo: true })} />);
    expect(
      screen.getByRole("button", { name: /quitar.*autoritativo/i }),
    ).toBeInTheDocument();
  });

  it("Sin sesión (user=null): no muestra acciones admin", () => {
    userRef.current = null;
    render(<DocumentActionsBar document={makeDoc()} />);
    expect(screen.queryByRole("button", { name: /marcar autoritativo/i })).toBeNull();
  });

  it("Descargar dispara onDownload", () => {
    userRef.current = makeUser({ isAdmin: false });
    const onDownload = vi.fn();
    render(<DocumentActionsBar document={makeDoc()} onDownload={onDownload} />);
    fireEvent.click(screen.getByRole("button", { name: /descargar/i }));
    expect(onDownload).toHaveBeenCalledOnce();
  });

  it("Toggle autoritativo dispara onToggleAuthoritative con el next state correcto", () => {
    userRef.current = makeUser({ isAdmin: true });
    const onToggle = vi.fn();
    const { rerender } = render(
      <DocumentActionsBar
        document={makeDoc({ autoritativo: false })}
        onToggleAuthoritative={onToggle}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /marcar autoritativo/i }));
    expect(onToggle).toHaveBeenLastCalledWith(true);

    rerender(
      <DocumentActionsBar
        document={makeDoc({ autoritativo: true })}
        onToggleAuthoritative={onToggle}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /quitar.*autoritativo/i }));
    expect(onToggle).toHaveBeenLastCalledWith(false);
  });
});
