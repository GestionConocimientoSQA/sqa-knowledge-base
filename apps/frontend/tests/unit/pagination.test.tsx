import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Pagination } from "@/components/explorer/pagination";

describe("Pagination", () => {
  it("muestra el rango de items y el total de páginas", () => {
    render(
      <Pagination page={2} limit={20} total={45} onPageChange={vi.fn()} />,
    );
    expect(screen.getByText(/21/)).toBeInTheDocument();
    expect(screen.getByText(/40/)).toBeInTheDocument();
    expect(screen.getByText(/45/)).toBeInTheDocument();
    expect(screen.getByText(/Página/)).toBeInTheDocument();
  });

  it("Anterior está deshabilitado en página 1", () => {
    render(<Pagination page={1} limit={20} total={45} onPageChange={vi.fn()} />);
    const prev = screen.getByRole("button", { name: /página anterior/i });
    expect((prev as HTMLButtonElement).disabled).toBe(true);
  });

  it("Siguiente está deshabilitado en la última página", () => {
    render(<Pagination page={3} limit={20} total={45} onPageChange={vi.fn()} />);
    const next = screen.getByRole("button", { name: /página siguiente/i });
    expect((next as HTMLButtonElement).disabled).toBe(true);
  });

  it("click en Siguiente avanza una página", () => {
    const onPageChange = vi.fn();
    render(<Pagination page={1} limit={20} total={45} onPageChange={onPageChange} />);
    fireEvent.click(screen.getByRole("button", { name: /página siguiente/i }));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("click en Anterior retrocede una página", () => {
    const onPageChange = vi.fn();
    render(<Pagination page={3} limit={20} total={45} onPageChange={onPageChange} />);
    fireEvent.click(screen.getByRole("button", { name: /página anterior/i }));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("total=0: muestra '0 resultados' y ambos botones deshabilitados", () => {
    render(<Pagination page={1} limit={20} total={0} onPageChange={vi.fn()} />);
    expect(screen.getByText(/0 resultados/i)).toBeInTheDocument();
    expect((screen.getByRole("button", { name: /página anterior/i }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: /página siguiente/i }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("clampa page fuera de rango sin romper", () => {
    render(<Pagination page={999} limit={20} total={45} onPageChange={vi.fn()} />);
    // Debería mostrar página 3 (última válida) y no romper.
    expect(screen.getByText(/Página/)).toBeInTheDocument();
  });
});
