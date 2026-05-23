"""PostgresUserRepository — implementación del puerto UserRepository."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.adapters.repositories.postgres import mappers, models
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.domain.entities import User


class PostgresUserRepository:
    """Espejo del catálogo de usuarios — alimentado desde JWT en login."""

    def __init__(self, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._session_factory: async_sessionmaker = session_factory

    async def upsert_from_token(self, user: User) -> User:
        async with session_scope(self._session_factory) as session:
            existing = await session.get(models.UserModel, user.oid)
            if existing is None:
                model = mappers.new_user_model(user)
                session.add(model)
                await session.flush()
                await session.refresh(model)
                return mappers.to_user_entity(model)
            mappers.apply_user_to_model(user, existing)
            await session.flush()
            await session.refresh(existing)
            return mappers.to_user_entity(existing)

    async def get_by_oid(self, oid: str) -> User | None:
        async with self._session_factory() as session:
            model = await session.get(models.UserModel, oid)
            return mappers.to_user_entity(model) if model else None

    async def list_by_role(self, role: str, *, limit: int = 50) -> Sequence[User]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(models.UserModel)
                .where(models.UserModel.role_id == role)
                .order_by(models.UserModel.created_at.desc())
                .limit(limit)
            )
            return [mappers.to_user_entity(m) for m in result.scalars().all()]
