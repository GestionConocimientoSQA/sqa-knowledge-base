"""Indexer — orquesta el pipeline de indexación (Fase 3.2).

Flujo:
1. Lee el `Document` del repo para obtener `tipo`, `carpeta` (necesarios
   para chunker config + header contextual).
2. Llama al `Chunker` con sections + doc_type.
3. Para cada chunk, construye el texto con `format_context_header` y lo
   acumula en un batch.
4. Embedea por sub-batches de tamaño `MAX_BATCH_SIZE` (96 Cohere).
5. Borra chunks viejos del documento si `replace=True` (default).
6. `bulk_insert` los chunks nuevos con sus vectores.
7. Devuelve `IndexerResult` con métricas para audit.

Atomicidad:
- Embedeamos TODOS los chunks antes de tocar la DB. Si el embedder falla
  a mitad, no quedamos en estado inconsistente (los chunks viejos siguen
  ahí).
- El `bulk_insert` corre en una transacción (session_scope). Si la DB
  rechaza, hace rollback.
- El `delete_by_document` previo NO es transaccional con el insert
  intencionalmente — son dos commits porque queremos que el delete
  libere espacio antes (la tabla puede tener millones de filas en Fase 4+).

Background task:
- `index_document_background()` wrap el método para FastAPI
  `BackgroundTasks`. Loggea + swallowea excepciones (las que escapan
  serían silenciadas por FastAPI igual; mejor logging explícito).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqa_kb.domain.entities import DocumentChunk
from sqa_kb.ports.gateways import EmbedderPort
from sqa_kb.ports.repositories import ChunkRepository, DocumentRepository
from sqa_kb.rag.chunker import Chunker, Section
from sqa_kb.rag.context_header import format_context_header

logger = logging.getLogger(__name__)


# Cohere acepta hasta 96 textos por batch (espejo de la constante del adapter).
DEFAULT_EMBED_BATCH_SIZE: int = 96


@dataclass(frozen=True, slots=True)
class IndexerResult:
    """Métricas de una corrida del indexer. Útil para audit + cost tracking."""

    document_id: str
    chunks_created: int
    tokens_embedded: int
    cost_usd: float
    sub_batches: int
    replaced_old_chunks: int
    """Cantidad de chunks viejos borrados antes del insert nuevo."""


class Indexer:
    """Orquesta chunk → embed → bulk insert. Stateless."""

    def __init__(
        self,
        *,
        embedder: EmbedderPort,
        chunk_repo: ChunkRepository,
        document_repo: DocumentRepository,
        chunker: Chunker | None = None,
        batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
    ) -> None:
        self._embedder = embedder
        self._chunk_repo = chunk_repo
        self._document_repo = document_repo
        self._chunker = chunker or Chunker()
        self._batch_size = batch_size

    async def index_document(
        self,
        document_id: str,
        *,
        sections: Sequence[Section],
        text: str | None = None,
        replace: bool = True,
    ) -> IndexerResult:
        """Indexa un documento end-to-end.

        Args:
            document_id: el `Document.id` ya creado en la tabla `documents`.
            sections: pieces estructuradas que devolvió el extractor.
            text: fallback si el extractor no detectó headings.
            replace: si True (default), borra chunks viejos antes de insertar.

        Lanza `ValueError` si el documento no existe.
        """
        document = await self._document_repo.get(document_id)
        if document is None:
            raise ValueError(f"Documento {document_id} no existe — no se puede indexar")

        # 1) Chunking
        chunks = self._chunker.chunk(
            doc_type=str(document.tipo), sections=sections, text=text
        )
        if not chunks:
            logger.info(
                "indexer_skipped", extra={"document_id": document_id, "reason": "no chunks"}
            )
            return IndexerResult(
                document_id=document_id,
                chunks_created=0,
                tokens_embedded=0,
                cost_usd=0.0,
                sub_batches=0,
                replaced_old_chunks=0,
            )

        # 2) Construir textos con header contextual.
        texts_to_embed = [
            format_context_header(
                document_type=str(document.tipo),
                category=str(document.carpeta),
                section_title=c.section_title,
                content=c.content,
            )
            for c in chunks
        ]

        # 3) Embedding en sub-batches.
        all_vectors: list[tuple[float, ...]] = []
        total_tokens = 0
        total_cost = 0.0
        sub_batches = 0
        for batch_idx in range(0, len(texts_to_embed), self._batch_size):
            batch = texts_to_embed[batch_idx : batch_idx + self._batch_size]
            result = await self._embedder.embed_documents(batch)
            all_vectors.extend(result.vectors)
            total_tokens += result.input_tokens
            total_cost += result.cost_usd
            sub_batches += 1

        if len(all_vectors) != len(chunks):
            # Defensa: si el embedder devolvió cantidad distinta, abortamos
            # antes de persistir basura.
            raise RuntimeError(
                f"embedder devolvió {len(all_vectors)} vectores para "
                f"{len(chunks)} chunks — desincronización detectada"
            )

        # 4) Construir entities de DocumentChunk.
        entities = [
            DocumentChunk(
                id=f"chk-{document_id}-{c.chunk_index:04d}-{uuid.uuid4().hex[:8]}",
                document_id=document_id,
                chunk_index=c.chunk_index,
                content=c.content,
                embedding=list(vector),
                metadata={
                    **c.metadata,
                    "section_title": c.section_title,
                    "token_count": c.token_count,
                },
            )
            for c, vector in zip(chunks, all_vectors, strict=True)
        ]

        # 5) Replace previo (opcional).
        replaced = 0
        if replace:
            replaced = await self._chunk_repo.delete_by_document(document_id)

        # 6) Bulk insert.
        inserted = await self._chunk_repo.bulk_insert(entities)

        return IndexerResult(
            document_id=document_id,
            chunks_created=inserted,
            tokens_embedded=total_tokens,
            cost_usd=round(total_cost, 6),
            sub_batches=sub_batches,
            replaced_old_chunks=replaced,
        )


# ===========================================================================
# Background task wrapper
# ===========================================================================


async def index_document_background(
    indexer: Indexer,
    document_id: str,
    *,
    sections: Sequence[Section],
    text: str | None = None,
    replace: bool = True,
) -> None:
    """Wrapper para `FastAPI.BackgroundTasks`. Loggea resultado o error.

    Las BackgroundTasks de FastAPI swallowean excepciones silenciosamente,
    así que acá las capturamos y loggeamos para que tengan visibilidad
    en App Insights / structlog. La sesión / response del usuario YA
    cerró cuando esto corre — no podemos devolver el error al cliente.
    """
    try:
        result = await indexer.index_document(
            document_id, sections=sections, text=text, replace=replace
        )
        logger.info(
            "indexer_completed",
            extra={
                "document_id": document_id,
                "chunks_created": result.chunks_created,
                "tokens": result.tokens_embedded,
                "cost_usd": result.cost_usd,
                "sub_batches": result.sub_batches,
                "replaced": result.replaced_old_chunks,
            },
        )
    except Exception as exc:  # noqa: BLE001 — background task, fail safe
        logger.exception(
            "indexer_failed",
            extra={"document_id": document_id, "error": str(exc)},
        )
