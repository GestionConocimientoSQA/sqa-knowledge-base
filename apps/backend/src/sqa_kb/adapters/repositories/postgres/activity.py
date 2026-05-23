"""PostgresActivityRepository — feed cronológico para el dashboard."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.adapters.repositories.postgres import mappers, models
from sqa_kb.domain.entities import RecentActivityItem


class PostgresActivityRepository:
    def __init__(self, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._session_factory: async_sessionmaker = session_factory

    async def recent(
        self, *, limit: int = 12, since_iso: str | None = None
    ) -> Sequence[RecentActivityItem]:
        async with self._session_factory() as db:
            stmt = select(models.RecentActivityModel)
            if since_iso:
                stmt = stmt.where(
                    models.RecentActivityModel.at >= datetime.fromisoformat(since_iso)
                )
            stmt = stmt.order_by(models.RecentActivityModel.at.desc()).limit(limit)
            rows = (await db.execute(stmt)).scalars().all()
            return [mappers.to_activity_entity(r) for r in rows]
