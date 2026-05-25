"""Nodo index_ingestion (modo C — paso final).

Persiste:
- `Document` en el repo de documentos (igual que generation en modo A).
- `IngestionItem` en el repo de ingesta (tracking del workflow).
- **Chunks RAG (Fase 3.6)**: si hay `indexer` cableado, dispara
  `index_document_background` con el `extracted_text` como contenido.

Diferencias con `generation` (modo A):
- El texto NO se genera con LLM — viene del usuario / extractor.
- NO se scorea (Fase 5+ podría agregar scoring también acá).
- Sí persiste la `Traceability` como metadata.

Si falla la persistencia → emite disculpa con last_error y termina.
Si falla la indexación → swallow + log (no bloqueante; reintentable con
`scripts/reindex_all.py`).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqa_kb.agent.markdown_generator import build_document_id
from sqa_kb.agent.state import AgentState
from sqa_kb.domain.entities import Document, IngestionItem
from sqa_kb.domain.value_objects import (
    CategoryCode,
    DocStatus,
    DocTypeCode,
    IngestionStatus,
)
from sqa_kb.ports.repositories import DocumentRepository, IngestionRepository
from sqa_kb.rag.chunker import Section
from sqa_kb.rag.indexer import Indexer, index_document_background

logger = logging.getLogger(__name__)

NodeFn = Callable[[AgentState], Awaitable[dict[str, Any]]]


def make_index_ingestion_node(
    *,
    document_repo: DocumentRepository,
    ingestion_repo: IngestionRepository,
    indexer: Indexer | None = None,
) -> NodeFn:
    """Factory que captura ambos repos.

    Args:
        document_repo: para persistir el Document indexado.
        ingestion_repo: para el tracking del workflow C.
        indexer: opcional (Fase 3.6). Si está, indexa el doc recién
            creado en `document_chunks`. Si `None`, no-op (back-compat).
    """

    async def index_ingestion(state: AgentState) -> dict[str, Any]:
        if state.suggested_classification is None or state.extracted_text is None:
            return _error(state, "Faltan datos de clasificación o texto.")
        if state.traceability is None:
            return _error(state, "Falta trazabilidad.")

        now = datetime.now(UTC)
        classification = state.suggested_classification
        title = _title_from_text(state.extracted_text)
        document_id = build_document_id(
            document_type=str(classification.document_type),
            topic=title,
            fecha=now,
        )

        try:
            document = await _create_document(
                document_repo,
                state=state,
                document_id=document_id,
                title=title,
                now=now,
            )
            ingestion_item = await _create_ingestion_item(
                ingestion_repo,
                state=state,
                document_id=document.id,
                now=now,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Persistencia de ingesta falló: %s", exc)
            return _error(
                state,
                "Recibí los datos pero no pude persistir el documento.",
            )

        # Hook RAG (Fase 3.6): indexa el texto extraído. El extractor de
        # Fase 4 traerá secciones reales; mientras tanto pasamos el texto
        # como una sola Section con el title derivado del texto.
        if indexer is not None:
            await index_document_background(
                indexer,
                document.id,
                sections=[Section(title=title, content=state.extracted_text)],
            )

        text = (
            f"Listo. Indexé el documento **{document.titulo}** "
            f"(ID `{document.id}`) en la carpeta {document.carpeta} "
            f"como tipo {document.tipo}. "
            f"Aprobado por **{state.traceability.approved_by}** "
            f"el {state.traceability.approval_date}. "
            f"Item de ingesta: `{ingestion_item.id}`."
        )
        message = _agent_message(state, content=text, stage="index_ingestion")
        return {
            "messages": [message],
            "generated_document_id": document.id,
            "ingestion_item_id": ingestion_item.id,
            "current_stage": "index_ingestion",
            "previous_stage": state.current_stage,
            "needs_user_input": False,
            "awaiting_confirmation": None,
        }

    return index_ingestion


# ===========================================================================
# Helpers
# ===========================================================================


async def _create_document(
    repo: DocumentRepository,
    *,
    state: AgentState,
    document_id: str,
    title: str,
    now: datetime,
) -> Document:
    assert state.suggested_classification is not None
    document = Document(
        id=document_id,
        titulo=title,
        carpeta=CategoryCode(str(state.suggested_classification.category)),
        tipo=DocTypeCode(str(state.suggested_classification.document_type)),
        autoritativo=False,
        estado=DocStatus.VIGENTE,
        autor_oid=state.user_id,
        autor_name=state.user_name,
        autor_role=state.user_role or "no especificado",
        fecha=now,
        revision=now,
        # `version` no admite None (NonEmptyStr) — caemos a "1.0" si el
        # usuario no especificó.
        version=(state.traceability.source_version if state.traceability else None) or "1.0",
        formato="MD",
        anonimizado=False,
        aprobador_name=state.traceability.approved_by if state.traceability else None,
        fecha_aprobacion=_parse_iso_date_safe(
            state.traceability.approval_date if state.traceability else None
        ),
        tags=[],
    )
    return await repo.create(document)


async def _create_ingestion_item(
    repo: IngestionRepository,
    *,
    state: AgentState,
    document_id: str,
    now: datetime,
) -> IngestionItem:
    assert state.suggested_classification is not None
    assert state.traceability is not None
    item = IngestionItem(
        id=f"ing-{uuid.uuid4().hex[:8]}",
        filename=f"{document_id}.md",
        size_bytes=len((state.extracted_text or "").encode("utf-8")),
        paginas=max(1, (state.sections_detected or 1)),
        carpeta_sugerida=CategoryCode(str(state.suggested_classification.category)),
        tipo_sugerido=DocTypeCode(str(state.suggested_classification.document_type)),
        aprobador_oid=None,
        aprobador_name=state.traceability.approved_by,
        fecha_aprobacion=_parse_iso_date_safe(state.traceability.approval_date),
        fuente_original=state.traceability.source_origin,
        version=state.traceability.source_version or "",
        status=IngestionStatus.LISTO,
        uploaded_by_oid=state.user_id,
        uploaded_at=now,
        blob_path=None,
    )
    return await repo.create(item)


def _title_from_text(text: str, *, max_words: int = 8) -> str:
    """Toma las primeras N palabras como título estimado.

    Si el texto arranca con un `# heading` markdown, usa eso.
    """
    stripped = text.strip()
    first_line = stripped.splitlines()[0] if stripped else ""
    if first_line.startswith("#"):
        return first_line.lstrip("#").strip() or "Documento sin título"
    words = stripped.split()
    if not words:
        return "Documento sin título"
    return " ".join(words[:max_words])


def _parse_iso_date_safe(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).replace(tzinfo=UTC)
    except ValueError:
        return None


def _error(state: AgentState, reason: str) -> dict[str, Any]:
    message = _agent_message(state, content=reason, stage="index_ingestion")
    return {
        "messages": [message],
        "current_stage": "index_ingestion",
        "previous_stage": state.current_stage,
        "needs_user_input": False,
        "awaiting_confirmation": None,
        "last_error": reason,
    }


def _agent_message(
    state: AgentState, *, content: str, stage: str
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": f"msg-ii-{state.session_id}-{len(state.messages)}",
        "role": "agent",
        "content": content,
        "stage": stage,
        "status": "complete",
        "started_at": now,
        "ended_at": now,
    }
