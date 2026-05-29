"""PostgresDocumentationSessionRepository (Fase 9.5).

CRUD sobre `documentation_sessions`. La lógica de transiciones y
validación por step vive en `DocumentationSessionService` — el repo
solo expone read/write.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.adapters.repositories.postgres import models
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.domain.entities import DocumentationSession
from sqa_kb.domain.errors import NotFoundError
from sqa_kb.domain.value_objects import (
    DocumentationSessionStatus,
    DocumentationStep,
)


def _to_entity(m: models.DocumentationSessionModel) -> DocumentationSession:
    return DocumentationSession(
        id=m.id,
        project_id=m.project_id,
        owner_oid=m.owner_oid,
        status=DocumentationSessionStatus(m.status),
        current_step=DocumentationStep(m.current_step),
        step_data=dict(m.step_data or {}),
        started_at=m.started_at,
        finalized_at=m.finalized_at,
        generated_document_ids=list(m.generated_document_ids or []),
    )


class PostgresDocumentationSessionRepository:
    def __init__(self, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._session_factory: async_sessionmaker = session_factory

    async def create(self, session: DocumentationSession) -> DocumentationSession:
        async with session_scope(self._session_factory) as db:
            model = models.DocumentationSessionModel(
                id=session.id,
                project_id=session.project_id,
                owner_oid=session.owner_oid,
                status=str(session.status),
                current_step=str(session.current_step),
                step_data=session.step_data,
                generated_document_ids=list(session.generated_document_ids),
            )
            db.add(model)
            await db.flush()
            await db.refresh(model)
            return _to_entity(model)

    async def get(self, session_id: str) -> DocumentationSession | None:
        async with self._session_factory() as db:
            model = await db.get(
                models.DocumentationSessionModel, session_id
            )
            return _to_entity(model) if model else None

    async def list_for_project(
        self, project_id: str
    ) -> Sequence[DocumentationSession]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(models.DocumentationSessionModel)
                .where(
                    models.DocumentationSessionModel.project_id == project_id
                )
                .order_by(
                    models.DocumentationSessionModel.started_at.desc()
                )
            )
            return [_to_entity(m) for m in result.scalars().all()]

    async def update(
        self, session: DocumentationSession
    ) -> DocumentationSession:
        async with session_scope(self._session_factory) as db:
            model = await db.get(
                models.DocumentationSessionModel, session.id
            )
            if model is None:
                raise NotFoundError(
                    f"Sesión de documentación {session.id} no encontrada"
                )
            model.status = str(session.status)
            model.current_step = str(session.current_step)
            model.step_data = session.step_data
            model.finalized_at = session.finalized_at
            model.generated_document_ids = list(session.generated_document_ids)
            await db.flush()
            await db.refresh(model)
            return _to_entity(model)
