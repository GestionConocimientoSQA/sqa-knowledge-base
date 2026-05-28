import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { IngestionStatusBadge } from "@/components/ingestion/status-badge";
import type { IngestionStatus } from "@/types/domain";

const CASES: Array<{ status: IngestionStatus; expectedText: RegExp }> = [
  { status: "pendiente-metadata", expectedText: /pendiente metadata/i },
  { status: "listo", expectedText: /listo para revisar/i },
  { status: "en-revision", expectedText: /en revisión/i },
  { status: "aprobado", expectedText: /aprobado/i },
  { status: "indexado", expectedText: /indexado/i },
  { status: "rechazado", expectedText: /rechazado/i },
];

describe("IngestionStatusBadge", () => {
  it.each(CASES)(
    "renderiza label legible para status=$status",
    ({ status, expectedText }) => {
      render(<IngestionStatusBadge status={status} />);
      expect(screen.getByText(expectedText)).toBeInTheDocument();
    },
  );

  it("expone data-status para selectors de test", () => {
    const { container } = render(<IngestionStatusBadge status="aprobado" />);
    expect(container.querySelector('[data-status="aprobado"]')).not.toBeNull();
  });
});
