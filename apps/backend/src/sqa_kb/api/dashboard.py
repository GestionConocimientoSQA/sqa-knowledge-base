"""Endpoints del dashboard — hot topics + recent activity.

Mismas formas que el frontend espera en `lib/api/documents.ts` (Fase 7.1):
- HotTopic[]: `topic`, `queries_30d`, `citation_count`, `is_gap`
- RecentActivityItem[]: `id`, `type`, `actor_oid`, `actor_name`, `at`,
  `summary`, `ref_url`
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Query

from sqa_kb.api.dependencies import (
    ActivityRepoDep,
    CurrentUser,
    QueryRepoDep,
)
from sqa_kb.domain.entities import HotTopic, RecentActivityItem

router = APIRouter(tags=["dashboard"], prefix="/dashboard")


@router.get("/hot-topics", response_model=list[HotTopic])
async def hot_topics(
    repo: QueryRepoDep,
    _user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=50)] = 8,
) -> Sequence[HotTopic]:
    """Top de temas demandados — alimenta el panel del dashboard."""
    return await repo.hot_topics(limit=limit)


@router.get("/activity", response_model=list[RecentActivityItem])
async def recent_activity(
    repo: ActivityRepoDep,
    _user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 12,
    since: Annotated[str | None, Query(description="ISO datetime")] = None,
) -> Sequence[RecentActivityItem]:
    """Feed cronológico de actividad reciente para el dashboard admin."""
    return await repo.recent(limit=limit, since_iso=since)
