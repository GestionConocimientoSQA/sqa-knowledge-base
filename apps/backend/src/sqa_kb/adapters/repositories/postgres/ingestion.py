"""PostgresIngestionRepository — bandeja de items pendientes (modo C)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.adapters.repositories.postgres import mappers, models
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.domain.entities import IngestionItem
from sqa_kb.domain.errors import NotFoundError


class PostgresIngestionRepository:
    def __init__(self, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._session_factory: async_sessionmaker = session_factory

    async def create(self, item: IngestionItem) -> IngestionItem:
        async with session_scope(self._session_factory) as db:
            model = mappers.new_ingestion_model(item)
            db.add(model)
            await db.flush()
            await db.refresh(model)
            return mappers.to_ingestion_entity(model)

    async def get(self, item_id: str) -> IngestionItem | None:
        async with self._session_factory() as db:
            m = await db.get(models.IngestionItemModel, item_id)
            return mappers.to_ingestion_entity(m) if m else None

    async def list_pending(
        self, *, limit: int = 50, offset: int = 0
    ) -> Sequence[IngestionItem]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(models.IngestionItemModel)
                .where(
                    models.IngestionItemModel.status.in_(
                        ["pendiente-metadata", "listo", "en-revision"]
                    )
                )
                .order_by(models.IngestionItemModel.uploaded_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return [mappers.to_ingestion_entity(m) for m in result.scalars().all()]

    async def list_by_status(
        self,
        statuses=None,  # type: ignore[no-untyped-def]
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[IngestionItem]:
        async with self._session_factory() as db:
            stmt = select(models.IngestionItemModel)
            if statuses:
                stmt = stmt.where(
                    models.IngestionItemModel.status.in_([str(s) for s in statuses])
                )
            stmt = (
                stmt.order_by(models.IngestionItemModel.uploaded_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await db.execute(stmt)
            return [mappers.to_ingestion_entity(m) for m in result.scalars().all()]

    async def update(self, item: IngestionItem) -> IngestionItem:
        async with session_scope(self._session_factory) as db:
            model = await db.get(models.IngestionItemModel, item.id)
            if model is None:
                raise NotFoundError(f"Item de ingesta {item.id} no encontrado")
            for field, value in {
                "filename": item.filename,
                "size_bytes": item.size_bytes,
                "paginas": item.paginas,
                "carpeta_sugerida": (
                    str(item.carpeta_sugerida) if item.carpeta_sugerida else None
                ),
                "tipo_sugerido": (
                    str(item.tipo_sugerido) if item.tipo_sugerido else None
                ),
                "aprobador_oid": item.aprobador_oid,
                "aprobador_name": item.aprobador_name,
                "fecha_aprobacion": item.fecha_aprobacion,
                "fuente_original": item.fuente_original,
                "version": item.version,
                "status": str(item.status),
                "blob_path": item.blob_path,
                "error_detail": item.error_detail,
            }.items():
                setattr(model, field, value)
            await db.flush()
            await db.refresh(model)
            return mappers.to_ingestion_entity(model)
