"""Nodo free_capture (ETAPA 2).

Doble responsabilidad por turno:
1. **Primera entrada** (vengo de identification, awaiting=classification):
   Procesa la confirmación del usuario sobre la clasificación propuesta.
   Si confirma → emite el prompt de captura libre.
   Si rechaza → marca el tema para re-clasificación (futuro: 2.5).

2. **Entradas siguientes** (awaiting=free_capture_more):
   El usuario respondió al prompt de captura. Agrega su mensaje a
   `free_capture_blocks` y avanza a ETAPA 3 (deep_dive).

Se simplifica para 2.4: una sola vuelta de captura libre. Iteraciones
extras (usuario sigue añadiendo más bloques) se cubren en 2.5+.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from langgraph.types import Command

from sqa_kb.agent.state import AgentState
from sqa_kb.agent.templates import render

NodeFn = Callable[[AgentState], Awaitable[dict[str, Any] | Command]]


def make_free_capture_node() -> NodeFn:
    """Factory del nodo free_capture. Sin dependencias externas."""

    async def free_capture(state: AgentState) -> dict[str, Any]:
        last_user = _last_user_msg(state)
        if last_user is None:
            # Edge: el dispatcher nos llevó acá sin que el user respondiera.
            # Pedimos input.
            return _ask_again(state)

        # Si veníamos de la propuesta de clasificación, este turno es la
        # respuesta del usuario al "¿confirmás?". Lo interpretamos simple:
        # cualquier respuesta NO negativa cuenta como confirmación.
        if state.awaiting_confirmation == "classification":
            return _emit_capture_prompt(state)

        # Si venimos pidiendo más captura, este turno es contenido nuevo.
        return _store_block_and_advance(state, last_user)

    return free_capture


# ===========================================================================
# Helpers
# ===========================================================================


def _last_user_msg(state: AgentState) -> str | None:
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            return content if isinstance(content, str) else None
    return None


def _emit_capture_prompt(state: AgentState) -> dict[str, Any]:
    """Confirmó la clasificación → pide la captura libre."""
    assert state.classification is not None  # invariante del dispatcher

    text = render(
        "free_capture_prompt.j2",
        topic=state.topic or "",
        classification=state.classification.model_dump(),
    )
    message = _agent_message(state, content=text, stage="ETAPA_2")
    return {
        "messages": [message],
        "current_stage": "ETAPA_2",
        "previous_stage": state.current_stage,
        "classification_confirmed": True,
        "needs_user_input": True,
        "awaiting_confirmation": "free_capture_more",
    }


def _store_block_and_advance(state: AgentState, block: str) -> Command:
    """Guarda el bloque y delega a deep_dive en la misma vuelta para que
    el usuario reciba directamente las preguntas dirigidas (sin tener que
    mandar un mensaje sentinel).
    """
    cleaned = block.strip()
    new_blocks = [*state.free_capture_blocks, cleaned] if cleaned else list(
        state.free_capture_blocks
    )
    ack = (
        "Anoté lo que me contaste. Voy a hacerte un par de preguntas "
        "más específicas para terminar de armar el documento."
    )
    message = _agent_message(state, content=ack, stage="ETAPA_2")
    return Command(
        goto="deep_dive",
        update={
            "messages": [message],
            "free_capture_blocks": new_blocks,
            "current_stage": "ETAPA_2",
            "previous_stage": state.current_stage,
            "needs_user_input": False,
            "awaiting_confirmation": None,
        },
    )


def _ask_again(state: AgentState) -> dict[str, Any]:
    text = "Decime con tus palabras lo que querés capturar."
    message = _agent_message(state, content=text, stage="ETAPA_2")
    return {
        "messages": [message],
        "current_stage": "ETAPA_2",
        "previous_stage": state.current_stage,
        "needs_user_input": True,
        "awaiting_confirmation": "free_capture_more",
    }


def _agent_message(state: AgentState, *, content: str, stage: str) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": f"msg-fc-{state.session_id}-{len(state.messages)}",
        "role": "agent",
        "content": content,
        "stage": stage,
        "status": "complete",
        "started_at": now,
        "ended_at": now,
    }
