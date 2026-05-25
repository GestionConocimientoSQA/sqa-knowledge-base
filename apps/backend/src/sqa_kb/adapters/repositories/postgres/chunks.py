"""PostgresChunkRepository — persistencia de chunks vectoriales (Fase 3).

Solo expone lo mínimo: bulk_insert + delete_by_document + count. El
retriever NO usa este repo — usa SQL crudo sobre `document_chunks` para
aprovechar pgvector + HNSW (los SELECT con cosine distance son más
limpios sin pasar por SQLAlchemy ORM).
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.adapters.repositories.postgres import models
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.domain.entities import DocumentChunk


class PostgresChunkRepository:
    """Implementación del puerto `ChunkRepository` con SQLAlchemy + pgvector."""

    def __init__(self, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._session_factory: async_sessionmaker = session_factory

    async def bulk_insert(self, chunks: Sequence[DocumentChunk]) -> int:
        """Inserta los chunks en una sola transacción multi-row.

        `ON CONFLICT (document_id, chunk_index) DO UPDATE` permite
        re-indexar sin borrar antes — útil para reindex_all que itera
        documento por documento sin downtime. Si el indexer prefiere
        snapshot limpio (versionamiento), debe llamar
        `delete_by_document` antes.
        """
        if not chunks:
            return 0
        # Importante: el atributo Python del modelo es `metadata_` (no
        # `metadata`) para esquivar el shadow del `MetaData` reservado de
        # SQLAlchemy Declarative. La columna real en la DB sí se llama
        # `metadata` (vía `mapped_column("metadata", ...)`).
        rows = [
            {
                "id": c.id,
                "document_id": c.document_id,
                "chunk_index": c.chunk_index,
                "content": c.content,
                "embedding": c.embedding,
                "metadata_": dict(c.metadata),
            }
            for c in chunks
        ]
        stmt = pg_insert(models.DocumentChunkModel).values(rows)
        # `excluded` expone columnas por nombre DB (no atributo Python).
        # Indexing por string para evitar el clash con `MetaData`.
        excluded_metadata_col = stmt.excluded["metadata"]
        stmt = stmt.on_conflict_do_update(
            index_elements=["document_id", "chunk_index"],
            set_={
                # set_ keys son nombres DB (no atributos Python).
                "content": stmt.excluded.content,
                "embedding": stmt.excluded.embedding,
                "metadata": excluded_metadata_col,
            },
        )
        async with session_scope(self._session_factory) as db:
            await db.execute(stmt)
        return len(rows)

    async def delete_by_document(self, document_id: str) -> int:
        """Borra todos los chunks de un documento. Devuelve la cantidad
        eliminada (0 si el documento no tenía chunks)."""
        async with session_scope(self._session_factory) as db:
            result = await db.execute(
                delete(models.DocumentChunkModel).where(
                    models.DocumentChunkModel.document_id == document_id
                )
            )
            return result.rowcount or 0

    async def count_for_document(self, document_id: str) -> int:
        """Cantidad de chunks de un documento."""
        async with self._session_factory() as db:
            result = await db.execute(
                select(func.count())
                .select_from(models.DocumentChunkModel)
                .where(models.DocumentChunkModel.document_id == document_id)
            )
            return int(result.scalar_one() or 0)
