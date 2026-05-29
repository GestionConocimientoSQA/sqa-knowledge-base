"""Dispatcher de extractores por extensión (Fase 4.3).

Elige el `DocumentExtractor` adecuado según la extensión del archivo.
Registro estático de los 4 extractores soportados; agregar uno nuevo es
sumarlo a `_EXTRACTORS`.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from sqa_kb.documents.extractors.base import DocumentExtractor, ExtractedDocument
from sqa_kb.documents.extractors.docx import DocxExtractor
from sqa_kb.documents.extractors.markdown import MarkdownExtractor
from sqa_kb.documents.extractors.pdf import PdfExtractor
from sqa_kb.documents.extractors.pptx import PptxExtractor
from sqa_kb.documents.extractors.xlsx import XlsxExtractor


class UnsupportedFormatError(ValueError):
    """El archivo tiene una extensión sin extractor registrado."""


def _normalize_extension(filename: str) -> str:
    """Extrae la extensión en minúsculas sin punto. `''` si no hay."""
    suffix = PurePosixPath(filename).suffix.lower()
    return suffix[1:] if suffix.startswith(".") else suffix


class ExtractorDispatcher:
    """Resuelve y ejecuta el extractor correcto por extensión."""

    def __init__(self, extractors: list[DocumentExtractor] | None = None) -> None:
        self._extractors: list[DocumentExtractor] = extractors or [
            DocxExtractor(),
            PptxExtractor(),
            PdfExtractor(),
            XlsxExtractor(),
            MarkdownExtractor(),
        ]
        # Mapa extensión → extractor (la última registrada gana si colisionan).
        self._by_ext: dict[str, DocumentExtractor] = {}
        for ext_handler in self._extractors:
            for ext in ext_handler.extensions:
                self._by_ext[ext] = ext_handler

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_ext))

    def supports(self, filename: str) -> bool:
        return _normalize_extension(filename) in self._by_ext

    def extractor_for(self, filename: str) -> DocumentExtractor:
        ext = _normalize_extension(filename)
        handler = self._by_ext.get(ext)
        if handler is None:
            raise UnsupportedFormatError(
                f"Formato no soportado: {ext or '(sin extensión)'!r}. "
                f"Soportados: {', '.join(self.supported_extensions)}."
            )
        return handler

    def extract(self, filename: str, data: bytes) -> ExtractedDocument:
        """Elige el extractor por extensión de `filename` y procesa `data`."""
        return self.extractor_for(filename).extract(data)
