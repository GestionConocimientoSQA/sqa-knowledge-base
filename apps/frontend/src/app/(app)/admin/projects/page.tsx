"use client";

/**
 * /admin/projects — lista de proyectos del KB (Fase 9.6).
 *
 * Solo GK Lead. Cualquier otro rol ve "Acceso restringido".
 */
import { useState } from "react";
import { FolderKanban, Plus, Shield } from "lucide-react";

import { CreateProjectDialog } from "@/components/admin/create-project-dialog";
import { ProjectCard } from "@/components/admin/project-card";
import { EmptyState } from "@/components/shared/empty-state";
import { PageContainer } from "@/components/shared/page-container";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth/auth-provider";
import { useProjects } from "@/lib/hooks/use-projects";

export default function AdminProjectsPage() {
  const { user } = useAuth();
  const { data, isLoading, isError, error } = useProjects();
  const [dialogOpen, setDialogOpen] = useState(false);

  if (!user || user.roleId !== "gklead") {
    return (
      <PageContainer>
        <EmptyState
          icon={Shield}
          title="Acceso restringido"
          description="La administración de proyectos está disponible solo para GK Lead."
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="eyebrow">Multi-tenant</div>
          <h2 className="font-display text-2xl font-extrabold">Proyectos</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Cada proyecto tiene su propio knowledge aislado. Designá un
            `project_owner` por email al crear el proyecto.
          </p>
        </div>
        <Button onClick={() => setDialogOpen(true)} type="button">
          <Plus className="h-4 w-4" aria-hidden />
          Nuevo proyecto
        </Button>
      </header>

      {isLoading && (
        <div className="grid gap-3 lg:grid-cols-2" aria-busy="true">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      )}

      {isError && (
        <EmptyState
          icon={FolderKanban}
          title="No se pudo cargar la lista"
          description={
            error instanceof Error ? error.message : "Error desconocido."
          }
        />
      )}

      {!isLoading && !isError && (data?.length ?? 0) === 0 && (
        <EmptyState
          icon={FolderKanban}
          title="Sin proyectos"
          description="Creá el primer proyecto del KB para arrancar."
          action={
            <Button onClick={() => setDialogOpen(true)} type="button">
              <Plus className="h-4 w-4" aria-hidden />
              Nuevo proyecto
            </Button>
          }
        />
      )}

      {!isLoading && !isError && (data?.length ?? 0) > 0 && (
        <ul
          aria-label="Lista de proyectos"
          data-testid="projects-list"
          className="grid gap-3 lg:grid-cols-2"
        >
          {data!.map((p) => (
            <li key={p.id}>
              <ProjectCard project={p} />
            </li>
          ))}
        </ul>
      )}

      <CreateProjectDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
      />
    </PageContainer>
  );
}
