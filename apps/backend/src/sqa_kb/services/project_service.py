"""ProjectService — gobierno de proyectos y memberships (Fase 9.2).

Orquesta el CRUD de proyectos + administración de miembros, aplicando
las reglas de autorización del ADR 0009 §D2:

- Solo `gk_lead` crea / elimina proyectos.
- `gk_lead` o el `project_owner` del proyecto puede editar el proyecto,
  añadir/quitar miembros y editar la taxonomía.
- `colaborador` sin membership en el proyecto: sin acceso.

La política de permisos vive en `PermissionPolicy` — una clase explícita
que toma `(user, project_id)` y resuelve la `ProjectMembership` derivada.
Esto centraliza la lógica de autorización (DRY + testable).

Diseño SOLID:
- El servicio recibe `ProjectRepository` + `UserRepository` por
  constructor (DIP).
- El router HTTP (`api/projects.py`) es un thin wrapper: valida request +
  delega + serializa.
- Los tests pueden usar fakes de ambos repos para cubrir todos los
  caminos sin tocar la DB.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqa_kb.domain.entities import (
    Project,
    ProjectMember,
    ProjectMembership,
    User,
)
from sqa_kb.domain.errors import ForbiddenError, NotFoundError, ValidationError
from sqa_kb.domain.value_objects import ProjectMemberRole, RoleId
from sqa_kb.ports.repositories import ProjectRepository, UserRepository

# ===========================================================================
# Permission policy
# ===========================================================================


@dataclass(slots=True)
class PermissionPolicy:
    """Centraliza las decisiones de autorización per-proyecto.

    Es un value object con un repo inyectado. Se construye on-demand por
    cada request (cheap) o como dependencia (también vale). No mantiene
    estado entre llamadas.

    Uso típico desde un endpoint:

        policy = PermissionPolicy(project_repo)
        membership = await policy.resolve(user, project_id)
        if not membership.can_approve:
            raise ForbiddenError(...)
    """

    project_repo: ProjectRepository

    async def resolve(
        self, user: User, project_id: str
    ) -> ProjectMembership:
        """Construye el `ProjectMembership` derivado del usuario.

        `gk_lead` no necesita membership (acceso por privilegio global) —
        igual consultamos el rol per-proyecto por si existe (para auditar
        correctamente). `colaborador` sin membership tiene `project_role=None`
        y todas las `can_*` darán False.

        El método NO chequea que el proyecto exista — eso es responsabilidad
        del caller (queremos diferenciar 404 de 403). Aquí solo resolvemos
        la membership.
        """
        membership = await self.project_repo.get_membership(
            project_id, user.oid
        )
        return ProjectMembership(
            project_id=project_id,
            user_oid=user.oid,
            global_role=RoleId(user.role_id),
            project_role=membership.role if membership else None,
        )


# ===========================================================================
# Service
# ===========================================================================


@dataclass(frozen=True, slots=True)
class CreateProjectInput:
    """Inputs para `POST /projects`."""

    slug: str
    name: str
    description: str
    owner_email: str
    """Email del usuario que será `project_owner` inicial. El servicio lo
    resuelve a `oid` via `UserRepository.get_by_email`."""


@dataclass(frozen=True, slots=True)
class UpdateProjectInput:
    """Inputs para `PUT /projects/{id}`."""

    name: str | None = None
    description: str | None = None
    slug: str | None = None


@dataclass(frozen=True, slots=True)
class AddMemberInput:
    """Inputs para `POST /projects/{id}/members`."""

    email: str
    role: ProjectMemberRole


class ProjectService:
    """Orquestador del CRUD de proyectos + memberships."""

    def __init__(
        self,
        project_repo: ProjectRepository,
        user_repo: UserRepository,
    ) -> None:
        self._projects = project_repo
        self._users = user_repo
        self._policy = PermissionPolicy(project_repo)

    # -----------------------------------------------------------------------
    # Helpers (privados)
    # -----------------------------------------------------------------------

    async def _require_project(self, project_id: str) -> Project:
        project = await self._projects.get(project_id)
        if project is None:
            raise NotFoundError(f"Proyecto {project_id} no encontrado")
        return project

    async def _require_user_by_email(self, email: str) -> User:
        user = await self._users.get_by_email(email)
        if user is None:
            raise NotFoundError(
                f"Usuario con email {email!r} no encontrado en el directorio"
            )
        return user

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def create(self, caller: User, payload: CreateProjectInput) -> Project:
        """Crea un proyecto. Solo `gk_lead`.

        Designa al usuario indicado por `owner_email` como `project_owner`
        del proyecto recién creado. El proyecto queda con `owner_oid` = oid
        de ese usuario (también podría ser `caller.oid` si quisiéramos que
        el creador sea el owner, pero el ADR dice: GK Lead designa).
        """
        if caller.role_id != RoleId.GKLEAD:
            raise ForbiddenError("Solo GK Lead puede crear proyectos")

        # Slug único.
        existing = await self._projects.get_by_slug(payload.slug)
        if existing is not None:
            raise ValidationError(f"Slug {payload.slug!r} ya está en uso")

        # Resolver email → oid antes de crear (UX: error temprano si el
        # email no está en el directorio).
        owner_user = await self._require_user_by_email(payload.owner_email)

        project = Project(
            id=str(uuid.uuid4()),
            slug=payload.slug,
            name=payload.name,
            description=payload.description,
            owner_oid=owner_user.oid,
            created_at=datetime.now(UTC),
        )
        created = await self._projects.create(project)

        # Auto-añadir al owner como `project_owner` del proyecto.
        await self._projects.add_member(
            ProjectMember(
                project_id=created.id,
                user_oid=owner_user.oid,
                role=ProjectMemberRole.PROJECT_OWNER,
                added_at=datetime.now(UTC),
            )
        )
        return created

    async def list_visible(self, caller: User) -> Sequence[Project]:
        """`gk_lead` ve todo; el resto ve solo donde es miembro."""
        if caller.role_id == RoleId.GKLEAD:
            return await self._projects.list_all()
        return await self._projects.list_for_user(caller.oid)

    async def get(self, caller: User, project_id: str) -> Project:
        """Lee un proyecto. Requiere `can_read`."""
        project = await self._require_project(project_id)
        membership = await self._policy.resolve(caller, project_id)
        if not membership.can_read:
            raise NotFoundError(f"Proyecto {project_id} no encontrado")
        return project

    async def update(
        self, caller: User, project_id: str, payload: UpdateProjectInput
    ) -> Project:
        """Edita un proyecto. Requiere `can_edit_taxonomy` (mismo gate que
        otras tareas de administración del proyecto)."""
        project = await self._require_project(project_id)
        membership = await self._policy.resolve(caller, project_id)
        if not membership.can_edit_taxonomy:
            raise ForbiddenError(
                "Solo project_owner o gk_lead pueden editar el proyecto"
            )
        updated = project.model_copy(
            update={
                "slug": payload.slug or project.slug,
                "name": payload.name or project.name,
                "description": (
                    payload.description if payload.description is not None else project.description
                ),
            }
        )
        # Si cambió el slug, validar uniqueness.
        if updated.slug != project.slug:
            collision = await self._projects.get_by_slug(updated.slug)
            if collision is not None and collision.id != project.id:
                raise ValidationError(
                    f"Slug {updated.slug!r} ya está en uso"
                )
        return await self._projects.update(updated)

    async def archive(self, caller: User, project_id: str) -> Project:
        """Archiva (soft-delete) un proyecto. Solo `gk_lead`.

        No permitimos archivar al `gk-general` — es el proyecto raíz.
        """
        if caller.role_id != RoleId.GKLEAD:
            raise ForbiddenError("Solo GK Lead puede archivar proyectos")
        project = await self._require_project(project_id)
        if project.slug == "gk-general":
            raise ValidationError("No se puede archivar el proyecto raíz")
        return await self._projects.archive(project_id)

    # -----------------------------------------------------------------------
    # Members
    # -----------------------------------------------------------------------

    async def list_members(
        self, caller: User, project_id: str
    ) -> Sequence[ProjectMember]:
        """Lista miembros. Requiere `can_read`."""
        await self._require_project(project_id)
        membership = await self._policy.resolve(caller, project_id)
        if not membership.can_read:
            raise NotFoundError(f"Proyecto {project_id} no encontrado")
        return await self._projects.list_members(project_id)

    async def add_member(
        self, caller: User, project_id: str, payload: AddMemberInput
    ) -> ProjectMember:
        """Añade un miembro al proyecto. Requiere `can_manage_members`."""
        await self._require_project(project_id)
        membership = await self._policy.resolve(caller, project_id)
        if not membership.can_manage_members:
            raise ForbiddenError(
                "Solo project_owner o gk_lead pueden añadir miembros"
            )
        target_user = await self._require_user_by_email(payload.email)
        return await self._projects.add_member(
            ProjectMember(
                project_id=project_id,
                user_oid=target_user.oid,
                role=payload.role,
                added_at=datetime.now(UTC),
            )
        )

    async def remove_member(
        self, caller: User, project_id: str, user_oid: str
    ) -> None:
        """Quita un miembro del proyecto. Requiere `can_manage_members`.

        No permitimos remover al `owner_oid` del proyecto — para "cambiar
        el dueño" hay que `update()` primero (no implementado en 9.2, queda
        para 9.6 cuando el frontend cablee la transferencia)."""
        project = await self._require_project(project_id)
        membership = await self._policy.resolve(caller, project_id)
        if not membership.can_manage_members:
            raise ForbiddenError(
                "Solo project_owner o gk_lead pueden quitar miembros"
            )
        if user_oid == project.owner_oid:
            raise ValidationError(
                "No se puede quitar al owner del proyecto. "
                "Transferí la propiedad primero."
            )
        await self._projects.remove_member(project_id, user_oid)
