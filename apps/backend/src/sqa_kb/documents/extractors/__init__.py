"""Extractores de documentos por formato (Fase 4.3).

Cada extractor implementa `DocumentExtractor` (ver `base.py`): recibe
`bytes` y devuelve un `ExtractedDocument` (texto + secciones). El
`ExtractorDispatcher` elige el correcto según la extensión del archivo.
"""

from sqa_kb.documents.extractors.base import (
    DocumentExtractor,
    ExtractedDocument,
    ExtractedSection,
)
from sqa_kb.documents.extractors.dispatcher import (
    ExtractorDispatcher,
    UnsupportedFormatError,
)

__all__ = [
    "DocumentExtractor",
    "ExtractedDocument",
    "ExtractedSection",
    "ExtractorDispatcher",
    "UnsupportedFormatError",
]
