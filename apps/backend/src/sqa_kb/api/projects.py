"""Endpoints de proyectos + memberships (Fase 9.2).

Flujo:
    POST   /projects                   GK Lead crea proyecto + designa owner
    GET    /projects                   Lista filtrada por visibilidad
    GET    /projects/{id}              Detalle del proyecto
    PUT    /projects/{id}              Edita slug/name/description
    DELETE /projects/{id}              Soft-delete (archive) — solo GK Lead

    GET    /projects/{id}/members      Lista miembros
    POST   /projects/{id}/members      Añade miembro por email + role
    DELETE /projects/{id}/members/{oid}  Quita miembro

Thin wrapper: valida el request HTTP y delega en `ProjectService`. Las
decisiones de autorización viven en el servicio (`PermissionPolicy`).
"""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from sqa_kb.api.dependencies import CurrentUser, ProjectServiceDep
from sqa_kb.domain.entities import Project, ProjectMember
from sqa_kb.domain.value_objects import ProjectMemberRole
from sqa_kb.services.project_service import (
    AddMemberInput,
    CreateProjectInput,
    UpdateProjectInput,
)

router = APIRouter(tags=["projects"], prefix="/projects")


# ===========================================================================
# Schemas
# ===========================================================================


class _CamelBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CreateProjectBody(_CamelBase):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9-]*$")
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    owner_email: EmailStr
    """Email del usuario que será `project_owner` inicial."""


class UpdateProjectBody(_CamelBase):
    slug: str | None = Field(
        default=None, min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9-]*$"
    )
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class AddMemberBody(_CamelBase):
    email: EmailStr
    role: ProjectMemberRole = ProjectMemberRole.MEMBER


# ===========================================================================
# Endpoints — projects
# ===========================================================================


@router.post("", response_model=Project, status_code=201)
async def create_project(
    body: CreateProjectBody,
    service: ProjectServiceDep,
    user: CurrentUser,
) -> Project:
    """Crea un proyecto y designa al `owner_email` como `project_owner`."""
    return await service.create(
        user,
        CreateProjectInput(
            slug=body.slug,
            name=body.name,
            description=body.description,
            owner_email=body.owner_email,
        ),
    )


@router.get("", response_model=list[Project])
async def list_projects(
    service: ProjectServiceDep,
    user: CurrentUser,
) -> Sequence[Project]:
    """Lista proyectos visibles al caller (gk_lead ve todo; colaborador
    solo donde es miembro)."""
    return await service.list_visible(user)


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    service: ProjectServiceDep,
    user: CurrentUser,
) -> Project:
    """Detalle del proyecto. 404 si no tiene visibilidad (no diferenciamos
    'no existe' vs 'no podés verlo')."""
    return await service.get(user, project_id)


@router.put("/{project_id}", response_model=Project)
async def update_project(
    project_id: str,
    body: UpdateProjectBody,
    service: ProjectServiceDep,
    user: CurrentUser,
) -> Project:
    """Edita slug / name / description del proyecto."""
    return await service.update(
        user,
        project_id,
        UpdateProjectInput(
            slug=body.slug,
            name=body.name,
            description=body.description,
        ),
    )


@router.delete("/{project_id}", response_model=Project)
async def archive_project(
    project_id: str,
    service: ProjectServiceDep,
    user: CurrentUser,
) -> Project:
    """Soft-delete: setea `archived_at`. Solo GK Lead, y no para `gk-general`."""
    return await service.archive(user, project_id)


# ===========================================================================
# Endpoints — members
# ===========================================================================


@router.get("/{project_id}/members", response_model=list[ProjectMember])
async def list_members(
    project_id: str,
    service: ProjectServiceDep,
    user: CurrentUser,
) -> Sequence[ProjectMember]:
    return await service.list_members(user, project_id)


@router.post(
    "/{project_id}/members", response_model=ProjectMember, status_code=201
)
async def add_member(
    project_id: str,
    body: AddMemberBody,
    service: ProjectServiceDep,
    user: CurrentUser,
) -> ProjectMember:
    """Añade un miembro al proyecto por email. Idempotente: si el usuario
    ya era miembro, actualiza su rol."""
    return await service.add_member(
        user,
        project_id,
        AddMemberInput(email=body.email, role=body.role),
    )


@router.delete("/{project_id}/members/{user_oid}", status_code=204)
async def remove_member(
    project_id: str,
    user_oid: str,
    service: ProjectServiceDep,
    user: CurrentUser,
) -> None:
    """Quita un miembro del proyecto. No-op si no era miembro."""
    await service.remove_member(user, project_id, user_oid)
