import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DocumentMetaPanel } from "@/components/explorer/document-meta-panel";
import type { DocumentDetail } from "@/types/domain";

function makeDoc(overrides: Partial<DocumentDetail> = {}): DocumentDetail {
  return {
    id: "DOC-1",
    titulo: "Doc",
    carpeta: "TEC",
    tipo: "MTEC",
    autoritativo: false,
    estado: "vigente",
    autor: "Lucía Vargas",
    rol: "Automation Engineer",
    fecha: "2026-04-22",
    revision: "2026-04-22",
    version: "1.2",
    citas: 47,
    score: 4.4,
    anonimizado: false,
    fragmentos: 38,
    paginas: 14,
    formato: "DOCX",
    tags: ["regresión", "flakiness"],
    incomingCitations: [],
    resumen: "",
    ...overrides,
  };
}

describe("DocumentMetaPanel", () => {
  it("muestra autor, rol, versión, fecha y formato", () => {
    render(<DocumentMetaPanel document={makeDoc()} />);
    expect(screen.getByText(/Lucía Vargas · Automation Engineer/)).toBeInTheDocument();
    expect(screen.getByText(/v1\.2/)).toBeInTheDocument();
    // fecha y revision pueden coincidir; basta con que aparezca al menos una vez.
    expect(screen.getAllByText("2026-04-22").length).toBeGreaterThan(0);
    expect(screen.getByText(/DOCX · 14 pág · 38 fragmentos/)).toBeInTheDocument();
  });

  it("muestra score formateado con un decimal y citas recibidas", () => {
    render(<DocumentMetaPanel document={makeDoc({ score: 4.4, citas: 47 })} />);
    expect(screen.getByText(/4\.4 \/ 5 · 47 citas recibidas/)).toBeInTheDocument();
  });

  it("muestra aprobador y fecha de aprobación cuando existen", () => {
    render(
      <DocumentMetaPanel
        document={makeDoc({
          aprobador: "Andrés Altamiranda",
          fechaAprobacion: "2026-04-25",
        })}
      />,
    );
    expect(
      screen.getByText(/Andrés Altamiranda · 2026-04-25/),
    ).toBeInTheDocument();
  });

  it("omite el campo aprobador cuando no está", () => {
    render(<DocumentMetaPanel document={makeDoc({ aprobador: undefined })} />);
    expect(screen.queryByText(/Aprobado por/i)).toBeNull();
  });

  it("renderiza tags como badges", () => {
    render(<DocumentMetaPanel document={makeDoc()} />);
    const tagsList = screen.getByLabelText(/tags del documento/i);
    expect(tagsList).toBeInTheDocument();
    expect(screen.getByText("regresión")).toBeInTheDocument();
    expect(screen.getByText("flakiness")).toBeInTheDocument();
  });

  it("oculta la sección tags cuando no hay ninguno", () => {
    render(<DocumentMetaPanel document={makeDoc({ tags: [] })} />);
    expect(screen.queryByLabelText(/tags del documento/i)).toBeNull();
  });
});
