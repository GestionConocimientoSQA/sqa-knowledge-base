import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProjectCard } from "@/components/admin/project-card";
import type { Project } from "@/types/domain";

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: "p1",
    slug: "cliente-x",
    name: "Cliente X",
    description: "Cliente de prueba",
    ownerOid: "oid-owner",
    createdAt: "2026-05-29T10:00:00.000Z",
    archivedAt: null,
    ...overrides,
  };
}

describe("ProjectCard", () => {
  it("renderiza nombre, slug y descripción", () => {
    render(<ProjectCard project={makeProject()} />);
    expect(screen.getByText("Cliente X")).toBeInTheDocument();
    expect(screen.getByText("cliente-x")).toBeInTheDocument();
    expect(screen.getByText("Cliente de prueba")).toBeInTheDocument();
  });

  it("muestra badge 'Raíz' si el slug es gk-general", () => {
    render(<ProjectCard project={makeProject({ slug: "gk-general" })} />);
    expect(screen.getByLabelText("Proyecto raíz")).toBeInTheDocument();
  });

  it("muestra badge 'Archivado' y opacity reducida si archivedAt está set", () => {
    render(
      <ProjectCard
        project={makeProject({ archivedAt: "2026-06-01T00:00:00.000Z" })}
      />,
    );
    expect(screen.getByText(/Archivado/)).toBeInTheDocument();
  });

  it("el link apunta a /admin/projects/{id}", () => {
    render(<ProjectCard project={makeProject({ id: "abc" })} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/admin/projects/abc");
  });
});
