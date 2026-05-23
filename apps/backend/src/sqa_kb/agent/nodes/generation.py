"""Nodo generation (ETAPA 5).

Cadena interna sin pause: render Markdown → score → index. Si llegamos
acá significa que el usuario ya validó el resumen en ETAPA 4.

Pasos:
1. `render_markdown_document` arma el contenido + slug.
2. `index_document`: crea el `Document` en el repo (sin upload a Blob —
   eso es Fase 4 con `blob_path` real; acá lo dejamos `None`).
3. `score_capture` (LLM): calcula 4 dimensiones + value_score.
4. Emite mensaje con link al documento generado + scoring.

Si cualquier paso falla:
- `index_document` rota → guardamos `last_error`, emitimos disculpa.
- `score_capture` falla → indexamos sin scoring (no bloqueante).

El nodo NO marca `needs_user_input` — la sesión queda cerrada (END).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqa_kb.agent.markdown_generator import (
    GeneratedDocument,
    render_markdown_document,
)
from sqa_kb.agent.state import AgentState
from sqa_kb.agent.tools import score_capture
from sqa_kb.domain.entities import Document
from sqa_kb.domain.value_objects import CategoryCode, DocStatus, DocTypeCode
from sqa_kb.ports.gateways import LlmGateway
from sqa_kb.ports.repositories import DocumentRepository

logger = logging.getLogger(__name__)

NodeFn = Callable[[AgentState], Awaitable[dict[str, Any]]]


def make_generation_node(
    *,
    gateway: LlmGateway,
    document_repo: DocumentRepository,
) -> NodeFn:
    """Factory de generation. Necesita gateway (para scoring) y document
    repo (para persistir)."""

    async def generation(state: AgentState) -> dict[str, Any]:
        # Paso 1: render markdown
        try:
            generated = render_markdown_document(state)
        except ValueError as exc:
            logger.exception("Generación falló: %s", exc)
            return _error_message(state, f"No pude generar el documento: {exc}")

        # Paso 2: crear el Document en el repo
        try:
            document = await _create_document(
                document_repo, state=state, generated=generated
            )
        except Exception as exc:  # noqa: BLE001 — el repo puede tirar varias cosas
            logger.exception("Persistencia falló: %s", exc)
            return _error_message(
                state, "Generé el documento pero no pude persistirlo."
            )

        # Paso 3: scoring (no-blocking — si falla seguimos sin score)
        scoring = None
        try:
            scoring = await score_capture(
                gateway,
                document_content=generated.content,
                document_type=str(state.classification.document_type)
                if state.classification
                else "MTEC",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Scoring falló (no bloqueante): %s", exc)

        # Paso 4: mensaje final
        return _success_message(state, document=document, scoring=scoring)

    return generation


# ===========================================================================
# Helpers
# ===========================================================================


async def _create_document(
    repo: DocumentRepository,
    *,
    state: AgentState,
    generated: GeneratedDocument,
) -> Document:
    """Crea el Document en el repo. Asume que classification existe (el
    nodo validó en el llamador)."""
    assert state.classification is not None
    document = Document(
        id=generated.document_id,
        titulo=generated.title,
        carpeta=CategoryCode(str(state.classification.category)),
        tipo=DocTypeCode(str(state.classification.document_type)),
        autoritativo=False,
        estado=DocStatus.GENERADO,
        autor_oid=state.user_id,
        autor_name=state.user_name,
        autor_role=state.user_role or "no especificado",
        fecha=generated.fecha,
        revision=generated.fecha,
        version="1.0",
        formato=generated.format,
        anonimizado=generated.is_anonymized,
        tags=[],
        # blob_path queda None hasta Fase 4 (Azure Blob).
    )
    return await repo.create(document)


def _success_message(
    state: AgentState,
    *,
    document: Document,
    scoring,  # type: ignore[no-untyped-def]  CaptureScoring | None
) -> dict[str, Any]:
    parts = [
        f"Listo. Generé el documento **{document.titulo}** "
        f"con ID `{document.id}` (formato {document.formato}).",
    ]
    if scoring is not None:
        parts.append(
            f"Scoring: especificidad {scoring.specificity}/5, "
            f"profundidad {scoring.depth}/5, "
            f"reutilización {scoring.reusability}/5, "
            f"unicidad {scoring.uniqueness}/5 "
            f"(valor agregado **{scoring.value_score:.1f}/5**)."
        )
    parts.append("Ya quedó en el KB — gracias por capturar.")
    content = "\n\n".join(parts)
    message = _agent_message(state, content=content, stage="ETAPA_5")
    return {
        "messages": [message],
        "generated_document_id": document.id,
        "capture_scoring": scoring,
        "current_stage": "ETAPA_5",
        "previous_stage": state.current_stage,
        "needs_user_input": False,
        "awaiting_confirmation": None,
    }


def _error_message(state: AgentState, reason: str) -> dict[str, Any]:
    message = _agent_message(state, content=reason, stage="ETAPA_5")
    return {
        "messages": [message],
        "current_stage": "ETAPA_5",
        "previous_stage": state.current_stage,
        "needs_user_input": False,
        "awaiting_confirmation": None,
        "last_error": reason,
    }


def _agent_message(state: AgentState, *, content: str, stage: str) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": f"msg-gen-{state.session_id}-{len(state.messages)}",
        "role": "agent",
        "content": content,
        "stage": stage,
        "status": "complete",
        "started_at": now,
        "ended_at": now,
    }
