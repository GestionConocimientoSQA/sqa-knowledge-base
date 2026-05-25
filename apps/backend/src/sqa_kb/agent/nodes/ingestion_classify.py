"""Nodo ingestion_classify (modo C — primer paso).

Para Fase 2.5 simplificamos: el "documento ingerido" es el texto que el
usuario manda como mensaje (pegado del clipboard o resumen). Fase 4
reemplaza esta entrada con extracción real desde archivo via los
extractors (DocxExtractor, PdfExtractor, etc.) — el resto del flujo
permanece igual.

Pasos:
1. Toma el texto del último mensaje user.
2. Clasifica con LLM (reusa `classify_topic` — el contrato es el mismo).
3. Emite la propuesta + preview del texto.
4. Command(goto=ingestion_traceability) en la misma vuelta.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from langgraph.types import Command

from sqa_kb.agent.state import AgentState
from sqa_kb.agent.templates import render
from sqa_kb.agent.tools import classify_topic
from sqa_kb.ports.gateways import LlmGateway

logger = logging.getLogger(__name__)

NodeFn = Callable[[AgentState], Awaitable[dict[str, Any] | Command]]


PREVIEW_CHARS: int = 280
"""Cuántos caracteres del texto extraído mostrar al usuario para
confirmar visual que es el doc correcto."""


def make_ingestion_classify_node(*, gateway: LlmGateway) -> NodeFn:
    """Factory del clasificador de ingesta."""

    async def ingestion_classify(state: AgentState) -> dict[str, Any] | Command:
        extracted = _last_user_msg(state)
        if not extracted:
            return _ask_for_content(state)

        try:
            classification = await classify_topic(
                gateway,
                topic=_topic_from_text(extracted),
            )
        except Exception as exc:  # noqa: BLE001 — degradar y pedir reintento
            logger.exception("Clasificación de ingesta falló: %s", exc)
            return _emit_classify_error(state)

        preview = _make_preview(extracted)
        text = render(
            "ingestion_classification_proposal.j2",
            classification=classification.model_dump(),
            preview=preview,
        )
        message = _agent_message(state, content=text, stage="classify_ingest")
        return Command(
            goto="ingestion_traceability",
            update={
                "messages": [message],
                "extracted_text": extracted,
                "sections_detected": _approximate_section_count(extracted),
                "suggested_classification": classification,
                "current_stage": "classify_ingest",
                "previous_stage": state.current_stage,
                "needs_user_input": False,
                "awaiting_confirmation": None,
            },
        )

    return ingestion_classify


# ===========================================================================
# Helpers
# ===========================================================================


def _last_user_msg(state: AgentState) -> str:
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                return content.strip()
    return ""


def _topic_from_text(text: str, *, max_chars: int = 280) -> str:
    """Para que `classify_topic` funcione le pasamos los primeros chars del
    texto como "topic". El clasificador lee el JSON del LLM y devuelve la
    categoría/tipo igual."""
    snippet = text.strip().replace("\n", " ")
    return snippet[:max_chars] if len(snippet) > max_chars else snippet


def _make_preview(text: str) -> str:
    """Recorta a PREVIEW_CHARS con elipsis si trunca."""
    cleaned = text.strip()
    if len(cleaned) <= PREVIEW_CHARS:
        return cleaned
    return cleaned[:PREVIEW_CHARS].rstrip() + "..."


def _approximate_section_count(text: str) -> int:
    """Heurística: cuenta líneas que arrancan con `#` (markdown) o párrafos
    largos. Fase 4 lo reemplaza con detección real de extracción."""
    md_headers = sum(1 for line in text.splitlines() if line.startswith("#"))
    if md_headers > 0:
        return md_headers
    # Fallback: 1 sección cada ~500 chars.
    return max(1, len(text) // 500)


def _ask_for_content(state: AgentState) -> dict[str, Any]:
    text = (
        "Pegame el contenido del documento que querés ingresar al KB. "
        "Acepto texto plano o markdown — más adelante (Fase 4) vamos a "
        "soportar upload directo de archivos."
    )
    message = _agent_message(state, content=text, stage="classify_ingest")
    return {
        "messages": [message],
        "current_stage": "classify_ingest",
        "previous_stage": state.current_stage,
        "needs_user_input": True,
        "awaiting_confirmation": "mode_choice",  # reusamos para dispatcher loop
    }


def _emit_classify_error(state: AgentState) -> dict[str, Any]:
    text = (
        "No pude clasificar el contenido — probá pegarlo de nuevo o "
        "agregá más contexto."
    )
    message = _agent_message(state, content=text, stage="classify_ingest")
    return {
        "messages": [message],
        "current_stage": "classify_ingest",
        "previous_stage": state.current_stage,
        "needs_user_input": True,
        "awaiting_confirmation": "mode_choice",
        "last_error": "classify_failed",
    }


def _agent_message(
    state: AgentState, *, content: str, stage: str
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": f"msg-ic-{state.session_id}-{len(state.messages)}",
        "role": "agent",
        "content": content,
        "stage": stage,
        "status": "complete",
        "started_at": now,
        "ended_at": now,
    }
