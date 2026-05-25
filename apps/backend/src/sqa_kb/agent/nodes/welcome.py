"""Nodo welcome (ETAPA 0).

Es el primer nodo del grafo. Emite el saludo inicial usando el template
`welcome.j2` y setea `current_stage` para que el router decida la rama
siguiente según `state.mode`.

Diseño:
- **Sin LLM**: el saludo es plantilla pura — Anthropic no aporta valor acá
  y ahorramos un round-trip + tokens.
- **Idempotente**: si el nodo se re-ejecuta (resume desde checkpoint con
  `messages` ya cargado), no duplica el saludo.
- **Marca `needs_user_input=True`**: el orquestador SSE (2.6) lee esto
  para saber que tiene que pausar y esperar.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqa_kb.agent.state import AgentState
from sqa_kb.agent.templates import render

# Type alias para la signature que LangGraph espera.
NodeFn = Callable[[AgentState], Awaitable[dict[str, Any]]]


def make_welcome_node() -> NodeFn:
    """Factory del nodo welcome.

    No tiene dependencias externas (LLM, repos) — pero mantenemos la
    factory por simetría con los demás nodos y para permitir agregar
    deps en el futuro sin cambiar la firma de `graph.py`.
    """

    async def welcome(state: AgentState) -> dict[str, Any]:
        # Idempotencia: si ya hay un mensaje del agente en stage ETAPA_0,
        # significa que welcome ya corrió. Salimos sin emitir de nuevo.
        already_greeted = any(
            m.get("role") == "agent" and m.get("stage") == "ETAPA_0"
            for m in state.messages
        )
        if already_greeted:
            return {"current_stage": "ETAPA_0"}

        text = render("welcome.j2", user_name=state.user_name)
        message = {
            "id": f"msg-welcome-{state.session_id}",
            "role": "agent",
            "content": text,
            "stage": "ETAPA_0",
            "status": "complete",
            "started_at": datetime.now(UTC).isoformat(),
            "ended_at": datetime.now(UTC).isoformat(),
        }
        return {
            "messages": [message],
            "current_stage": "ETAPA_0",
            "previous_stage": state.current_stage,
            "needs_user_input": True,
            "awaiting_confirmation": "mode_choice",
        }

    return welcome
