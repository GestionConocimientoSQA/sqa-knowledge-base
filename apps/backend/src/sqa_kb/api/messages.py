"""Endpoint de streaming del agente — Fase 2.6.

`POST /sessions/{session_id}/messages` recibe un mensaje del usuario y
devuelve un `text/event-stream` con los 14 tipos de eventos del §15.2.

Diseño:
- IDOR enforcement por `SessionRepository.get(session_id, caller_oid)`.
- Si el usuario reconecta, manda `Last-Event-ID: N` y el orchestrator
  replaya los eventos `> N` antes de retomar.
- Cancellation: cuando el cliente cierra la conexión, `StreamingResponse`
  cancela el generator. El orchestrator captura `CancelledError` y
  corta limpio sin emitir más eventos.

Listar mensajes históricos sigue siendo `GET /sessions/{id}/messages`
(en `api/sessions.py`, 1B.5) — no lo tocamos.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from sqa_kb.api.dependencies import (
    AgentGraphDep,
    CurrentUser,
    SessionRepoDep,
    SseBufferDep,
)
from sqa_kb.api.sse import SseOrchestrator
from sqa_kb.domain.errors import NotFoundError

router = APIRouter(tags=["messages"], prefix="/sessions")


class SendMessageBody(BaseModel):
    """Body del POST. `attachments` reservado para 2.7+ (upload separado)."""

    content: str = Field(
        min_length=1,
        max_length=20000,
        description="Texto del usuario (1-20k chars).",
    )
    attachments: list[str] = Field(
        default_factory=list, description="IDs de attachments ya subidos."
    )


@router.post(
    "/{session_id}/messages",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Stream SSE con eventos del agente",
            "content": {"text/event-stream": {}},
        },
        404: {"description": "Sesión no existe o no es del usuario actual"},
    },
)
async def send_message(
    session_id: str,
    body: SendMessageBody,
    request: Request,
    user: CurrentUser,
    sessions: SessionRepoDep,
    graph: AgentGraphDep,
    buffer: SseBufferDep,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """Envía un mensaje del usuario y abre un stream SSE.

    IDOR: la sesión se verifica contra `caller_oid` ANTES de tocar el grafo.
    """
    session = await sessions.get(session_id, caller_oid=user.oid)
    if session is None:
        raise NotFoundError(f"Sesión {session_id} no encontrada")

    parsed_last_id = _parse_last_event_id(last_event_id)
    user_message = _build_user_message(body.content)

    orchestrator = SseOrchestrator(graph=graph, buffer=buffer)
    generator = orchestrator.run(
        session_id=session_id,
        user_message=user_message,
        last_event_id=parsed_last_id,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            # Desactiva buffering en proxies (nginx, varnish) — crítico
            # para que los eventos lleguen al cliente sin esperar al cierre.
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ===========================================================================
# Helpers
# ===========================================================================


def _parse_last_event_id(raw: str | None) -> int | None:
    """Parsea el header `Last-Event-ID` defensivamente.

    Si el cliente manda algo no-numérico, lo ignoramos (en vez de 400)
    para que el stream arranque limpio en lugar de fallar la conexión.
    """
    if raw is None or not raw.strip():
        return None
    try:
        return int(raw.strip())
    except ValueError:
        return None


def _build_user_message(content: str) -> dict[str, object]:
    """Construye el dict de mensaje en el shape que el grafo espera.

    Mismo schema que los nodos producen para sus mensajes — así el
    state.messages es homogéneo cuando se persiste.
    """
    from datetime import UTC, datetime
    from uuid import uuid4

    now = datetime.now(UTC).isoformat()
    return {
        "id": f"msg-user-{uuid4().hex[:12]}",
        "role": "user",
        "content": content,
        "stage": None,
        "status": "complete",
        "started_at": now,
        "ended_at": now,
    }
