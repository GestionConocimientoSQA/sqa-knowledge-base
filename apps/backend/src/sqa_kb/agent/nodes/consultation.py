"""Nodo consultation (modo B).

Una sola pregunta por turno:
1. Toma la última pregunta del usuario.
2. Busca chunks en el KB con `search_kb_chunks` (hybrid vector + FTS).
3. Llama al LLM para sintetizar respuesta con citaciones.
4. Emite la respuesta + `awaiting=consult_more` para que el usuario pueda
   seguir preguntando.

Sin chunks → mensaje de "no encontré info" + sugerencia de capturar
(`relevance_level=sin_resultados`).

Diseño:
- Desde Fase 3.5: `search_kb_chunks` devuelve `HybridChunk` reales con
  `content` largo (extraído del indexer). Antes (Fase 2.5) era stub que
  inventaba content desde el titulo.
- LLM call sin cache_control: cada consulta es distinta, no se beneficia
  del prompt caching (sí en Fase 2.6+ cuando agreguemos skills inyectados
  en el system prompt).
- `_classify_relevance` recibe `distance = 1 - score` para mantener la
  semántica del threshold ROADMAP §17.7.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from sqa_kb.agent.state import AgentState
from sqa_kb.agent.templates import render
from sqa_kb.agent.tools import (
    build_citations_from_results,
    search_kb_chunks,
    synthesize_consultation_answer,
)
from sqa_kb.ports.gateways import LlmGateway
from sqa_kb.rag.hybrid_search import HybridChunk, HybridSearcher

logger = logging.getLogger(__name__)

NodeFn = Callable[[AgentState], Awaitable[dict[str, Any]]]

# Threshold de relevancia del retriever real. Espejo de ROADMAP §17.7:
# distance <= 0.55 → alta; 0.55-0.65 → media; > 0.65 → sin_resultados.
# Lo dejamos ligeramente más permisivo (0.5/0.8) porque el hybrid score
# combinado puede ser un poco más alto que el coseno crudo.
HIGH_RELEVANCE_THRESHOLD: float = 0.5
MEDIUM_RELEVANCE_THRESHOLD: float = 0.8

CHUNKS_FOR_SYNTHESIS: int = 5
"""Cuántos chunks alimentar al sintetizador LLM. Más chunks saturan el
context; menos pierden cobertura. 5 es el sweet spot empírico."""


def make_consultation_node(
    *,
    gateway: LlmGateway,
    searcher: HybridSearcher,
) -> NodeFn:
    """Factory que captura gateway + searcher."""

    async def consultation(state: AgentState) -> dict[str, Any]:
        query = _last_user_msg(state)
        if not query:
            return _ask_for_query(state)

        chunks = await search_kb_chunks(
            searcher, query=query, top_k=CHUNKS_FOR_SYNTHESIS
        )

        if not chunks:
            return _emit_no_results(state, query=query)

        # `distance = 1 - score` para reusar la semántica del threshold.
        # El `HybridChunk` ya viene ordenado desc por score, así que el
        # primero es el más cercano.
        nearest_score = chunks[0].score
        nearest_distance = max(0.0, 1.0 - nearest_score)
        relevance = _classify_relevance(nearest_distance)

        chunk_dicts = _hybrid_chunks_to_dicts(chunks)
        try:
            answer = await synthesize_consultation_answer(
                gateway, query=query, chunks=chunk_dicts
            )
        except Exception as exc:  # noqa: BLE001 — degradar a "no pude responder"
            logger.exception("Síntesis LLM falló: %s", exc)
            return _emit_synthesis_error(state, query=query)

        citations = build_citations_from_results(chunk_dicts)
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
    """Clasifica relevancia según `distance = 1 - score_combinado`."""
    if distance <= HIGH_RELEVANCE_THRESHOLD:
        return "alta"
    if distance <= MEDIUM_RELEVANCE_THRESHOLD:
        return "media"
    return "sin_resultados"


def _hybrid_chunks_to_dicts(chunks: Sequence[HybridChunk]) -> list[dict[str, str]]:
    """Convierte `HybridChunk` (DTO del retriever) a dicts que el
    sintetizador y `build_citations_from_results` consumen.

    Mantenemos los dicts como contrato del prompt LLM en `tools.py`
    (no cambiar la firma de `synthesize_consultation_answer` para no
    romper sus tests). Es una capa de adaptación delgada acá.
    """
    out: list[dict[str, str]] = []
    for c in chunks:
        out.append(
            {
                "document_id": c.document_id,
                "filename": c.document_id + ".md",
                "content": c.content,
                "section_title": c.section_title,
                "chunk_id": c.chunk_id,
            }
        )
    return out


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
