"use client";

/**
 * Panel de gestión de miembros de un proyecto (Fase 9.6).
 *
 * Lista miembros + form para añadir por email + acción de quitar.
 * Restricción: no se puede quitar al owner del proyecto (la regla la
 * valida también el backend; acá solo deshabilitamos el botón).
 */
import { useState, type FormEvent } from "react";
import { Crown, Trash2, UserPlus } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useAddProjectMember,
  useProjectMembers,
  useRemoveProjectMember,
} from "@/lib/hooks/use-projects";
import type { Project, ProjectMemberRole } from "@/types/domain";

export function MembersPanel({ project }: { project: Project }) {
  const { data, isLoading } = useProjectMembers(project.id);
  const add = useAddProjectMember();
  const remove = useRemoveProjectMember();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<ProjectMemberRole>("member");

  function handleAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.includes("@")) {
      toast.error("Email inválido");
      return;
    }
    add.mutate(
      { projectId: project.id, input: { email: email.trim(), role } },
      {
        onSuccess: () => {
          setEmail("");
          toast.success("Miembro añadido");
        },
        onError: (err) => toast.error(err.message),
      },
    );
  }

  function handleRemove(userOid: string) {
    if (userOid === project.ownerOid) {
      toast.error(
        "No se puede quitar al owner. Transferí la propiedad primero.",
      );
      return;
    }
    if (!window.confirm("¿Quitar este miembro del proyecto?")) return;
    remove.mutate(
      { projectId: project.id, userOid },
      {
        onSuccess: () => toast.success("Miembro removido"),
        onError: (err) => toast.error(err.message),
      },
    );
  }

  return (
    <section
      aria-labelledby="members-heading"
      className="rounded-lg border border-border bg-card p-5"
    >
      <h3
        id="members-heading"
        className="mb-4 font-display text-base font-bold"
      >
        Miembros
      </h3>

      <form onSubmit={handleAdd} className="mb-6 grid gap-3 sm:grid-cols-[1fr_auto_auto]">
        <div className="space-y-1.5">
          <Label htmlFor="member-email" className="sr-only">
            Email del nuevo miembro
          </Label>
          <Input
            id="member-email"
            type="email"
            placeholder="usuario@cliente.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="member-role" className="sr-only">
            Rol del nuevo miembro
          </Label>
          <select
            id="member-role"
            value={role}
            onChange={(e) => setRole(e.target.value as ProjectMemberRole)}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="member">Miembro</option>
            <option value="project_owner">Project owner</option>
          </select>
        </div>
        <Button type="submit" disabled={add.isPending}>
          <UserPlus className="h-4 w-4" aria-hidden />
          Añadir
        </Button>
      </form>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : (
        <ul aria-label="Lista de miembros" className="space-y-2">
          {(data ?? []).map((m) => {
            const isOwner = m.userOid === project.ownerOid;
            return (
              <li
                key={`${m.projectId}-${m.userOid}`}
                data-testid={`member-row-${m.userOid}`}
                className="flex items-center justify-between rounded-md border border-border bg-background px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-muted-foreground">
                    {m.userOid}
                  </span>
                  <Badge
                    variant={
                      m.role === "project_owner" ? "authoritative" : "secondary"
                    }
                  >
                    {m.role === "project_owner" && (
                      <Crown className="h-3 w-3" aria-hidden />
                    )}
                    {m.role === "project_owner" ? "Owner" : "Miembro"}
                  </Badge>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={isOwner || remove.isPending}
                  onClick={() => handleRemove(m.userOid)}
                  aria-label={`Quitar ${m.userOid}`}
                >
                  <Trash2 className="h-4 w-4" aria-hidden />
                </Button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
