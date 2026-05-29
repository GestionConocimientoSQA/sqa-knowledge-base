"""PostgresProjectTaxonomyRepository — overrides + extensiones de
taxonomía per-proyecto (Fase 9.4).

Solo expone CRUD sobre `project_categories` y `project_doc_types`. El
merge con el catálogo global vive en `ProjectTaxonomyService`.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.adapters.repositories.postgres import models
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.domain.entities import ProjectCategory, ProjectDocType


def _to_category_entity(m: models.ProjectCategoryModel) -> ProjectCategory:
    return ProjectCategory(
        project_id=m.project_id,
        code=m.code,
        label=m.label,
        parent_global_code=m.parent_global_code,
        is_override=m.is_override,
    )


def _to_doc_type_entity(m: models.ProjectDocTypeModel) -> ProjectDocType:
    return ProjectDocType(
        project_id=m.project_id,
        code=m.code,
        label=m.label,
        parent_global_code=m.parent_global_code,
        is_override=m.is_override,
    )


class PostgresProjectTaxonomyRepository:
    """Adapter PG del puerto `ProjectTaxonomyRepository`."""

    def __init__(self, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._session_factory: async_sessionmaker = session_factory

    # -----------------------------------------------------------------------
    # Categories
    # -----------------------------------------------------------------------

    async def list_categories(
        self, project_id: str
    ) -> Sequence[ProjectCategory]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(models.ProjectCategoryModel)
                .where(models.ProjectCategoryModel.project_id == project_id)
                .order_by(models.ProjectCategoryModel.code.asc())
            )
            return [_to_category_entity(m) for m in result.scalars().all()]

    async def upsert_category(
        self, category: ProjectCategory
    ) -> ProjectCategory:
        """ON CONFLICT (project_id, code) DO UPDATE."""
        async with session_scope(self._session_factory) as db:
            stmt = pg_insert(models.ProjectCategoryModel).values(
                project_id=category.project_id,
                code=category.code,
                label=category.label,
                parent_global_code=category.parent_global_code,
                is_override=category.is_override,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["project_id", "code"],
                set_={
                    "label": stmt.excluded.label,
                    "parent_global_code": stmt.excluded.parent_global_code,
                    "is_override": stmt.excluded.is_override,
                },
            )
            await db.execute(stmt)
            result = await db.execute(
                select(models.ProjectCategoryModel).where(
                    models.ProjectCategoryModel.project_id == category.project_id,
                    models.ProjectCategoryModel.code == category.code,
                )
            )
            return _to_category_entity(result.scalar_one())

    async def delete_category(self, project_id: str, code: str) -> None:
        async with session_scope(self._session_factory) as db:
            model = await db.get(
                models.ProjectCategoryModel, (project_id, code)
            )
            if model is not None:
                await db.delete(model)

    # -----------------------------------------------------------------------
    # Doc types
    # -----------------------------------------------------------------------

    async def list_doc_types(
        self, project_id: str
    ) -> Sequence[ProjectDocType]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(models.ProjectDocTypeModel)
                .where(models.ProjectDocTypeModel.project_id == project_id)
                .order_by(models.ProjectDocTypeModel.code.asc())
            )
            return [_to_doc_type_entity(m) for m in result.scalars().all()]

    async def upsert_doc_type(
        self, doc_type: ProjectDocType
    ) -> ProjectDocType:
        async with session_scope(self._session_factory) as db:
            stmt = pg_insert(models.ProjectDocTypeModel).values(
                project_id=doc_type.project_id,
                code=doc_type.code,
                label=doc_type.label,
                parent_global_code=doc_type.parent_global_code,
                is_override=doc_type.is_override,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["project_id", "code"],
                set_={
                    "label": stmt.excluded.label,
                    "parent_global_code": stmt.excluded.parent_global_code,
                    "is_override": stmt.excluded.is_override,
                },
            )
            await db.execute(stmt)
            result = await db.execute(
                select(models.ProjectDocTypeModel).where(
                    models.ProjectDocTypeModel.project_id == doc_type.project_id,
                    models.ProjectDocTypeModel.code == doc_type.code,
                )
            )
            return _to_doc_type_entity(result.scalar_one())

    async def delete_doc_type(self, project_id: str, code: str) -> None:
        async with session_scope(self._session_factory) as db:
            model = await db.get(
                models.ProjectDocTypeModel, (project_id, code)
            )
            if model is not None:
                await db.delete(model)
