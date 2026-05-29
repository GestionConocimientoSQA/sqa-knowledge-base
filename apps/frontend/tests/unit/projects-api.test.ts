import { beforeEach, describe, expect, it } from "vitest";

import {
  __resetProjectsStub,
  addProjectMember,
  archiveProject,
  createProject,
  getProject,
  listProjectMembers,
  listProjects,
  removeProjectMember,
  updateProject,
} from "@/lib/api/projects";

describe("projects API (mock-stub)", () => {
  beforeEach(() => {
    __resetProjectsStub();
  });

  it("lista los proyectos seed (gk-general + cliente-acme)", async () => {
    const list = await listProjects();
    expect(list.length).toBeGreaterThanOrEqual(2);
    const slugs = list.map((p) => p.slug);
    expect(slugs).toContain("gk-general");
    expect(slugs).toContain("cliente-acme");
  });

  it("crea un proyecto nuevo y aparece en la lista", async () => {
    const created = await createProject({
      slug: "cliente-banco-x",
      name: "Banco X",
      description: "Cliente bancario",
      ownerEmail: "owner@banco-x.com",
    });
    expect(created.slug).toBe("cliente-banco-x");
    expect(created.archivedAt).toBeNull();

    const all = await listProjects();
    expect(all.some((p) => p.id === created.id)).toBe(true);
  });

  it("rechaza un slug duplicado", async () => {
    await expect(
      createProject({
        slug: "gk-general",
        name: "X",
        description: "",
        ownerEmail: "x@y.com",
      }),
    ).rejects.toThrow(/ya está en uso/);
  });

  it("update modifica name/description sin tocar slug si no se manda", async () => {
    const projects = await listProjects();
    const acme = projects.find((p) => p.slug === "cliente-acme")!;
    const updated = await updateProject(acme.id, { name: "ACME Renamed" });
    expect(updated.name).toBe("ACME Renamed");
    expect(updated.slug).toBe("cliente-acme");
  });

  it("archive setea archivedAt", async () => {
    const projects = await listProjects();
    const acme = projects.find((p) => p.slug === "cliente-acme")!;
    const archived = await archiveProject(acme.id);
    expect(archived.archivedAt).not.toBeNull();
  });

  it("listMembers devuelve la membership inicial del seed", async () => {
    const projects = await listProjects();
    const acme = projects.find((p) => p.slug === "cliente-acme")!;
    const members = await listProjectMembers(acme.id);
    expect(members.length).toBe(1);
    expect(members[0]!.role).toBe("project_owner");
  });

  it("addMember + removeMember se reflejan en listMembers", async () => {
    const projects = await listProjects();
    const acme = projects.find((p) => p.slug === "cliente-acme")!;

    const added = await addProjectMember(acme.id, {
      email: "nuevo@cliente.com",
      role: "member",
    });
    let members = await listProjectMembers(acme.id);
    expect(members.length).toBe(2);

    await removeProjectMember(acme.id, added.userOid);
    members = await listProjectMembers(acme.id);
    expect(members.length).toBe(1);
  });

  it("getProject(id) lanza si no existe", async () => {
    await expect(getProject("no-existe")).rejects.toThrow(/no encontrado/);
  });
});
