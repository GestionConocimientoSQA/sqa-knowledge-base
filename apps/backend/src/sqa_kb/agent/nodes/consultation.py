"""Nodo consultation (modo B).

Una sola pregunta por turno:
1. Toma la última pregunta del usuario.
2. Busca en el KB (stub full-text de Fase 1; Fase 3 vector).
3. Llama al LLM para sintetizar respuesta con citaciones.
4. Emite la respuesta + `awaiting=consult_more` para que el usuario pueda
   seguir preguntando.

Sin chunks → mensaje de "no encontré info" + sugerencia de capturar
(`relevance_level=sin_resultados`).

Diseño:
- Stub de chunks: usamos `search_kb` que devuelve `ExistingDocument`. Para
  el sintetizador necesitamos algo más rico (con content). En 2.5 usamos
  el `titulo` como content stub — Fase 3 trae chunks vectoriales reales.
- LLM call sin cache_control: cada consulta es distinta, no se beneficia
  del prompt caching (sí en Fase 2.6+ cuando agreguemos skills inyectados
  en el system prompt).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqa_kb.agent.state import AgentState
from sqa_kb.agent.templates import render
from sqa_kb.agent.tools import (
    build_citations_from_results,
    search_kb,
    synthesize_consultation_answer,
)
from sqa_kb.ports.gateways import LlmGateway
from sqa_kb.ports.repositories import DocumentRepository

logger = logging.getLogger(__name__)

NodeFn = Callable[[AgentState], Awaitable[dict[str, Any]]]

# Threshold del retriever stub. Por debajo de 0.5 consideramos match alto;
# entre 0.5 y 0.8 medio; >= 0.8 sin resultados útiles. Fase 3 calibra con
# datos reales.
HIGH_RELEVANCE_THRESHOLD: float = 0.5
MEDIUM_RELEVANCE_THRESHOLD: float = 0.8


def make_consultation_node(
    *,
    gateway: LlmGateway,
    document_repo: DocumentRepository,
) -> NodeFn:
    """Factory que captura gateway + repo."""

    async def consultation(state: AgentState) -> dict[str, Any]:
        query = _last_user_msg(state)
        if not query:
            return _ask_for_query(state)

        existing = await search_kb(document_repo, query=query, top_k=5)

        if not existing:
            return _emit_no_results(state, query=query)

        nearest = existing[0].distance
        relevance = _classify_relevance(nearest)

        chunks = _chunks_from_existing(existing)
        try:
            answer = await synthesize_consultation_answer(
                gateway, query=query, chunks=chunks
            )
        except Exception as exc:  # noqa: BLE001 — degradar a "no pude responder"
            logger.exception("Síntesis LLM falló: %s", exc)
            return _emit_synthesis_error(state, query=query)

        citations = build_citations_from_results(chunks)
        text = render(
            "consultation_answer.j2",
            query=query,
            has_results=True,
            answer=answer,
            citations=[c.model_dump() for c in citations],
            relevance_level=relevance,
        )
        message = _agent_message(state, content=text, stage="consult_search")
        return {
            "messages": [message],
            "current_query": query,
            "citations": list(state.citations) + citations,
            "relevance_level": relevance,
            "current_stage": "consult_search",
            "previous_stage": state.current_stage,
            "needs_user_input": True,
            "awaiting_confirmation": "consult_more",
        }

    return consultation


# ===========================================================================
# Helpers
# ===========================================================================


def _classify_relevance(distance: float) -> str:
    """Clasifica relevancia según `distance` del retriever stub."""
    if distance <= HIGH_RELEVANCE_THRESHOLD:
        return "alta"
    if distance <= MEDIUM_RELEVANCE_THRESHOLD:
        return "media"
    return "sin_resultados"


def _chunks_from_existing(existing: list) -> list[dict[str, str]]:
    """Convierte `ExistingDocument` (stub de search) en chunks aptos para
    el sintetizador. Stub: usa `filename` como contenido — Fase 3 trae
    chunks vectoriales reales con `content` largo."""
    chunks: list[dict[str, str]] = []
    for doc in existing:
        chunks.append(
            {
                "document_id": doc.document_id,
                "filename": doc.filename,
                "content": f"Documento {doc.filename} en {doc.category}.",
                "section_title": "",
                "chunk_id": f"stub-{doc.document_id}",
            }
        )
    return chunks


def _last_user_msg(state: AgentState) -> str:
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                return content.strip()
    return ""


def _ask_for_query(state: AgentState) -> dict[str, Any]:
    """Dispatcher nos llevó sin user msg. Pedimos una pregunta."""
    text = "Decime qué querés consultar."
    message = _agent_message(state, content=text, stage="consult_search")
    return {
        "messages": [message],
        "current_stage": "consult_search",
        "previous_stage": state.current_stage,
        "needs_user_input": True,
        "awaiting_confirmation": "consult_more",
    }


def _emit_no_results(state: AgentState, *, query: str) -> dict[str, Any]:
    text = render(
        "consultation_answer.j2",
        query=query,
        has_results=False,
        answer="",
        citations=[],
        relevance_level="sin_resultados",
    )
    message = _agent_message(state, content=text, stage="consult_search")
    return {
        "messages": [message],
        "current_query": query,
        "relevance_level": "sin_resultados",
        "current_stage": "consult_search",
        "previous_stage": state.current_stage,
        "needs_user_input": True,
        "awaiting_confirmation": "consult_more",
    }


def _emit_synthesis_error(state: AgentState, *, query: str) -> dict[str, Any]:
    text = (
        "Encontré información relacionada pero no pude armar una respuesta "
        "ahora mismo. Probá de nuevo en unos segundos."
    )
    message = _agent_message(state, content=text, stage="consult_search")
    return {
        "messages": [message],
        "current_query": query,
        "current_stage": "consult_search",
        "previous_stage": state.current_stage,
        "needs_user_input": True,
        "awaiting_confirmation": "consult_more",
        "last_error": "synthesis_failed",
    }


def _agent_message(
    state: AgentState, *, content: str, stage: str
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": f"msg-c-{state.session_id}-{len(state.messages)}",
        "role": "agent",
        "content": content,
        "stage": stage,
        "status": "complete",
        "started_at": now,
        "ended_at": now,
    }
