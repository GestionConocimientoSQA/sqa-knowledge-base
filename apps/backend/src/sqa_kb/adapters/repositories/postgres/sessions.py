"""PostgresSessionRepository — sesiones de chat con Aria + mensajes.

IDOR enforcement: TODAS las queries con `session_id` reciben `caller_oid`
y filtran por `owner_oid = caller_oid` (ver [[project-security-idor-check]]).
La lógica de admin-puede-leer-cualquiera vive en services + audit log.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.adapters.repositories.postgres import mappers, models
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.domain.entities import Message, Session
from sqa_kb.domain.errors import NotFoundError
from sqa_kb.domain.value_objects import SessionMode, SessionStatus


class PostgresSessionRepository:
    def __init__(self, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._session_factory: async_sessionmaker = session_factory

    async def create(self, session_entity: Session) -> Session:
        async with session_scope(self._session_factory) as db:
            model = mappers.new_session_model(session_entity)
            db.add(model)
            await db.flush()
            await db.refresh(model)
            return mappers.to_session_entity(model)

    async def get(
        self, session_id: str, *, caller_oid: str
    ) -> Session | None:
        async with self._session_factory() as db:
            model = await db.get(models.SessionModel, session_id)
            if model is None or model.owner_oid != caller_oid:
                # Devolvemos None igual cuando no existe vs cuando es ajeno
                # para no filtrar existencia (defensa contra enumeración).
                return None
            return mappers.to_session_entity(model)

    async def list_for_user(
        self,
        caller_oid: str,
        *,
        mode: SessionMode | None = None,
        status: SessionStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Session]:
        async with self._session_factory() as db:
            stmt = select(models.SessionModel).where(
                models.SessionModel.owner_oid == caller_oid
            )
            if mode is not None:
                stmt = stmt.where(models.SessionModel.mode == str(mode))
            if status is not None:
                stmt = stmt.where(models.SessionModel.status == str(status))
            stmt = (
                stmt.order_by(models.SessionModel.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
            rows = (await db.execute(stmt)).scalars().all()
            return [mappers.to_session_entity(r) for r in rows]

    async def update_status(
        self,
        session_id: str,
        status: SessionStatus,
        *,
        caller_oid: str,
    ) -> Session:
        async with session_scope(self._session_factory) as db:
            model = await db.get(models.SessionModel, session_id)
            if model is None or model.owner_oid != caller_oid:
                raise NotFoundError(f"Sesión {session_id} no encontrada")
            model.status = str(status)
            await db.flush()
            await db.refresh(model)
            return mappers.to_session_entity(model)

    async def delete(self, session_id: str, *, caller_oid: str) -> None:
        async with session_scope(self._session_factory) as db:
            model = await db.get(models.SessionModel, session_id)
            if model is None or model.owner_oid != caller_oid:
                raise NotFoundError(f"Sesión {session_id} no encontrada")
            await db.delete(model)

    async def append_message(
        self, message: Message, *, caller_oid: str
    ) -> Message:
        async with session_scope(self._session_factory) as db:
            session_model = await db.get(models.SessionModel, message.session_id)
            if session_model is None or session_model.owner_oid != caller_oid:
                raise NotFoundError(f"Sesión {message.session_id} no encontrada")
            msg_model = mappers.new_message_model(message)
            db.add(msg_model)
            # Mantener message_count + current_stage + updated_at sincronizados.
            session_model.message_count += 1
            if message.stage is not None:
                session_model.current_stage = str(message.stage)
            await db.flush()
            await db.refresh(msg_model)
            return mappers.to_message_entity(msg_model)

    async def list_messages(
        self,
        session_id: str,
        *,
        caller_oid: str,
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[Message]:
        async with self._session_factory() as db:
            session_model = await db.get(models.SessionModel, session_id)
            if session_model is None or session_model.owner_oid != caller_oid:
                # No diferenciar existencia.
                return []
            stmt = (
                select(models.MessageModel)
                .where(models.MessageModel.session_id == session_id)
                .order_by(models.MessageModel.started_at.asc())
                .limit(limit)
                .offset(offset)
            )
            rows = (await db.execute(stmt)).scalars().all()
            return [mappers.to_message_entity(r) for r in rows]
