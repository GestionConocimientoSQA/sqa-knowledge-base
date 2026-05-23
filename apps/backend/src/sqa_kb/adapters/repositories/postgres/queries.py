"""PostgresQueryRepository — consultas (modo B) + hot topics.

`hot_topics` lee del snapshot `hot_topics_snapshot` que llena el worker
de Fase 3. Mientras tanto devuelve [] — el frontend tolera empty state.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.adapters.repositories.postgres import models
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.domain.entities import HotTopic, Query, QueryCitation


class PostgresQueryRepository:
    def __init__(self, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._session_factory: async_sessionmaker = session_factory

    async def record(self, query: Query) -> Query:
        async with session_scope(self._session_factory) as db:
            db.add(
                models.QueryModel(
                    id=query.id,
                    user_oid=query.user_oid,
                    session_id=query.session_id,
                    text=query.text,
                    asked_at=query.asked_at,
                    answered_at=query.answered_at,
                    has_result=query.has_result,
                )
            )
            return query

    async def add_citation(self, citation: QueryCitation) -> QueryCitation:
        async with session_scope(self._session_factory) as db:
            db.add(
                models.QueryCitationModel(
                    query_id=citation.query_id,
                    document_id=citation.document_id,
                    section=citation.section,
                    snippet=citation.snippet,
                )
            )
            return citation

    async def hot_topics(
        self, *, since_days: int = 30, limit: int = 8
    ) -> Sequence[HotTopic]:
        # since_days lo dejamos parametrizado a futuro (el worker de F3
        # puede aceptar window distinto). Ahora leemos el snapshot tal cual.
        del since_days
        async with self._session_factory() as db:
            result = await db.execute(
                select(models.HotTopicModel)
                .order_by(models.HotTopicModel.queries_30d.desc())
                .limit(limit)
            )
            return [
                HotTopic(
                    topic=m.topic,
                    queries_30d=m.queries_30d,
                    citation_count=m.citation_count,
                    is_gap=m.is_gap,
                )
                for m in result.scalars().all()
            ]
