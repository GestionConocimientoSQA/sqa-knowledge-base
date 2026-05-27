"""Contrato común de los extractores de documentos (Fase 4.3).

Un extractor toma `bytes` de un archivo + su nombre (para la extensión)
y devuelve un `ExtractedDocument`: texto plano completo + secciones
estructuradas. El modo C de ingesta usa esto para reemplazar el texto
crudo que hoy pega el usuario.

`ExtractedSection` es deliberadamente independiente de
`rag.chunker.Section` para no acoplar `documents/` a `rag/`. El caller
(endpoint de ingesta) mapea uno a otro — son dos LOC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ExtractedSection:
    """Una sección detectada en el documento (heading + contenido)."""

    title: str
    content: str


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    """Resultado de un extractor."""

    text: str
    """Texto plano completo del documento (todas las secciones unidas)."""
    sections: tuple[ExtractedSection, ...] = field(default_factory=tuple)
    """Secciones estructuradas. Puede quedar vacío si el formato no expone
    estructura (p. ej. PDF sin headings claros) — en ese caso `text` trae
    todo y el chunker hace fallback a estrategia semántica."""
    page_count: int = 0
    """Páginas/slides/hojas detectadas. 0 si no aplica."""

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


@runtime_checkable
class DocumentExtractor(Protocol):
    """Extrae texto + estructura de un archivo. Implementaciones:
    `DocxExtractor`, `PptxExtractor`, `PdfExtractor`, `XlsxExtractor`."""

    @property
    def extensions(self) -> tuple[str, ...]:
        """Extensiones soportadas, sin punto (`('docx',)`)."""
        ...

    def extract(self, data: bytes) -> ExtractedDocument: ...
