import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { RecentActivityFeed } from "@/components/dashboard/recent-activity-feed";
import type { RecentActivityItem } from "@/types/domain";

function makeItem(
  partial: Partial<RecentActivityItem> & Pick<RecentActivityItem, "id" | "type">,
): RecentActivityItem {
  return {
    actor: { oid: "oid-x", name: "Test User" },
    at: "2026-05-19T12:00:00.000Z",
    summary: "Acción de prueba",
    ...partial,
  };
}

describe("RecentActivityFeed", () => {
  it("loading: renderiza skeletons", () => {
    render(<RecentActivityFeed items={undefined} isLoading />);
    expect(
      screen.getByLabelText(/cargando actividad reciente/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("vacío: muestra empty state", () => {
    render(<RecentActivityFeed items={[]} />);
    expect(screen.getByText(/sin actividad/i)).toBeInTheDocument();
  });

  it("renderiza items con summary y actor", () => {
    render(
      <RecentActivityFeed
        items={[
          makeItem({
            id: "1",
            type: "captura",
            summary: "Capturó MTEC sobre flakiness",
          }),
        ]}
      />,
    );
    const list = screen.getByRole("list", { name: /1 eventos recientes/i });
    expect(list).toBeInTheDocument();
    expect(screen.getByText("Capturó MTEC sobre flakiness")).toBeInTheDocument();
    expect(screen.getByText("Test User")).toBeInTheDocument();
  });

  it("envuelve en Link cuando hay refUrl, no cuando no", () => {
    render(
      <RecentActivityFeed
        items={[
          makeItem({ id: "1", type: "captura", refUrl: "/explorer/abc" }),
          makeItem({ id: "2", type: "consulta" }),
        ]}
      />,
    );
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(1);
    expect(links[0]!.getAttribute("href")).toBe("/explorer/abc");
  });

  it("usa el label correcto por tipo", () => {
    render(
      <RecentActivityFeed
        items={[
          makeItem({ id: "1", type: "captura" }),
          makeItem({ id: "2", type: "ingesta" }),
          makeItem({ id: "3", type: "consulta" }),
          makeItem({ id: "4", type: "taxonomia" }),
        ]}
      />,
    );
    // Los labels viven con primera mayúscula en el DOM y se uppercasean
    // por CSS (`uppercase`); buscamos por el texto literal.
    expect(screen.getByText("Captura")).toBeInTheDocument();
    expect(screen.getByText("Ingesta")).toBeInTheDocument();
    expect(screen.getByText("Consulta")).toBeInTheDocument();
    expect(screen.getByText("Taxonomía")).toBeInTheDocument();
  });

  it("renderiza el datetime ISO en atributo <time>", () => {
    const { container } = render(
      <RecentActivityFeed
        items={[
          makeItem({
            id: "1",
            type: "captura",
            at: "2026-05-19T12:00:00.000Z",
          }),
        ]}
      />,
    );
    const time = container.querySelector("time");
    expect(time?.getAttribute("datetime")).toBe("2026-05-19T12:00:00.000Z");
  });
});
