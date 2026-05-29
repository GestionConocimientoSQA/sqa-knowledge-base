/**
 * Hooks TanStack Query para proyectos multi-tenant (Fase 9.6).
 *
 * Encapsula el contrato `lib/api/projects` detrás de React Query.
 * Las mutaciones invalidan automáticamente las queries afectadas.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import {
  addProjectMember,
  archiveProject,
  createProject,
  getProject,
  listProjectMembers,
  listProjects,
  removeProjectMember,
  updateProject,
  type AddMemberInput,
  type CreateProjectInput,
  type UpdateProjectInput,
} from "@/lib/api/projects";
import type { Project, ProjectMember } from "@/types/domain";

const PROJECTS_KEY = ["projects"] as const;

// ===========================================================================
// Queries
// ===========================================================================

export function useProjects(): UseQueryResult<Project[]> {
  return useQuery({
    queryKey: [...PROJECTS_KEY, "list"],
    queryFn: listProjects,
    staleTime: 30_000,
  });
}

export function useProject(
  projectId: string | null | undefined,
): UseQueryResult<Project> {
  return useQuery({
    queryKey: [...PROJECTS_KEY, "item", projectId],
    queryFn: () => getProject(projectId as string),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });
}

export function useProjectMembers(
  projectId: string | null | undefined,
): UseQueryResult<ProjectMember[]> {
  return useQuery({
    queryKey: [...PROJECTS_KEY, "members", projectId],
    queryFn: () => listProjectMembers(projectId as string),
    enabled: Boolean(projectId),
    staleTime: 10_000,
  });
}

// ===========================================================================
// Mutations
// ===========================================================================

function useInvalidateAll() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: PROJECTS_KEY });
}

export function useCreateProject(): UseMutationResult<
  Project,
  Error,
  CreateProjectInput
> {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      void invalidate();
    },
  });
}

export interface UpdateArgs {
  projectId: string;
  input: UpdateProjectInput;
}

export function useUpdateProject(): UseMutationResult<
  Project,
  Error,
  UpdateArgs
> {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: ({ projectId, input }: UpdateArgs) =>
      updateProject(projectId, input),
    onSuccess: () => {
      void invalidate();
    },
  });
}

export function useArchiveProject(): UseMutationResult<Project, Error, string> {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (projectId: string) => archiveProject(projectId),
    onSuccess: () => {
      void invalidate();
    },
  });
}

export interface AddMemberArgs {
  projectId: string;
  input: AddMemberInput;
}

export function useAddProjectMember(): UseMutationResult<
  ProjectMember,
  Error,
  AddMemberArgs
> {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: ({ projectId, input }: AddMemberArgs) =>
      addProjectMember(projectId, input),
    onSuccess: () => {
      void invalidate();
    },
  });
}

export interface RemoveMemberArgs {
  projectId: string;
  userOid: string;
}

export function useRemoveProjectMember(): UseMutationResult<
  void,
  Error,
  RemoveMemberArgs
> {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: ({ projectId, userOid }: RemoveMemberArgs) =>
      removeProjectMember(projectId, userOid),
    onSuccess: () => {
      void invalidate();
    },
  });
}
