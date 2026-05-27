"""Generadores de documentos por formato (Fase 4).

Cada generador implementa el Protocol `DocumentGenerator` (ver `base.py`):
recibe un `DocumentContent` y devuelve `bytes` del archivo + su MIME y
extensión. El caller decide qué hacer con los bytes (subir a Blob,
devolver en la response HTTP, etc.).
"""

from sqa_kb.documents.generators.base import DocumentGenerator, GeneratedFile

__all__ = ["DocumentGenerator", "GeneratedFile"]
