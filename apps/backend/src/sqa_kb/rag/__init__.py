"""Subsistema RAG — Fase 3.

Composición:
- `chunker.py`: `Chunker` con 4 estrategias (semantic / by_steps /
  hierarchical / per_slide) configurables por tipo de documento.
- `context_header.py`: formato del header contextual prefijado a cada
  chunk antes de generar embedding (no se almacena duplicado).
- `indexer.py` (Fase 3.2): orquesta chunk → embed → bulk insert.
- `retriever.py` (Fase 3.3): vector search con boost autoritativos.
- `hybrid.py` (Fase 3.4): combina vector + full-text 70/30.
"""

from sqa_kb.rag.chunker import (
    CHUNK_CONFIG,
    Chunk,
    ChunkConfig,
    Chunker,
    Section,
)
from sqa_kb.rag.context_header import format_context_header
from sqa_kb.rag.indexer import (
    DEFAULT_EMBED_BATCH_SIZE,
    Indexer,
    IndexerResult,
    index_document_background,
)

__all__ = [
    "CHUNK_CONFIG",
    "DEFAULT_EMBED_BATCH_SIZE",
    "Chunk",
    "ChunkConfig",
    "Chunker",
    "Indexer",
    "IndexerResult",
    "Section",
    "format_context_header",
    "index_document_background",
]
