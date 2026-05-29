"""PostgresProjectRepository — proyectos + memberships (Fase 9.2).

Implementa el port `ProjectRepository`. La autorización (quién puede ver
qué proyecto) vive en `ProjectService`, no acá — este adapter solo expone
operaciones CRUD limpias sobre `projects` y `project_members`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.adapters.repositories.postgres import mappers, models
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.domain.entities import Project, ProjectMember
from sqa_kb.domain.errors import NotFoundError


class PostgresProjectRepository:
    """Implementación del puerto `ProjectRepository` con SQLAlchemy 2.0."""

    def __init__(self, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._session_factory: async_sessionmaker = session_factory

    # -----------------------------------------------------------------------
    # Projects
    # -----------------------------------------------------------------------

    async def create(self, project: Project) -> Project:
        async with session_scope(self._session_factory) as db:
            model = mappers.new_project_model(project)
            db.add(model)
            await db.flush()
            await db.refresh(model)
            return mappers.to_project_entity(model)

    async def get(self, project_id: str) -> Project | None:
        async with self._session_factory() as db:
            model = await db.get(models.ProjectModel, project_id)
            return mappers.to_project_entity(model) if model else None

    async def get_by_slug(self, slug: str) -> Project | None:
        async with self._session_factory() as db:
            result = await db.execute(
                select(models.ProjectModel).where(models.ProjectModel.slug == slug)
            )
            model = result.scalar_one_or_none()
            return mappers.to_project_entity(model) if model else None

    async def list_all(self) -> Sequence[Project]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(models.ProjectModel).order_by(
                    models.ProjectModel.archived_at.is_(None).desc(),
                    models.ProjectModel.created_at.desc(),
                )
            )
            return [mappers.to_project_entity(m) for m in result.scalars().all()]

    async def list_for_user(self, user_oid: str) -> Sequence[Project]:
        """JOIN con `project_members` — un proyecto aparece solo si el
        usuario es miembro."""
        async with self._session_factory() as db:
            stmt = (
                select(models.ProjectModel)
                .join(
                    models.ProjectMemberModel,
                    models.ProjectMemberModel.project_id == models.ProjectModel.id,
                )
                .where(models.ProjectMemberModel.user_oid == user_oid)
                .order_by(models.ProjectModel.created_at.desc())
            )
            result = await db.execute(stmt)
            return [mappers.to_project_entity(m) for m in result.scalars().all()]

    async def update(self, project: Project) -> Project:
        async with session_scope(self._session_factory) as db:
            model = await db.get(models.ProjectModel, project.id)
            if model is None:
                raise NotFoundError(f"Proyecto {project.id} no encontrado")
            # Campos editables (id, owner_oid, created_at son inmutables).
            model.slug = project.slug
            model.name = project.name
            model.description = project.description
            model.archived_at = project.archived_at
            await db.flush()
            await db.refresh(model)
            return mappers.to_project_entity(model)

    async def archive(self, project_id: str) -> Project:
        async with session_scope(self._session_factory) as db:
            model = await db.get(models.ProjectModel, project_id)
            if model is None:
                raise NotFoundError(f"Proyecto {project_id} no encontrado")
            model.archived_at = datetime.now(UTC)
            await db.flush()
            await db.refresh(model)
            return mappers.to_project_entity(model)

    # -----------------------------------------------------------------------
    # Memberships
    # -----------------------------------------------------------------------

    async def add_member(self, member: ProjectMember) -> ProjectMember:
        """Upsert: `ON CONFLICT (project_id, user_oid) DO UPDATE` reemplaza
        el rol si ya existía la membership."""
        async with session_scope(self._session_factory) as db:
            stmt = pg_insert(models.ProjectMemberModel).values(
                project_id=member.project_id,
                user_oid=member.user_oid,
                role=str(member.role),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["project_id", "user_oid"],
                set_={"role": stmt.excluded.role},
            )
            await db.execute(stmt)
            # Re-leemos para devolver el `added_at` real (server_default).
            result = await db.execute(
                select(models.ProjectMemberModel).where(
                    models.ProjectMemberModel.project_id == member.project_id,
                    models.ProjectMemberModel.user_oid == member.user_oid,
                )
            )
            row = result.scalar_one()
            return mappers.to_project_member_entity(row)

    async def remove_member(self, project_id: str, user_oid: str) -> None:
        async with session_scope(self._session_factory) as db:
            model = await db.get(
                models.ProjectMemberModel, (project_id, user_oid)
            )
            if model is not None:
                await db.delete(model)

    async def list_members(self, project_id: str) -> Sequence[ProjectMember]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(models.ProjectMemberModel)
                .where(models.ProjectMemberModel.project_id == project_id)
                .order_by(models.ProjectMemberModel.added_at.asc())
            )
            return [
                mappers.to_project_member_entity(m)
                for m in result.scalars().all()
            ]

    async def get_membership(
        self, project_id: str, user_oid: str
    ) -> ProjectMember | None:
        async with self._session_factory() as db:
            model = await db.get(
                models.ProjectMemberModel, (project_id, user_oid)
            )
            return mappers.to_project_member_entity(model) if model else None
