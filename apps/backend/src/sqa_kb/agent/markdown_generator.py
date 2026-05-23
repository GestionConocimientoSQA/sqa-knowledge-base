"""Markdown generator — placeholder de Fase 2.4.

Renderiza el documento final en Markdown usando el template
`markdown_document.j2`. Fase 4 reemplaza este módulo con generadores
multi-formato (DOCX, PPTX, PDF, XLSX) sin cambiar la interfaz pública.

Slug builder: `[TIPO]-[topic-slug]-[YYYY-MM-DD]` — espejo del agente
actual y validado por el regex de `domain.entities.Slug`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from sqa_kb.agent.state import AgentState
from sqa_kb.agent.templates import render

# ===========================================================================
# Slug
# ===========================================================================


def _slugify_topic(topic: str, *, max_words: int = 4) -> str:
    """Reduce el topic a kebab-case ASCII apto para filename.

    - Quita acentos por mapeo simple (no unicodedata para no acoplarse a
      la lib externa — los topics SQA son español neutro corto).
    - Conserva solo `[A-Za-z0-9-]`.
    - Toma las primeras `max_words` palabras significativas.
    - Cae a 'sin-topic' si el resultado queda vacío.
    """
    accent_map = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
    cleaned = topic.translate(accent_map).lower()
    cleaned = re.sub(r"[^a-z0-9\s-]", "", cleaned)
    words = [w for w in cleaned.split() if w]
    if not words:
        return "sin-topic"
    return "-".join(words[:max_words])


def build_document_id(*, document_type: str, topic: str, fecha: datetime) -> str:
    """Devuelve un ID que matchea el regex `Slug` del dominio.

    Formato: `[TIPO]-[topic-slug]-[YYYY-MM-DD]`. Ejemplo:
    `MTEC-flaky-tests-2026-05-23`.
    """
    slug = _slugify_topic(topic)
    return f"{document_type}-{slug}-{fecha.strftime('%Y-%m-%d')}"


# ===========================================================================
# Renderer
# ===========================================================================


@dataclass(frozen=True, slots=True)
class GeneratedDocument:
    """Output del generator. `content` es el markdown listo para persistir
    en Blob (o en local en Fase 2.4)."""

    document_id: str
    title: str
    content: str
    format: str  # "MD" en Fase 2.4. Fase 4: DOCX, PPTX, PDF, XLSX.
    fecha: datetime
    is_anonymized: bool


def render_markdown_document(
    state: AgentState, *, now: datetime | None = None
) -> GeneratedDocument:
    """Construye el documento final a partir del state acumulado.

    Lanza `ValueError` si el state no tiene clasificación o topic — el
    nodo `generation` valida antes de llamar acá.
    """
    if state.classification is None:
        raise ValueError("classification ausente — no se puede generar")
    if not state.topic:
        raise ValueError("topic vacío — no se puede generar")

    fecha = now or datetime.now(UTC)
    title = _titlecase_topic(state.topic)
    document_type = str(state.classification.document_type)
    category = str(state.classification.category)
    document_id = build_document_id(
        document_type=document_type, topic=state.topic, fecha=fecha
    )
    content = render(
        "markdown_document.j2",
        title=title,
        category=category,
        document_type=document_type,
        version="1.0",
        fecha=fecha.strftime("%Y-%m-%d"),
        author_name=state.user_name,
        author_role=state.user_role,
        topic=state.topic,
        free_capture_blocks=state.free_capture_blocks,
        deep_dive_qa=state.deep_dive_qa,
        is_anonymized=bool(state.is_reusable_content),
    )
    return GeneratedDocument(
        document_id=document_id,
        title=title,
        content=content,
        format="MD",
        fecha=fecha,
        is_anonymized=bool(state.is_reusable_content),
    )


def _titlecase_topic(topic: str) -> str:
    """Capitaliza primera letra y deja el resto como está. No usamos
    `.title()` porque rompe siglas (CI/CD, API, etc.)."""
    if not topic:
        return ""
    return topic[0].upper() + topic[1:]
