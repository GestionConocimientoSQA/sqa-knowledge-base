"""PostgresSkillRepository — prompts editables del agente."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.adapters.repositories.postgres import mappers, models
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.domain.entities import Skill


class PostgresSkillRepository:
    def __init__(self, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._session_factory: async_sessionmaker = session_factory

    async def list_enabled(self) -> Sequence[Skill]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(models.SkillModel)
                .where(models.SkillModel.enabled.is_(True))
                .order_by(models.SkillModel.name)
            )
            return [mappers.to_skill_entity(s) for s in result.scalars().all()]

    async def get(self, skill_id: str) -> Skill | None:
        async with self._session_factory() as db:
            m = await db.get(models.SkillModel, skill_id)
            return mappers.to_skill_entity(m) if m else None

    async def upsert(self, skill: Skill) -> Skill:
        async with session_scope(self._session_factory) as db:
            existing = await db.get(models.SkillModel, skill.id)
            if existing is None:
                existing = models.SkillModel(
                    id=skill.id,
                    name=skill.name,
                    description=skill.description,
                    body_markdown=skill.body_markdown,
                    enabled=skill.enabled,
                    version=skill.version,
                    updated_by_oid=skill.updated_by_oid,
                )
                db.add(existing)
            else:
                existing.name = skill.name
                existing.description = skill.description
                existing.body_markdown = skill.body_markdown
                existing.enabled = skill.enabled
                existing.version = skill.version + 1
                existing.updated_by_oid = skill.updated_by_oid
            await db.flush()
            await db.refresh(existing)
            return mappers.to_skill_entity(existing)
