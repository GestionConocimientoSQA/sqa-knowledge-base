import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { IncomingCitationsPanel } from "@/components/explorer/incoming-citations-panel";
import type { IncomingCitation } from "@/types/domain";

function makeCitation(overrides: Partial<IncomingCitation> = {}): IncomingCitation {
  return {
    sourceDocId: "TEC-foo-2026-01-01",
    sourceTitle: "Doc origen de prueba",
    sourceFolder: "TEC",
    section: "§3",
    snippet: "Snippet citado del documento origen…",
    citedAt: "2026-01-15",
    ...overrides,
  };
}

describe("IncomingCitationsPanel", () => {
  it("lista vacía: muestra empty state, no list", () => {
    render(<IncomingCitationsPanel citations={[]} />);
    expect(screen.getByText(/sin citaciones recibidas/i)).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("renderiza una citación con título, snippet y link al origen", () => {
    render(<IncomingCitationsPanel citations={[makeCitation()]} />);
    expect(screen.getByText("Doc origen de prueba")).toBeInTheDocument();
    expect(screen.getByText(/snippet citado/i)).toBeInTheDocument();
    expect(screen.getByText("§3")).toBeInTheDocument();
    const link = screen.getByRole("link");
    expect(link.getAttribute("href")).toBe("/explorer/TEC-foo-2026-01-01");
  });

  it("renderiza múltiples citaciones con badge del total", () => {
    render(
      <IncomingCitationsPanel
        citations={[
          makeCitation({ sourceDocId: "a", section: "§1" }),
          makeCitation({ sourceDocId: "b", section: "§2" }),
          makeCitation({ sourceDocId: "c", section: "§3" }),
        ]}
      />,
    );
    const list = screen.getByRole("list", { name: /3 citaciones recibidas/i });
    expect(list).toBeInTheDocument();
    expect(list.querySelectorAll("li")).toHaveLength(3);
  });
});
