import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MyCapturesSummary } from "@/components/dashboard/my-captures-summary";
import type { MyCapturesStats } from "@/types/domain";

const FULL_STATS: MyCapturesStats = {
  totalCaptures: 5,
  totalCitationsReceived: 42,
  avgScore: 4.12,
  lastCapturedAt: "2026-05-19",
};

describe("MyCapturesSummary", () => {
  it("loading: renderiza 4 skeletons", () => {
    const { container } = render(
      <MyCapturesSummary stats={undefined} isLoading />,
    );
    // Cuatro placeholders en grid (no se usa label específico).
    const grid = container.querySelector(".grid");
    expect(grid?.children.length).toBe(4);
  });

  it("stats undefined sin loading: no renderiza nada", () => {
    const { container } = render(
      <MyCapturesSummary stats={undefined} isLoading={false} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("totalCaptures=0: muestra CTA a /chat?mode=captura", () => {
    render(
      <MyCapturesSummary
        stats={{
          totalCaptures: 0,
          totalCitationsReceived: 0,
          avgScore: 0,
          lastCapturedAt: null,
        }}
      />,
    );
    expect(screen.getByText(/aún no tenés capturas/i)).toBeInTheDocument();
    const cta = screen.getByRole("link", { name: /iniciar captura/i });
    expect(cta.getAttribute("href")).toBe("/chat?mode=captura");
  });

  it("stats con datos: muestra los 4 StatCards y link a /my-captures", () => {
    render(<MyCapturesSummary stats={FULL_STATS} />);
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("4.12")).toBeInTheDocument();
    expect(screen.getByText("2026-05-19")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /ver todas mis capturas/i });
    expect(link.getAttribute("href")).toBe("/my-captures");
  });

  it("lastCapturedAt=null: muestra placeholder '—'", () => {
    render(
      <MyCapturesSummary
        stats={{ ...FULL_STATS, lastCapturedAt: null }}
      />,
    );
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
