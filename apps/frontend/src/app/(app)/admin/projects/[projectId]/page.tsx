"use client";

/**
 * /admin/projects/[projectId] — detalle de proyecto (Fase 9.6).
 *
 * Metadata + miembros. Acceso restringido a GK Lead.
 * En Fase 9.7 el `project_owner` accede a paneles parecidos vía
 * `/projects/[id]/admin/*`, pero aquellos heredan reglas más laxas.
 */
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Archive, ArrowLeft, ChevronRight, Shield } from "lucide-react";
import { toast } from "sonner";

import { MembersPanel } from "@/components/admin/members-panel";
import { EmptyState } from "@/components/shared/empty-state";
import { PageContainer } from "@/components/shared/page-container";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth/auth-provider";
import {
  useArchiveProject,
  useProject,
} from "@/lib/hooks/use-projects";

const GK_GENERAL_SLUG = "gk-general";

export default function ProjectDetailPage() {
  const params = useParams<{ projectId: string }>();
  const router = useRouter();
  const projectId = params?.projectId;
  const { user } = useAuth();
  const { data: project, isLoading, isError, error } = useProject(projectId);
  const archive = useArchiveProject();

  if (!user || user.roleId !== "gklead") {
    return (
      <PageContainer>
        <EmptyState
          icon={Shield}
          title="Acceso restringido"
          description="El detalle de proyectos está disponible solo para GK Lead."
        />
      </PageContainer>
    );
  }

  if (isLoading) {
    return (
      <PageContainer>
        <Skeleton className="mb-3 h-6 w-1/3" />
        <Skeleton className="mb-6 h-10 w-2/3" />
        <Skeleton className="h-48 w-full" />
      </PageContainer>
    );
  }

  if (isError || !project) {
    return (
      <PageContainer>
        <EmptyState
          icon={Shield}
          title="Proyecto no encontrado"
          description={
            error instanceof Error ? error.message : "No pudimos cargarlo."
          }
          action={
            <Button asChild variant="outline">
              <Link href={"/admin/projects" as never}>
                <ArrowLeft className="h-4 w-4" aria-hidden />
                Volver
              </Link>
            </Button>
          }
        />
      </PageContainer>
    );
  }

  const isRoot = project.slug === GK_GENERAL_SLUG;
  const isArchived = project.archivedAt !== null;

  function handleArchive() {
    if (!project) return;
    if (
      !window.confirm(
        `Archivar "${project.name}"? Quedará en modo solo lectura.`,
      )
    ) {
      return;
    }
    archive.mutate(project.id, {
      onSuccess: () => {
        toast.success("Proyecto archivado");
        router.push("/admin/projects" as never);
      },
      onError: (err) => toast.error(err.message),
    });
  }

  return (
    <PageContainer>
      <nav
        aria-label="Migas de pan"
        className="mb-4 flex items-center gap-1 text-sm text-muted-foreground"
      >
        <Link href={"/admin/projects" as never} className="hover:text-foreground">
          Proyectos
        </Link>
        <ChevronRight className="h-4 w-4" aria-hidden />
        <span className="truncate text-foreground">{project.name}</span>
      </nav>

      <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-display text-2xl font-extrabold">
              {project.name}
            </h2>
            {isRoot && <Badge variant="authoritative">Raíz</Badge>}
            {isArchived && <Badge variant="secondary">Archivado</Badge>}
          </div>
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            {project.slug} · {project.id}
          </p>
        </div>
        {!isRoot && !isArchived && (
          <Button
            variant="outline"
            type="button"
            onClick={handleArchive}
            disabled={archive.isPending}
          >
            <Archive className="h-4 w-4" aria-hidden />
            Archivar
          </Button>
        )}
      </header>

      <section
        aria-labelledby="meta-heading"
        className="mb-6 rounded-lg border border-border bg-card p-5"
      >
        <h3 id="meta-heading" className="mb-3 font-display text-base font-bold">
          Metadata
        </h3>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase text-muted-foreground">
              Descripción
            </dt>
            <dd>{project.description || "—"}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-muted-foreground">
              Owner OID
            </dt>
            <dd className="font-mono text-xs">{project.ownerOid}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-muted-foreground">
              Creado
            </dt>
            <dd>{new Date(project.createdAt).toLocaleString("es-AR")}</dd>
          </div>
          {project.archivedAt && (
            <div>
              <dt className="text-xs font-semibold uppercase text-muted-foreground">
                Archivado
              </dt>
              <dd>{new Date(project.archivedAt).toLocaleString("es-AR")}</dd>
            </div>
          )}
        </dl>
      </section>

      <MembersPanel project={project} />
    </PageContainer>
  );
}
