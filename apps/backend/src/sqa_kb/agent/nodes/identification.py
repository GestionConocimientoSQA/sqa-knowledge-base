"""Nodo identification (ETAPA 1, modo captura).

Flujo:
1. Extrae el `topic` del último mensaje user (heurística simple — el LLM
   no agrega valor para topic extraction de un solo mensaje).
2. `search_kb(topic)` → lista de documentos similares.
3. `classify_topic(topic, history)` → carpeta + tipo + confidence.
4. Si hay match cercano (`distance <= DUPLICATE_THRESHOLD`):
   → render `duplicate_found.j2`, espera `update_decision`.
   Si no: → render `classification_proposal.j2`, espera `classification`.

Salida (partial state update):
- `topic`, `classification`, `existing_documents`
- `messages`: el mensaje del agente con la propuesta
- `current_stage`, `previous_stage`
- `needs_user_input=True`, `awaiting_confirmation`

Diseño:
- LLM solo se usa en `classify_topic` — esta función vive en `tools.py`
  con tests propios.
- `search_kb` es stub en 2.3 (full-text), Fase 3 lo cambia a vector.
- El threshold de duplicate (`0.55` por ROADMAP §16) es constante del
  módulo para que tests/admin lo ajusten sin tocar el nodo.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqa_kb.agent.state import AgentState
from sqa_kb.agent.templates import render
from sqa_kb.agent.tools import classify_topic, search_kb
from sqa_kb.ports.gateways import LlmGateway
from sqa_kb.ports.repositories import DocumentRepository

NodeFn = Callable[[AgentState], Awaitable[dict[str, Any]]]


DUPLICATE_THRESHOLD: float = 0.55
"""Si el doc más cercano tiene `distance <= 0.55`, dispara el workflow
de update/complement. Valor del §16 del ROADMAP."""

MAX_KB_RESULTS: int = 3
"""Top-k del search inicial. Más alto satura el prompt; más bajo pierde
contexto. 3 es el sweet spot del ROADMAP."""


def make_identification_node(
    *,
    gateway: LlmGateway,
    document_repo: DocumentRepository,
) -> NodeFn:
    """Factory que captura gateway + repo en closure.

    Recibimos los puertos (no implementaciones concretas) para que `graph.py`
    inyecte real o fake según el contexto.
    """

    async def identification(state: AgentState) -> dict[str, Any]:
        topic = _extract_topic(state)
        if not topic:
            return _ask_for_topic(state)

        existing = await search_kb(
            document_repo, query=topic, top_k=MAX_KB_RESULTS
        )
        classification = await classify_topic(
            gateway,
            topic=topic,
            # Pasamos los últimos mensajes user como contexto del clasificador.
            history=_recent_user_history(state, limit=5),
        )

        nearest_distance = existing[0].distance if existing else float("inf")
        if nearest_distance <= DUPLICATE_THRESHOLD:
            text = render(
                "duplicate_found.j2",
                topic=topic,
                existing=[doc.model_dump() for doc in existing],
            )
            awaiting = "update_decision"
        else:
            text = render(
                "classification_proposal.j2",
                topic=topic,
                classification=classification.model_dump(),
            )
            awaiting = "classification"

        message = {
            "id": f"msg-id-{state.session_id}-{len(state.messages)}",
            "role": "agent",
            "content": text,
            "stage": "ETAPA_1",
            "status": "complete",
            "started_at": datetime.now(UTC).isoformat(),
            "ended_at": datetime.now(UTC).isoformat(),
            "classification": classification.model_dump(),
        }
        return {
            "topic": topic,
            "classification": classification,
            "existing_documents": existing,
            "messages": [message],
            "current_stage": "ETAPA_1",
            "previous_stage": state.current_stage,
            "needs_user_input": True,
            "awaiting_confirmation": awaiting,
        }

    return identification


# ===========================================================================
# Helpers
# ===========================================================================


def _extract_topic(state: AgentState) -> str:
    """Topic = último mensaje user. En 2.3 es así de simple porque la UI
    pide al usuario el topic con prompt explícito (el saludo de welcome).
    Mejoras futuras: usar el LLM para extraer topic de conversación
    libre cuando sumemos free-form capture."""
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content.strip()
    return ""


def _recent_user_history(state: AgentState, *, limit: int) -> list:
    """Últimos N mensajes user/agent en formato `ChatMessage` para el LLM."""
    from sqa_kb.ports.gateways import ChatMessage

    out: list[ChatMessage] = []
    for msg in state.messages[-limit:]:
        role = msg.get("role")
        if role not in ("user", "agent"):
            continue
        # Mapeo `agent` (nuestro nombre) → `assistant` (formato Anthropic).
        anthropic_role = "assistant" if role == "agent" else "user"
        out.append(
            ChatMessage(
                role=anthropic_role,
                content=str(msg.get("content", "")),
            )
        )
    return out


def _ask_for_topic(state: AgentState) -> dict[str, Any]:
    """Edge case: identification se ejecutó sin que el user mande nada.
    Caemos al "decime el topic" sin tocar LLM ni KB."""
    text = "Contame en una frase de qué querés capturar."
    message = {
        "id": f"msg-id-ask-{state.session_id}",
        "role": "agent",
        "content": text,
        "stage": "ETAPA_1",
        "status": "complete",
        "started_at": datetime.now(UTC).isoformat(),
        "ended_at": datetime.now(UTC).isoformat(),
    }
    return {
        "messages": [message],
        "current_stage": "ETAPA_1",
        "previous_stage": state.current_stage,
        "needs_user_input": True,
        "awaiting_confirmation": "topic",
    }
