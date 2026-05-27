"""DTOs de datos de documento (Fase 4).

`DocumentContent` es el input común de TODOS los generadores (DOCX,
PPTX, XLSX, PDF, Markdown). Es un objeto de datos puro — no sabe nada
del `AgentState` ni de SQLAlchemy. El caller (agente o endpoint)
construye el `DocumentContent` desde su fuente y se lo pasa al generador.

Esto desacopla:
- el "qué contiene el documento" (este DTO),
- del "cómo se genera el archivo" (cada generador),
- del "de dónde salen los datos" (state del agente, ingesta, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class QaPair:
    """Una pregunta + respuesta de la fase deep-dive (ETAPA 3)."""

    question: str
    answer: str


@dataclass(frozen=True, slots=True)
class DocumentContent:
    """Datos puros de un documento a generar — input de los generadores.

    Inmutable: los generadores no lo mutan, solo lo leen. Construir uno
    nuevo si hace falta variar algo (p. ej. tras anonimizar).
    """

    document_id: str
    """ID/slug del documento (`[TIPO]-[tema]-[YYYY-MM-DD]`)."""
    title: str
    category: str
    """Código de carpeta (PROC, TEC, ...)."""
    document_type: str
    """Código de tipo (POL, PROC, GUIA, ...)."""
    version: str
    fecha: datetime
    author_name: str
    author_role: str | None
    topic: str
    body_blocks: tuple[str, ...] = ()
    """Bloques de contenido libre (free_capture en modo A)."""
    qa_pairs: tuple[QaPair, ...] = ()
    """Precisiones del deep-dive (ETAPA 3). Vacío si no hubo."""
    is_anonymized: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)

    def with_body(self, blocks: tuple[str, ...]) -> DocumentContent:
        """Devuelve una copia con `body_blocks` reemplazado (p. ej. tras
        anonimizar el contenido). No muta el original."""
        return DocumentContent(
            document_id=self.document_id,
            title=self.title,
            category=self.category,
            document_type=self.document_type,
            version=self.version,
            fecha=self.fecha,
            author_name=self.author_name,
            author_role=self.author_role,
            topic=self.topic,
            body_blocks=blocks,
            qa_pairs=self.qa_pairs,
            is_anonymized=self.is_anonymized,
            tags=self.tags,
        )
