import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { SearchInput } from "@/components/explorer/search-input";

describe("SearchInput", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("muestra el valor inicial y no dispara onDebouncedChange al montar", () => {
    const onChange = vi.fn();
    render(<SearchInput value="inicial" onDebouncedChange={onChange} />);
    const input = screen.getByLabelText("Buscar documentos") as HTMLInputElement;
    expect(input.value).toBe("inicial");
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("emite onDebouncedChange después de que el valor escrito se estabiliza", () => {
    const onChange = vi.fn();
    render(<SearchInput value="" onDebouncedChange={onChange} debounceMs={300} />);
    const input = screen.getByLabelText("Buscar documentos");
    fireEvent.change(input, { target: { value: "play" } });
    act(() => {
      vi.advanceTimersByTime(299);
    });
    expect(onChange).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(onChange).toHaveBeenCalledWith("play");
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it("rapid typing solo emite el valor final", () => {
    const onChange = vi.fn();
    render(<SearchInput value="" onDebouncedChange={onChange} debounceMs={300} />);
    const input = screen.getByLabelText("Buscar documentos");
    fireEvent.change(input, { target: { value: "p" } });
    act(() => vi.advanceTimersByTime(100));
    fireEvent.change(input, { target: { value: "pl" } });
    act(() => vi.advanceTimersByTime(100));
    fireEvent.change(input, { target: { value: "play" } });
    act(() => vi.advanceTimersByTime(300));
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenLastCalledWith("play");
  });

  it("clear button limpia el input y emite '' al padre", () => {
    const onChange = vi.fn();
    render(<SearchInput value="hola" onDebouncedChange={onChange} debounceMs={200} />);
    const clear = screen.getByLabelText("Limpiar búsqueda");
    fireEvent.click(clear);
    act(() => vi.advanceTimersByTime(200));
    expect(onChange).toHaveBeenCalledWith("");
  });

  it("clear button no aparece cuando el input está vacío", () => {
    render(<SearchInput value="" onDebouncedChange={vi.fn()} />);
    expect(screen.queryByLabelText("Limpiar búsqueda")).toBeNull();
  });

  it("sincroniza con cambios externos del prop value sin re-emitir", () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <SearchInput value="abc" onDebouncedChange={onChange} debounceMs={200} />,
    );
    rerender(<SearchInput value="def" onDebouncedChange={onChange} debounceMs={200} />);
    const input = screen.getByLabelText("Buscar documentos") as HTMLInputElement;
    expect(input.value).toBe("def");
    act(() => vi.advanceTimersByTime(500));
    expect(onChange).not.toHaveBeenCalled();
  });
});
