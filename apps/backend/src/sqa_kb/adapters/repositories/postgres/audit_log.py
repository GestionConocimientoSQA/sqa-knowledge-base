"""PostgresAuditLogRepository — append-only.

No hay update ni delete. Si TI define un audit log central
([[docs/alineacion-arquitectura-ti.md §2.5]]), un decorator alrededor de
este repo escribirá también al log compartido sin tocar callers.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.adapters.repositories.postgres import mappers, models
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.domain.entities import AuditLog


class PostgresAuditLogRepository:
    def __init__(self, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._session_factory: async_sessionmaker = session_factory

    async def append(self, entry: AuditLog) -> AuditLog:
        async with session_scope(self._session_factory) as db:
            model = mappers.new_audit_model(entry)
            db.add(model)
            await db.flush()
            return entry

    async def list_for_resource(
        self,
        resource_id: str,
        *,
        limit: int = 100,
    ) -> Sequence[AuditLog]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(models.AuditLogModel)
                .where(models.AuditLogModel.resource_id == resource_id)
                .order_by(models.AuditLogModel.at.desc())
                .limit(limit)
            )
            return [mappers.to_audit_entity(r) for r in result.scalars().all()]
