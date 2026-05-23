"""Endpoints de sesiones de chat con Aria.

IDOR enforcement automático ([[project-security-idor-check]]): cada
operación recibe `caller_oid = user.oid` y el repo filtra por owner.
El admin puede ver sesiones ajenas — esa lógica vive en service Fase 2
(con audit log obligatorio según la memoria de seguridad).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from sqa_kb.api.dependencies import CurrentUser, SessionRepoDep
from sqa_kb.domain.entities import Message, Session
from sqa_kb.domain.errors import NotFoundError
from sqa_kb.domain.value_objects import SessionMode, SessionStatus

router = APIRouter(tags=["sessions"], prefix="/sessions")


# ===========================================================================
# Schemas
# ===========================================================================


class CreateSessionBody(BaseModel):
    """Body para POST /sessions. Mismo shape que el frontend usa hoy."""

    mode: SessionMode
    title: str | None = Field(
        default=None,
        max_length=255,
        description="Si se omite se genera automáticamente del modo.",
    )


class UpdateSessionStatusBody(BaseModel):
    status: SessionStatus


def _default_title(mode: SessionMode) -> str:
    return {
        SessionMode.CAPTURA: "Nueva captura",
        SessionMode.CONSULTA: "Nueva consulta",
        SessionMode.INGESTA: "Nueva ingesta",
    }[mode]


# ===========================================================================
# Endpoints
# ===========================================================================


@router.get("", response_model=list[Session])
async def list_sessions(
    repo: SessionRepoDep,
    user: CurrentUser,
    mode: Annotated[SessionMode | None, Query()] = None,
    status: Annotated[SessionStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[Session]:
    """Sesiones del usuario autenticado, ordenadas por updated_at desc."""
    return await repo.list_for_user(
        user.oid, mode=mode, status=status, limit=limit, offset=offset
    )


@router.post("", response_model=Session, status_code=201)
async def create_session(
    body: CreateSessionBody,
    repo: SessionRepoDep,
    user: CurrentUser,
) -> Session:
    """Crea una sesión nueva y devuelve su ID. El frontend hace `POST` al
    iniciar captura/consulta/ingesta desde el selector de modo."""
    now = datetime.now(UTC)
    session = Session(
        id=str(uuid.uuid4()),
        owner_oid=user.oid,
        mode=body.mode,
        title=body.title or _default_title(body.mode),
        status=SessionStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    return await repo.create(session)


@router.get("/{session_id}", response_model=Session)
async def get_session(
    session_id: str,
    repo: SessionRepoDep,
    user: CurrentUser,
) -> Session:
    """Detalle de una sesión. 404 si no existe o el caller no es dueño."""
    session = await repo.get(session_id, caller_oid=user.oid)
    if session is None:
        raise NotFoundError(f"Sesión {session_id} no encontrada")
    return session


@router.patch("/{session_id}/status", response_model=Session)
async def update_status(
    session_id: str,
    body: UpdateSessionStatusBody,
    repo: SessionRepoDep,
    user: CurrentUser,
) -> Session:
    """Pausa/reanuda/finaliza una sesión."""
    return await repo.update_status(session_id, body.status, caller_oid=user.oid)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    repo: SessionRepoDep,
    user: CurrentUser,
) -> None:
    """Elimina una sesión con sus mensajes (cascade)."""
    await repo.delete(session_id, caller_oid=user.oid)


# ===========================================================================
# Messages
# ===========================================================================


@router.get("/{session_id}/messages", response_model=list[Message])
async def list_messages(
    session_id: str,
    repo: SessionRepoDep,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[Message]:
    """Mensajes de la sesión en orden cronológico ascendente."""
    return await repo.list_messages(
        session_id, caller_oid=user.oid, limit=limit, offset=offset
    )
