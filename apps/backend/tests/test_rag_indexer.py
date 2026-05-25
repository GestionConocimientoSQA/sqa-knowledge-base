"""Tests unitarios del Indexer (Fase 3.2).

Usan fakes para `EmbedderPort`, `ChunkRepository` y `DocumentRepository`.
Sin tocar Cohere ni PG.

Integración con PG real va en `tests/integration/test_rag_indexer_pg.py`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest

from sqa_kb.domain.entities import Document, DocumentChunk
from sqa_kb.domain.value_objects import CategoryCode, DocStatus, DocTypeCode
from sqa_kb.ports.gateways import EmbeddingBatch
from sqa_kb.rag.chunker import Section
from sqa_kb.rag.indexer import (
    DEFAULT_EMBED_BATCH_SIZE,
    Indexer,
    IndexerResult,
    index_document_background,
)

# ===========================================================================
# Fakes
# ===========================================================================


def _doc(id: str, tipo: str = "POL", carpeta: str = "TEC") -> Document:
    now = datetime.now(UTC)
    return Document(
        id=id,
        titulo="Doc test",
        carpeta=CategoryCode(carpeta),
        tipo=DocTypeCode(tipo),
        autoritativo=False,
        estado=DocStatus.VIGENTE,
        autor_name="Tester",
        autor_role="QA",
        fecha=now,
        revision=now,
        version="1.0",
        formato="MD",
    )


@dataclass
class _FakeDocRepo:
    docs: dict[str, Document] = field(default_factory=dict)

    async def get(self, doc_id: str) -> Document | None:
        return self.docs.get(doc_id)


@dataclass
class _FakeChunkRepo:
    bulk_calls: list[list[DocumentChunk]] = field(default_factory=list)
    delete_calls: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    delete_returns: int = 3  # simula 3 chunks viejos por default

    async def bulk_insert(self, chunks: Sequence[DocumentChunk]) -> int:
        self.bulk_calls.append(list(chunks))
        return len(chunks)

    async def delete_by_document(self, document_id: str) -> int:
        self.delete_calls.append(document_id)
        return self.delete_returns

    async def count_for_document(self, document_id: str) -> int:
        return self.counts.get(document_id, 0)


@dataclass
class _FakeEmbedder:
    """Devuelve vectores deterministas para no flakear tests.

    Cada texto produce un vector [len(text), 0.0, 0.0, ...] (1024 dim) —
    así podemos verificar el orden de los chunks vs vectors.
    """

    raise_on: int | None = None
    """Si se setea, lanza al N-ésimo embed call (1-indexed)."""
    call_count: int = 0
    batch_sizes: list[int] = field(default_factory=list)
    return_mismatch: bool = False
    """Si True, devuelve un vector menos para forzar desincronización."""

    async def embed_documents(self, texts: Sequence[str]) -> EmbeddingBatch:
        self.call_count += 1
        self.batch_sizes.append(len(texts))
        if self.raise_on is not None and self.call_count == self.raise_on:
            raise RuntimeError(f"cohere down on call #{self.raise_on}")
        n = len(texts) - 1 if self.return_mismatch else len(texts)
        vectors = tuple(
            tuple([float(len(t))] + [0.0] * 1023) for t in texts[:n]
        )
        return EmbeddingBatch(
            vectors=vectors,
            input_tokens=sum(len(t) for t in texts),
            cost_usd=0.001,
            model="embed-multilingual-v3.0",
        )

    async def embed_query(self, text: str) -> EmbeddingBatch:  # noqa: ARG002
        raise NotImplementedError("indexer no llama embed_query")


# ===========================================================================
# Happy path
# ===========================================================================


async def test_index_document_creates_chunks_with_vectors() -> None:
    doc = _doc("POL-test-2026-01-01")
    doc_repo = _FakeDocRepo(docs={doc.id: doc})
    chunk_repo = _FakeChunkRepo()
    embedder = _FakeEmbedder()

    indexer = Indexer(
        embedder=embedder,  # type: ignore[arg-type]
        chunk_repo=chunk_repo,  # type: ignore[arg-type]
        document_repo=doc_repo,  # type: ignore[arg-type]
    )

    sections = [
        Section(title="Intro", content="Introducción de la política."),
        Section(title="Alcance", content="Aplica a todos los proyectos."),
    ]
    result = await indexer.index_document(doc.id, sections=sections)

    assert isinstance(result, IndexerResult)
    assert result.document_id == doc.id
    assert result.chunks_created == 2
    assert result.sub_batches == 1
    assert result.tokens_embedded > 0
    assert result.cost_usd == 0.001  # un solo batch del fake
    # Replace por default → 3 chunks viejos borrados.
    assert result.replaced_old_chunks == 3

    # Bulk insert recibió 2 entidades.
    inserted = chunk_repo.bulk_calls[0]
    assert len(inserted) == 2
    assert all(c.document_id == doc.id for c in inserted)
    # Embedding asignado.
    assert all(c.embedding is not None and len(c.embedding) == 1024 for c in inserted)


async def test_index_document_returns_zero_when_no_chunks() -> None:
    """Sections vacías + sin text → no embed, no insert, no delete."""
    doc = _doc("POL-empty-2026-01-01")
    doc_repo = _FakeDocRepo(docs={doc.id: doc})
    chunk_repo = _FakeChunkRepo()
    embedder = _FakeEmbedder()

    indexer = Indexer(
        embedder=embedder,  # type: ignore[arg-type]
        chunk_repo=chunk_repo,  # type: ignore[arg-type]
        document_repo=doc_repo,  # type: ignore[arg-type]
    )
    result = await indexer.index_document(doc.id, sections=[])

    assert result.chunks_created == 0
    assert result.sub_batches == 0
    assert result.replaced_old_chunks == 0  # ni siquiera intentó borrar
    # NO se llamó embed ni delete.
    assert embedder.call_count == 0
    assert chunk_repo.delete_calls == []
    assert chunk_repo.bulk_calls == []


async def test_index_document_uses_text_fallback() -> None:
    """Si no hay sections, el chunker arma una con `text`."""
    doc = _doc("POL-fallback-2026-01-01")
    doc_repo = _FakeDocRepo(docs={doc.id: doc})
    chunk_repo = _FakeChunkRepo()
    embedder = _FakeEmbedder()

    indexer = Indexer(
        embedder=embedder,  # type: ignore[arg-type]
        chunk_repo=chunk_repo,  # type: ignore[arg-type]
        document_repo=doc_repo,  # type: ignore[arg-type]
    )
    result = await indexer.index_document(
        doc.id, sections=[], text="Política institucional. " * 5
    )
    assert result.chunks_created == 1


async def test_index_document_chunks_have_metadata_with_token_count() -> None:
    doc = _doc("POL-meta-2026-01-01")
    doc_repo = _FakeDocRepo(docs={doc.id: doc})
    chunk_repo = _FakeChunkRepo()
    embedder = _FakeEmbedder()

    indexer = Indexer(
        embedder=embedder,  # type: ignore[arg-type]
        chunk_repo=chunk_repo,  # type: ignore[arg-type]
        document_repo=doc_repo,  # type: ignore[arg-type]
    )
    await indexer.index_document(
        doc.id, sections=[Section(title="X", content="Contenido.")]
    )
    inserted = chunk_repo.bulk_calls[0][0]
    assert "token_count" in inserted.metadata
    assert inserted.metadata["section_title"] == "X"
    assert inserted.metadata["strategy"] == "semantic"


# ===========================================================================
# Batching
# ===========================================================================


async def test_index_document_splits_in_sub_batches_when_needed() -> None:
    """Más de 96 chunks → múltiples batches al embedder."""
    doc = _doc("POL-batch-2026-01-01")
    doc_repo = _FakeDocRepo(docs={doc.id: doc})
    chunk_repo = _FakeChunkRepo()
    embedder = _FakeEmbedder()

    # 100 sections cortas → 100 chunks → 2 batches (96 + 4).
    sections = [
        Section(title=f"S{i}", content=f"contenido sección {i}.") for i in range(100)
    ]

    indexer = Indexer(
        embedder=embedder,  # type: ignore[arg-type]
        chunk_repo=chunk_repo,  # type: ignore[arg-type]
        document_repo=doc_repo,  # type: ignore[arg-type]
    )
    result = await indexer.index_document(doc.id, sections=sections)

    assert result.chunks_created == 100
    assert result.sub_batches == 2
    assert embedder.batch_sizes == [DEFAULT_EMBED_BATCH_SIZE, 4]
    assert result.cost_usd == pytest.approx(0.002, rel=1e-6)  # 2 batches × 0.001


async def test_index_document_accepts_custom_batch_size() -> None:
    """Inyectable para tests / debugging."""
    doc = _doc("POL-custom-2026-01-01")
    doc_repo = _FakeDocRepo(docs={doc.id: doc})
    chunk_repo = _FakeChunkRepo()
    embedder = _FakeEmbedder()

    sections = [Section(title=f"S{i}", content="x") for i in range(5)]
    indexer = Indexer(
        embedder=embedder,  # type: ignore[arg-type]
        chunk_repo=chunk_repo,  # type: ignore[arg-type]
        document_repo=doc_repo,  # type: ignore[arg-type]
        batch_size=2,
    )
    result = await indexer.index_document(doc.id, sections=sections)
    # 5 chunks / batch 2 = 3 batches (2+2+1).
    assert result.sub_batches == 3
    assert embedder.batch_sizes == [2, 2, 1]


# ===========================================================================
# Errores
# ===========================================================================


async def test_index_document_unknown_doc_raises() -> None:
    doc_repo = _FakeDocRepo()  # vacío
    chunk_repo = _FakeChunkRepo()
    embedder = _FakeEmbedder()

    indexer = Indexer(
        embedder=embedder,  # type: ignore[arg-type]
        chunk_repo=chunk_repo,  # type: ignore[arg-type]
        document_repo=doc_repo,  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="no existe"):
        await indexer.index_document("DOC-no-existe-2026-01-01", sections=[])


async def test_index_document_does_not_persist_when_embedder_fails_mid_run() -> None:
    """Embedder rompe al segundo batch → no se borra ni inserta nada.

    Si el delete fuese ANTES del embedding, ya habríamos perdido los
    chunks viejos al fallar. Por eso el orden es embed-completo → delete
    → insert (ROADMAP §17.3).
    """
    doc = _doc("POL-fail-2026-01-01")
    doc_repo = _FakeDocRepo(docs={doc.id: doc})
    chunk_repo = _FakeChunkRepo()
    embedder = _FakeEmbedder(raise_on=2)  # falla en el segundo call

    sections = [
        Section(title=f"S{i}", content=f"texto {i}.") for i in range(150)
    ]
    indexer = Indexer(
        embedder=embedder,  # type: ignore[arg-type]
        chunk_repo=chunk_repo,  # type: ignore[arg-type]
        document_repo=doc_repo,  # type: ignore[arg-type]
    )
    with pytest.raises(RuntimeError, match="cohere down"):
        await indexer.index_document(doc.id, sections=sections)

    # Crítico: ni delete ni insert se llamaron.
    assert chunk_repo.delete_calls == []
    assert chunk_repo.bulk_calls == []


async def test_index_document_detects_vector_count_mismatch() -> None:
    """Defensa: si el embedder devuelve N vectores para != N chunks → abortar."""
    doc = _doc("POL-mismatch-2026-01-01")
    doc_repo = _FakeDocRepo(docs={doc.id: doc})
    chunk_repo = _FakeChunkRepo()
    embedder = _FakeEmbedder(return_mismatch=True)

    indexer = Indexer(
        embedder=embedder,  # type: ignore[arg-type]
        chunk_repo=chunk_repo,  # type: ignore[arg-type]
        document_repo=doc_repo,  # type: ignore[arg-type]
    )
    with pytest.raises(RuntimeError, match="desincronización"):
        await indexer.index_document(
            doc.id,
            sections=[
                Section(title="A", content="x"),
                Section(title="B", content="y"),
            ],
        )
    assert chunk_repo.bulk_calls == []


async def test_index_document_skips_delete_when_replace_false() -> None:
    """`replace=False` para reindex incremental que reusa el conflict do update."""
    doc = _doc("POL-noreplace-2026-01-01")
    doc_repo = _FakeDocRepo(docs={doc.id: doc})
    chunk_repo = _FakeChunkRepo()
    embedder = _FakeEmbedder()

    indexer = Indexer(
        embedder=embedder,  # type: ignore[arg-type]
        chunk_repo=chunk_repo,  # type: ignore[arg-type]
        document_repo=doc_repo,  # type: ignore[arg-type]
    )
    result = await indexer.index_document(
        doc.id,
        sections=[Section(title="X", content="x")],
        replace=False,
    )
    assert chunk_repo.delete_calls == []
    assert result.replaced_old_chunks == 0


# ===========================================================================
# Background task wrapper
# ===========================================================================


async def test_background_swallows_exceptions(caplog: Any) -> None:
    """El wrapper NO debe propagar excepciones — solo loggea."""
    import logging

    doc_repo = _FakeDocRepo()  # vacío → ValueError
    chunk_repo = _FakeChunkRepo()
    embedder = _FakeEmbedder()
    indexer = Indexer(
        embedder=embedder,  # type: ignore[arg-type]
        chunk_repo=chunk_repo,  # type: ignore[arg-type]
        document_repo=doc_repo,  # type: ignore[arg-type]
    )

    # NO raise — el wrapper se traga la excepción.
    with caplog.at_level(logging.ERROR):
        await index_document_background(
            indexer, "DOC-no-existe-2026-01-01", sections=[]
        )
    # Pero la loggeó.
    assert any("indexer_failed" in rec.message for rec in caplog.records)


async def test_background_logs_success(caplog: Any) -> None:
    import logging

    doc = _doc("POL-bg-ok-2026-01-01")
    doc_repo = _FakeDocRepo(docs={doc.id: doc})
    chunk_repo = _FakeChunkRepo()
    embedder = _FakeEmbedder()
    indexer = Indexer(
        embedder=embedder,  # type: ignore[arg-type]
        chunk_repo=chunk_repo,  # type: ignore[arg-type]
        document_repo=doc_repo,  # type: ignore[arg-type]
    )

    with caplog.at_level(logging.INFO):
        await index_document_background(
            indexer, doc.id, sections=[Section(title="X", content="x")]
        )
    assert any("indexer_completed" in rec.message for rec in caplog.records)
