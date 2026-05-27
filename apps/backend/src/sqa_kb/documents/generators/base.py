"""Contrato común de los generadores de documentos (Fase 4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sqa_kb.documents.models import DocumentContent


@dataclass(frozen=True, slots=True)
class GeneratedFile:
    """Resultado de un generador: bytes + metadata para servir/persistir."""

    filename: str
    """Nombre sugerido con extensión (`MTEC-foo-2026-05-26.docx`)."""
    media_type: str
    """MIME type para la response HTTP / metadata del Blob."""
    data: bytes
    """Contenido binario del archivo."""

    @property
    def size_bytes(self) -> int:
        return len(self.data)


@runtime_checkable
class DocumentGenerator(Protocol):
    """Genera un archivo a partir de un `DocumentContent`.

    Implementaciones: `MarkdownGenerator`, `DocxGenerator`,
    `PptxGenerator`, `XlsxGenerator`, `PdfGenerator`.
    """

    @property
    def extension(self) -> str:
        """Extensión sin punto (`docx`, `pdf`, `md`, ...)."""
        ...

    @property
    def media_type(self) -> str:
        """MIME type del formato."""
        ...

    def generate(self, content: DocumentContent) -> GeneratedFile: ...
