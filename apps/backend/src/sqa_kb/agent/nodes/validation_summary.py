"""Nodo validation_summary (ETAPA 4).

Muestra el resumen de lo capturado (topic + clasificación + captura libre
+ deep dive) y espera confirmación del usuario.

Si el usuario confirma → `current_stage` queda en `ETAPA_4` con
`awaiting_confirmation = "summary"`. El dispatcher entra a `generation`
en la próxima vuelta.

Si el usuario rechaza → en 2.4 no manejamos el camino "back to capture";
queda como TODO de 2.5+ (frontend muestra opción de cancelar sesión).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from langgraph.types import Command

from sqa_kb.agent.state import AgentState
from sqa_kb.agent.templates import render

NodeFn = Callable[[AgentState], Awaitable[dict[str, Any] | Command]]


def make_validation_summary_node() -> NodeFn:
    async def validation_summary(state: AgentState) -> dict[str, Any]:
        if state.classification is None:
            return _abort(state, "No hay clasificación todavía — no puedo resumir.")

        if state.awaiting_confirmation == "summary":
            # Vuelta siguiente: usuario respondió al resumen. Lo marcamos
            # validado y avanzamos a ETAPA 4 listo para generación.
            return _accept_and_advance(state)

        # Primera entrada — emitimos el resumen.
        text = render(
            "validation_summary.j2",
            topic=state.topic or "",
            classification=state.classification.model_dump(),
            free_capture_blocks=state.free_capture_blocks,
            deep_dive_qa=state.deep_dive_qa,
            is_reusable_content=state.is_reusable_content,
        )
        message = _agent_message(state, content=text, stage="ETAPA_4")
        return {
            "messages": [message],
            "current_stage": "ETAPA_4",
            "previous_stage": state.current_stage,
            "needs_user_input": True,
            "awaiting_confirmation": "summary",
        }

    return validation_summary


# ===========================================================================
# Helpers
# ===========================================================================


def _accept_and_advance(state: AgentState) -> Command:
    """Validó el resumen → encadena con generation en la misma vuelta."""
    ack = "Genial, genero el documento ahora."
    message = _agent_message(state, content=ack, stage="ETAPA_4")
    return Command(
        goto="generation",
        update={
            "messages": [message],
            "summary_validated": True,
            "current_stage": "ETAPA_4",
            "previous_stage": state.current_stage,
            "needs_user_input": False,
            "awaiting_confirmation": None,
        },
    )


def _abort(state: AgentState, reason: str) -> dict[str, Any]:
    message = _agent_message(state, content=reason, stage="ETAPA_4")
    return {
        "messages": [message],
        "current_stage": "ETAPA_4",
        "previous_stage": state.current_stage,
        "needs_user_input": True,
        "awaiting_confirmation": "error",
        "last_error": reason,
    }


def _agent_message(state: AgentState, *, content: str, stage: str) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": f"msg-vs-{state.session_id}-{len(state.messages)}",
        "role": "agent",
        "content": content,
        "stage": stage,
        "status": "complete",
        "started_at": now,
        "ended_at": now,
    }
