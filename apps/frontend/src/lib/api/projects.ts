/**
 * API de proyectos multi-tenant — Fase 9.6.
 *
 * Consume los endpoints `/projects` del backend (Fase 9.2). Mismo patrón
 * DIP que `documents.ts` / `ingestion.ts`: con `NEXT_PUBLIC_API_URL`
 * seteada hace HTTP real; sin ella cae a un mock-stub en memoria.
 *
 * El stub mantiene proyectos + memberships mutables — las acciones
 * (create / addMember / removeMember) se reflejen entre llamadas dentro
 * de la misma sesión.
 */
import { api, USE_REAL_API } from "@/lib/api/client";
import type {
  Project,
  ProjectMember,
  ProjectMemberRole,
} from "@/types/domain";

const STUB_DELAY_MS = 150;

function delay<T>(value: T, ms = STUB_DELAY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

// ===========================================================================
// Mock-stub
// ===========================================================================

const GK_GENERAL_ID = "00000000-0000-0000-0000-000000000001";

const SEED_PROJECTS: Project[] = [
  {
    id: GK_GENERAL_ID,
    slug: "gk-general",
    name: "GK General",
    description:
      "Proyecto raíz de GK — conocimiento transversal a toda la organización.",
    ownerOid: "stub-gklead-00000000",
    createdAt: "2026-05-28T00:00:00.000Z",
    archivedAt: null,
  },
  {
    id: "11111111-1111-1111-1111-111111111111",
    slug: "cliente-acme",
    name: "Cliente ACME",
    description: "Cliente de banca digital — proyecto piloto.",
    ownerOid: "stub-owner-00000000",
    createdAt: "2026-05-29T10:00:00.000Z",
    archivedAt: null,
  },
];

const SEED_MEMBERS: ProjectMember[] = [
  {
    projectId: GK_GENERAL_ID,
    userOid: "stub-gklead-00000000",
    role: "project_owner",
    addedAt: "2026-05-28T00:00:00.000Z",
  },
  {
    projectId: GK_GENERAL_ID,
    userOid: "stub-owner-00000000",
    role: "member",
    addedAt: "2026-05-28T00:00:00.000Z",
  },
  {
    projectId: "11111111-1111-1111-1111-111111111111",
    userOid: "stub-owner-00000000",
    role: "project_owner",
    addedAt: "2026-05-29T10:00:00.000Z",
  },
];

let stubProjects: Project[] = SEED_PROJECTS.map((p) => ({ ...p }));
let stubMembers: ProjectMember[] = SEED_MEMBERS.map((m) => ({ ...m }));

/** Resetea el estado del stub (para tests). */
export function __resetProjectsStub(): void {
  stubProjects = SEED_PROJECTS.map((p) => ({ ...p }));
  stubMembers = SEED_MEMBERS.map((m) => ({ ...m }));
}

function fakeUuid(): string {
  return "stub-" + Math.random().toString(36).slice(2, 12);
}

// ===========================================================================
// Projects
// ===========================================================================

export async function listProjects(): Promise<Project[]> {
  if (USE_REAL_API) {
    return api.get("projects").json<Project[]>();
  }
  return delay(stubProjects.map((p) => ({ ...p })));
}

export async function getProject(projectId: string): Promise<Project> {
  if (USE_REAL_API) {
    return api.get(`projects/${projectId}`).json<Project>();
  }
  const found = stubProjects.find((p) => p.id === projectId);
  if (!found) throw new Error(`Proyecto ${projectId} no encontrado (stub)`);
  return delay({ ...found });
}

export interface CreateProjectInput {
  slug: string;
  name: string;
  description: string;
  ownerEmail: string;
}

export async function createProject(
  input: CreateProjectInput,
): Promise<Project> {
  if (USE_REAL_API) {
    return api.post("projects", { json: input }).json<Project>();
  }
  if (stubProjects.some((p) => p.slug === input.slug)) {
    throw new Error(`El slug "${input.slug}" ya está en uso`);
  }
  // Mock: asume el email corresponde al owner stub.
  const project: Project = {
    id: fakeUuid(),
    slug: input.slug,
    name: input.name,
    description: input.description,
    ownerOid: "stub-owner-00000000",
    createdAt: new Date().toISOString(),
    archivedAt: null,
  };
  stubProjects = [project, ...stubProjects];
  stubMembers = [
    ...stubMembers,
    {
      projectId: project.id,
      userOid: "stub-owner-00000000",
      role: "project_owner",
      addedAt: project.createdAt,
    },
  ];
  return delay({ ...project });
}

export interface UpdateProjectInput {
  slug?: string;
  name?: string;
  description?: string;
}

export async function updateProject(
  projectId: string,
  input: UpdateProjectInput,
): Promise<Project> {
  if (USE_REAL_API) {
    return api.put(`projects/${projectId}`, { json: input }).json<Project>();
  }
  let updated: Project | undefined;
  stubProjects = stubProjects.map((p) => {
    if (p.id !== projectId) return p;
    updated = {
      ...p,
      slug: input.slug ?? p.slug,
      name: input.name ?? p.name,
      description: input.description ?? p.description,
    };
    return updated;
  });
  if (!updated) throw new Error(`Proyecto ${projectId} no encontrado (stub)`);
  return delay({ ...updated });
}

export async function archiveProject(projectId: string): Promise<Project> {
  if (USE_REAL_API) {
    return api.delete(`projects/${projectId}`).json<Project>();
  }
  let archived: Project | undefined;
  stubProjects = stubProjects.map((p) => {
    if (p.id !== projectId) return p;
    archived = { ...p, archivedAt: new Date().toISOString() };
    return archived;
  });
  if (!archived) throw new Error(`Proyecto ${projectId} no encontrado (stub)`);
  return delay({ ...archived });
}

// ===========================================================================
// Members
// ===========================================================================

export async function listProjectMembers(
  projectId: string,
): Promise<ProjectMember[]> {
  if (USE_REAL_API) {
    return api.get(`projects/${projectId}/members`).json<ProjectMember[]>();
  }
  return delay(
    stubMembers
      .filter((m) => m.projectId === projectId)
      .map((m) => ({ ...m })),
  );
}

export interface AddMemberInput {
  email: string;
  role: ProjectMemberRole;
}

export async function addProjectMember(
  projectId: string,
  input: AddMemberInput,
): Promise<ProjectMember> {
  if (USE_REAL_API) {
    return api
      .post(`projects/${projectId}/members`, { json: input })
      .json<ProjectMember>();
  }
  // Mock: deriva un oid del email.
  const userOid = `stub-${input.email.split("@")[0]}-${Math.random()
    .toString(36)
    .slice(2, 6)}`;
  const existing = stubMembers.find(
    (m) => m.projectId === projectId && m.userOid === userOid,
  );
  const member: ProjectMember = existing
    ? { ...existing, role: input.role }
    : {
        projectId,
        userOid,
        role: input.role,
        addedAt: new Date().toISOString(),
      };
  stubMembers = [
    ...stubMembers.filter(
      (m) => !(m.projectId === projectId && m.userOid === userOid),
    ),
    member,
  ];
  return delay({ ...member });
}

export async function removeProjectMember(
  projectId: string,
  userOid: string,
): Promise<void> {
  if (USE_REAL_API) {
    await api.delete(`projects/${projectId}/members/${userOid}`);
    return;
  }
  stubMembers = stubMembers.filter(
    (m) => !(m.projectId === projectId && m.userOid === userOid),
  );
  await delay(undefined);
}
