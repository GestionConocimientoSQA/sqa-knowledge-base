"use client";

/**
 * Diálogo modal "Crear proyecto" (Fase 9.6).
 *
 * Form simple: nombre, slug, descripción, email del project_owner.
 * El submit dispara `useCreateProject` y, al éxito, cierra el modal y
 * notifica al padre con el proyecto creado.
 */
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateProject } from "@/lib/hooks/use-projects";
import type { Project } from "@/types/domain";

interface CreateProjectDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated?: (project: Project) => void;
}

const SLUG_RE = /^[a-z][a-z0-9-]*$/;

export function CreateProjectDialog({
  open,
  onClose,
  onCreated,
}: CreateProjectDialogProps) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [ownerEmail, setOwnerEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const create = useCreateProject();

  if (!open) return null;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) return setError("El nombre es obligatorio");
    if (!SLUG_RE.test(slug))
      return setError(
        "El slug debe arrancar con letra minúscula y solo usar a-z, 0-9 y guiones",
      );
    if (!ownerEmail.includes("@"))
      return setError("Email del owner inválido");
    setError(null);
    create.mutate(
      {
        slug: slug.trim(),
        name: name.trim(),
        description: description.trim(),
        ownerEmail: ownerEmail.trim(),
      },
      {
        onSuccess: (project) => {
          setName("");
          setSlug("");
          setDescription("");
          setOwnerEmail("");
          onCreated?.(project);
          onClose();
        },
        onError: (err) => setError(err.message),
      },
    );
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-project-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
    >
      <div className="w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-lg">
        <h2
          id="create-project-title"
          className="mb-4 font-display text-lg font-bold"
        >
          Crear proyecto
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="proj-name">Nombre</Label>
            <Input
              id="proj-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Cliente ACME"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="proj-slug">Slug</Label>
            <Input
              id="proj-slug"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="cliente-acme"
              required
            />
            <p className="text-xs text-muted-foreground">
              Identificador URL-friendly. Minúsculas, números y guiones.
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="proj-desc">Descripción</Label>
            <textarea
              id="proj-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Breve descripción del proyecto..."
              rows={3}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="proj-owner">Email del project_owner</Label>
            <Input
              id="proj-owner"
              type="email"
              value={ownerEmail}
              onChange={(e) => setOwnerEmail(e.target.value)}
              placeholder="responsable@cliente.com"
              required
            />
            <p className="text-xs text-muted-foreground">
              Será administrador del proyecto. Debe existir en el directorio.
            </p>
          </div>

          {error && (
            <p
              role="alert"
              className="rounded-md border border-error/40 bg-error/5 px-3 py-2 text-sm text-error"
            >
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              disabled={create.isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Creando…" : "Crear proyecto"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
