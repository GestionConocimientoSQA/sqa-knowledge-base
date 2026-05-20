import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { HotTopicsPanel } from "@/components/dashboard/hot-topics-panel";
import type { HotTopic } from "@/types/domain";

const topics: HotTopic[] = [
  { topic: "Flakiness en CI", queries30d: 87, citationCount: 14, isGap: false },
  { topic: "Performance k6", queries30d: 52, citationCount: 4, isGap: true },
];

describe("HotTopicsPanel", () => {
  it("loading: renderiza skeletons en lugar de la lista", () => {
    render(<HotTopicsPanel topics={undefined} isLoading />);
    expect(
      screen.getByLabelText(/cargando temas en demanda/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("vacío: muestra empty state", () => {
    render(<HotTopicsPanel topics={[]} />);
    expect(screen.getByText(/sin actividad reciente/i)).toBeInTheDocument();
  });

  it("renderiza topics con queries y citaciones", () => {
    render(<HotTopicsPanel topics={topics} />);
    const list = screen.getByRole("list", { name: /2 temas en demanda/i });
    expect(list).toBeInTheDocument();
    const rows = within(list).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    expect(within(rows[0]!).getByText("Flakiness en CI")).toBeInTheDocument();
    expect(within(rows[0]!).getByText(/87/)).toBeInTheDocument();
    expect(within(rows[0]!).getByText(/14/)).toBeInTheDocument();
  });

  it("badge 'Gap' aparece sólo en topics con isGap=true", () => {
    render(<HotTopicsPanel topics={topics} />);
    const rows = screen.getAllByRole("listitem");
    expect(within(rows[0]!).queryByText(/^Gap$/)).toBeNull();
    expect(within(rows[1]!).getByText(/^Gap$/)).toBeInTheDocument();
  });
});
