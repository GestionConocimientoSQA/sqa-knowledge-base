import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { FilterBar } from "@/components/explorer/filter-bar";
import type { DocumentSearchFilters } from "@/types/domain";

function setup(overrides: {
  filters?: DocumentSearchFilters;
  sortBy?: undefined | "date_desc" | "score_desc" | "citations_desc" | "relevance";
  activeFilterCount?: number;
} = {}) {
  const onPatchFilters = vi.fn();
  const onSortChange = vi.fn();
  const onClear = vi.fn();
  render(
    <FilterBar
      filters={overrides.filters ?? {}}
      sortBy={overrides.sortBy}
      activeFilterCount={overrides.activeFilterCount ?? 0}
      onPatchFilters={onPatchFilters}
      onSortChange={onSortChange}
      onClear={onClear}
    />,
  );
  return { onPatchFilters, onSortChange, onClear };
}

describe("FilterBar", () => {
  it("renderiza las 8 carpetas como chips con aria-pressed correcto", () => {
    setup({ filters: { carpetas: ["TEC"] } });
    const tec = screen.getByRole("button", { name: /carpeta Técnico/i });
    expect(tec.getAttribute("aria-pressed")).toBe("true");
    const arq = screen.getByRole("button", { name: /carpeta Arquitectura/i });
    expect(arq.getAttribute("aria-pressed")).toBe("false");
  });

  it("toggle de carpeta llama onPatchFilters con la nueva lista", () => {
    const { onPatchFilters } = setup({ filters: { carpetas: ["TEC"] } });
    fireEvent.click(screen.getByRole("button", { name: /carpeta Arquitectura/i }));
    expect(onPatchFilters).toHaveBeenCalledWith({ carpetas: ["TEC", "ARQ"] });
  });

  it("toggle quita la carpeta cuando ya estaba activa", () => {
    const { onPatchFilters } = setup({ filters: { carpetas: ["TEC", "ARQ"] } });
    fireEvent.click(screen.getByRole("button", { name: /carpeta Técnico/i }));
    expect(onPatchFilters).toHaveBeenCalledWith({ carpetas: ["ARQ"] });
  });

  it("muestra contador + botón Limpiar cuando hay filtros activos", () => {
    const { onClear } = setup({ activeFilterCount: 3 });
    expect(screen.getByText(/3 filtros activos/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /limpiar todos los filtros/i }));
    expect(onClear).toHaveBeenCalledOnce();
  });

  it("oculta el contador y botón Limpiar cuando no hay filtros activos", () => {
    setup({ activeFilterCount: 0 });
    expect(screen.queryByText(/filtros? activos?/i)).toBeNull();
    expect(screen.queryByRole("button", { name: /limpiar todos los filtros/i })).toBeNull();
  });

  it("tri-state autoritativo: 'Todos' → 'Sí' → 'No'", () => {
    const { onPatchFilters } = setup();
    const autoGroup = screen.getByRole("radiogroup", { name: /^autoritativo$/i });
    fireEvent.click(within(autoGroup).getByRole("button", { name: "Sí" }));
    expect(onPatchFilters).toHaveBeenLastCalledWith({ autoritativo: true });
    fireEvent.click(within(autoGroup).getByRole("button", { name: "No" }));
    expect(onPatchFilters).toHaveBeenLastCalledWith({ autoritativo: false });
    fireEvent.click(within(autoGroup).getByRole("button", { name: "Todos" }));
    expect(onPatchFilters).toHaveBeenLastCalledWith({ autoritativo: undefined });
  });

  it("score slider con valor 1.0 envía undefined (sin filtrar)", () => {
    const { onPatchFilters } = setup({ filters: { minScore: 3.0 } });
    const slider = screen.getByLabelText(/score mínimo/i) as HTMLInputElement;
    fireEvent.change(slider, { target: { value: "1" } });
    expect(onPatchFilters).toHaveBeenCalledWith({ minScore: undefined });
  });

  it("score slider con valor > 1.0 envía el número", () => {
    const { onPatchFilters } = setup();
    const slider = screen.getByLabelText(/score mínimo/i) as HTMLInputElement;
    fireEvent.change(slider, { target: { value: "4.2" } });
    expect(onPatchFilters).toHaveBeenCalledWith({ minScore: 4.2 });
  });

  it("sort selector dispara onSortChange con el valor elegido", () => {
    const { onSortChange } = setup();
    const select = screen.getByLabelText(/ordenar por/i) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "score_desc" } });
    expect(onSortChange).toHaveBeenCalledWith("score_desc");
  });

  it("sort 'Por defecto' (value='') dispara undefined", () => {
    const { onSortChange } = setup({ sortBy: "score_desc" });
    const select = screen.getByLabelText(/ordenar por/i);
    fireEvent.change(select, { target: { value: "" } });
    expect(onSortChange).toHaveBeenCalledWith(undefined);
  });
});
