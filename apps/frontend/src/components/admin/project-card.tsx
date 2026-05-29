"use client";

/**
 * Card de un proyecto en el listado de admin (Fase 9.6).
 *
 * Click → navega al detalle. Marca visualmente el proyecto raíz
 * `gk-general` para diferenciarlo de los proyectos de clientes.
 */
import Link from "next/link";
import { Archive, FolderKanban, Star } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Project } from "@/types/domain";

const GK_GENERAL_SLUG = "gk-general";

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("es-AR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function ProjectCard({ project }: { project: Project }) {
  const isRoot = project.slug === GK_GENERAL_SLUG;
  const isArchived = project.archivedAt !== null;
  return (
    <Link
      href={`/admin/projects/${project.id}` as never}
      className={cn(
        "block rounded-lg border border-border bg-card p-4 transition-colors hover:border-brand",
        isArchived && "opacity-60",
      )}
      data-testid={`project-card-${project.slug}`}
    >
      <div className="flex items-start gap-3">
        <FolderKanban
          className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground"
          aria-hidden
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate font-display font-bold">{project.name}</h3>
            {isRoot && (
              <Badge variant="authoritative" aria-label="Proyecto raíz">
                <Star className="h-3 w-3" aria-hidden />
                Raíz
              </Badge>
            )}
            {isArchived && (
              <Badge variant="secondary">
                <Archive className="h-3 w-3" aria-hidden />
                Archivado
              </Badge>
            )}
          </div>
          <p className="mt-1 text-xs font-mono text-muted-foreground">
            {project.slug}
          </p>
          {project.description && (
            <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">
              {project.description}
            </p>
          )}
          <p className="mt-2 text-xs text-muted-foreground">
            Creado {formatDate(project.createdAt)}
          </p>
        </div>
      </div>
    </Link>
  );
}
