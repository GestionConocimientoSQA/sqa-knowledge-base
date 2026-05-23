"""PostgresTaxonomyRepository — carpetas + tipos de documento.

Lectura libre (cualquier user autenticado). Escritura solo GK Lead via
servicios admin (Fase 9). Por ahora solo expone los reads que necesita
el frontend.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.adapters.repositories.postgres import mappers, models
from sqa_kb.domain.entities import Category, DocType


class PostgresTaxonomyRepository:
    def __init__(self, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._session_factory: async_sessionmaker = session_factory

    async def list_categories(self) -> Sequence[Category]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(models.CategoryModel).order_by(models.CategoryModel.code)
            )
            return [mappers.to_category_entity(m) for m in result.scalars().all()]

    async def list_doc_types(self) -> Sequence[DocType]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(models.DocTypeModel).order_by(models.DocTypeModel.code)
            )
            return [mappers.to_doc_type_entity(m) for m in result.scalars().all()]
