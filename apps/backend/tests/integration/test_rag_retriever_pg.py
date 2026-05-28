"""Tests de integración del VectorRetriever (Fase 3.3).

Requieren PG real con la migración Alembic aplicada (incluyendo el índice
HNSW creado por `b3a7d1c2e0f4_hnsw_index_document_chunks`).

Estos tests validan el comportamiento del retriever contra pgvector real:

- La query SQL es válida (parseable + tipos coherentes).
- El operador `<=>` (cosine distance) calcula correctamente.
- El boost de autoritativo se aplica en el score final.
- Los filtros funcionan en la práctica (carpeta, tipo, authoritative_only).
- El índice HNSW existe en la DB tras la migración.

El embedder es un fake — sin tráfico a Cohere por regla del usuario.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import text

from sqa_kb.adapters.repositories.postgres import models
from sqa_kb.adapters.repositories.postgres.chunks import PostgresChunkRepository
from sqa_kb.adapters.repositories.postgres.mappers import GK_GENERAL_PROJECT_ID
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.domain.entities import DocumentChunk
from sqa_kb.ports.gateways import EmbeddingBatch
from sqa_kb.rag.retriever import VectorRetriever

# ===========================================================================
# Cleanup
# ===========================================================================
#
# El retriever ordena por similitud sobre TODA la tabla `document_chunks`.
# Otros tests integration (de chunks_repo, indexer, etc.) dejan filas
# committeadas porque usan `session_scope` (no rollback). Si esos chunks
# residuales están más cerca del query que los nuestros, top_k los devuelve
# en lugar de los nuestros y los asserts del ranking explotan.
#
# Limpieza por test: `TRUNCATE document_chunks CASCADE`. La tabla
# `documents` queda intacta — la cascade solo afectaría a `query_citations`
# si las hubiera (no las hay en estos tests). Cada test crea sus propios
# docs con suffix UUID, así que tampoco hay colisión con docs previos.


@pytest_asyncio.fixture(autouse=True)
async def _clean_chunks_table(db_engine) -> None:  # type: ignore[no-untyped-def]
    """Trunca `document_chunks` antes de cada test del retriever."""
    async with db_engine.connect() as conn:
        await conn.execute(text("TRUNCATE TABLE document_chunks"))
        await conn.commit()


# ===========================================================================
# Fake embedder (mismos vectores que se persistieron — sin red)
# ===========================================================================


@dataclass
class _StaticEmbedder:
    """Devuelve un vector fijo por query. Permite controlar la similitud
    contra los vectores conocidos que se insertaron en la DB."""

    vector: Sequence[float]

    async def embed_documents(self, texts):  # type: ignore[no-untyped-def] # noqa: ARG002
        raise NotImplementedError

    async def embed_query(self, text: str) -> EmbeddingBatch:  # noqa: ARG002
        return EmbeddingBatch(
            vectors=(tuple(self.vector),),
            input_tokens=1,
            cost_usd=0.0,
            model="fake-static",
        )


# ===========================================================================
# Helpers de seed
# ===========================================================================


def _vec_with_first(value: float) -> list[float]:
    """Vector 1024-dim con `value` en posición 0 — el resto en cero.

    Cosine distance entre dos vectores así depende solo de la posición 0,
    lo que hace los tests deterministas y fáciles de razonar.
    """
    return [value] + [0.0] * 1023


async def _ensure_doc(  # type: ignore[no-untyped-def]
    session_factory, *, doc_id: str, carpeta: str = "TEC", tipo: str = "POL",
    autoritativo: bool = False, titulo: str = "Doc test",
) -> None:
    async with session_scope(session_factory) as db:
        db.add(
            models.DocumentModel(
                id=doc_id,
                project_id=GK_GENERAL_PROJECT_ID,
                titulo=titulo,
                carpeta=carpeta,
                tipo=tipo,
                autoritativo=autoritativo,
                estado="vigente",
                autor_oid=None,
                autor_name="Tester",
                autor_role="QA",
                fecha=datetime.now(UTC),
                revision=datetime.now(UTC),
                version="1.0",
                citas=0,
                score=0.0,
                anonimizado=False,
                fragmentos=0,
                paginas=1,
                formato="MD",
                tags=[],
                resumen="",
            )
        )


async def _seed_chunk(  # type: ignore[no-untyped-def]
    session_factory, *, doc_id: str, vector: list[float], content: str = "contenido",
    section_title: str = "Intro", chunk_index: int = 0,
) -> None:
    repo = PostgresChunkRepository(session_factory)
    await repo.bulk_insert(
        [
            DocumentChunk(
                id=f"chk-{doc_id}-{chunk_index:04d}-{uuid.uuid4().hex[:8]}",
                document_id=doc_id,
                chunk_index=chunk_index,
                content=content,
                embedding=vector,
                metadata={
                    "section_title": section_title,
                    "strategy": "semantic",
                    "token_count": 50,
                },
            )
        ]
    )


# ===========================================================================
# Tests
# ===========================================================================


async def test_retrieve_finds_chunks_with_real_cosine_distance(session_factory) -> None:  # type: ignore[no-untyped-def]
    """Smoke: la query SQL se ejecuta y devuelve chunks ordenados por similitud."""
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"POL-cos-{suffix}-2026-05-25"
    await _ensure_doc(session_factory, doc_id=doc_id)
    # Dos chunks con distinta similitud al query.
    await _seed_chunk(
        session_factory, doc_id=doc_id, vector=_vec_with_first(0.9),
        content="chunk muy similar", chunk_index=0,
    )
    await _seed_chunk(
        session_factory, doc_id=doc_id, vector=_vec_with_first(0.1),
        content="chunk lejano", chunk_index=1,
    )

    # Query parecido al chunk 0.
    retriever = VectorRetriever(
        embedder=_StaticEmbedder(vector=_vec_with_first(0.95)),
        session_factory=session_factory,
    )
    out = await retriever.retrieve("q", top_k=5)

    # Filtramos los chunks del doc nuestro (otros tests pueden haber
    # dejado data — no asumimos DB virgen).
    ours = [c for c in out if c.document_id == doc_id]
    assert len(ours) == 2
    # El similar debe estar antes que el lejano.
    indices = [c.chunk_index for c in ours]
    assert indices.index(0) < indices.index(1)


async def test_retrieve_authoritative_boost_changes_ranking(session_factory) -> None:  # type: ignore[no-untyped-def]
    """Con la misma distancia cruda, autoritativo debe ganar por el boost.

    Caso límite: dos chunks con vector idéntico — sin boost empatarían;
    con boost 1.15 el autoritativo queda primero.
    """
    suffix = uuid.uuid4().hex[:6]
    doc_normal = f"POL-norm-{suffix}-2026-05-25"
    doc_auth = f"POL-auth-{suffix}-2026-05-25"
    await _ensure_doc(session_factory, doc_id=doc_normal, autoritativo=False)
    await _ensure_doc(session_factory, doc_id=doc_auth, autoritativo=True)

    same_vec = _vec_with_first(0.5)
    await _seed_chunk(session_factory, doc_id=doc_normal, vector=same_vec)
    await _seed_chunk(session_factory, doc_id=doc_auth, vector=same_vec)

    retriever = VectorRetriever(
        embedder=_StaticEmbedder(vector=same_vec),
        session_factory=session_factory,
    )
    out = await retriever.retrieve("q", top_k=50)
    ours = [c for c in out if c.document_id in {doc_normal, doc_auth}]
    assert len(ours) == 2
    # Tras re-rank, autoritativo primero.
    assert ours[0].document_id == doc_auth
    assert ours[0].authoritative is True
    # El score del autoritativo es ~1.15× el del normal.
    assert ours[0].score == pytest.approx(ours[1].score * 1.15, rel=1e-3)


async def test_retrieve_filters_by_carpeta(session_factory) -> None:  # type: ignore[no-untyped-def]
    """`carpetas=['TEC']` excluye chunks de otras carpetas."""
    suffix = uuid.uuid4().hex[:6]
    doc_tec = f"POL-tec-{suffix}-2026-05-25"
    doc_proc = f"POL-proc-{suffix}-2026-05-25"
    await _ensure_doc(session_factory, doc_id=doc_tec, carpeta="TEC")
    await _ensure_doc(session_factory, doc_id=doc_proc, carpeta="PROC")
    await _seed_chunk(session_factory, doc_id=doc_tec, vector=_vec_with_first(0.7))
    await _seed_chunk(session_factory, doc_id=doc_proc, vector=_vec_with_first(0.7))

    retriever = VectorRetriever(
        embedder=_StaticEmbedder(vector=_vec_with_first(0.7)),
        session_factory=session_factory,
    )
    out = await retriever.retrieve("q", top_k=50, carpetas=["TEC"])
    returned_ids = {c.document_id for c in out}
    assert doc_tec in returned_ids
    assert doc_proc not in returned_ids


async def test_retrieve_filters_by_tipo(session_factory) -> None:  # type: ignore[no-untyped-def]
    """`tipos=['PROC']` excluye chunks de docs de otro tipo."""
    suffix = uuid.uuid4().hex[:6]
    doc_pol = f"POL-tp-{suffix}-2026-05-25"
    doc_proc = f"PROC-tp-{suffix}-2026-05-25"
    await _ensure_doc(session_factory, doc_id=doc_pol, tipo="POL")
    await _ensure_doc(session_factory, doc_id=doc_proc, tipo="PROC")
    await _seed_chunk(session_factory, doc_id=doc_pol, vector=_vec_with_first(0.7))
    await _seed_chunk(session_factory, doc_id=doc_proc, vector=_vec_with_first(0.7))

    retriever = VectorRetriever(
        embedder=_StaticEmbedder(vector=_vec_with_first(0.7)),
        session_factory=session_factory,
    )
    out = await retriever.retrieve("q", top_k=50, tipos=["PROC"])
    returned_ids = {c.document_id for c in out}
    assert doc_proc in returned_ids
    assert doc_pol not in returned_ids


async def test_retrieve_authoritative_only_excludes_others(session_factory) -> None:  # type: ignore[no-untyped-def]
    """`authoritative_only=True` descarta no-autoritativos antes del rank."""
    suffix = uuid.uuid4().hex[:6]
    doc_normal = f"POL-ao-norm-{suffix}-2026-05-25"
    doc_auth = f"POL-ao-auth-{suffix}-2026-05-25"
    await _ensure_doc(session_factory, doc_id=doc_normal, autoritativo=False)
    await _ensure_doc(session_factory, doc_id=doc_auth, autoritativo=True)
    # Damos al normal una distancia mejor — sin el filtro ganaría.
    await _seed_chunk(session_factory, doc_id=doc_normal, vector=_vec_with_first(0.99))
    await _seed_chunk(session_factory, doc_id=doc_auth, vector=_vec_with_first(0.5))

    retriever = VectorRetriever(
        embedder=_StaticEmbedder(vector=_vec_with_first(0.99)),
        session_factory=session_factory,
    )
    out = await retriever.retrieve("q", top_k=50, authoritative_only=True)
    returned_ids = {c.document_id for c in out}
    assert doc_auth in returned_ids
    assert doc_normal not in returned_ids


async def test_retrieve_top_k_limits_results(session_factory) -> None:  # type: ignore[no-untyped-def]
    """`top_k=2` debe devolver a lo sumo 2 chunks aun con más en DB."""
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"POL-topk-{suffix}-2026-05-25"
    await _ensure_doc(session_factory, doc_id=doc_id)
    for i in range(5):
        await _seed_chunk(
            session_factory, doc_id=doc_id,
            vector=_vec_with_first(0.5 + i * 0.05), chunk_index=i,
        )

    retriever = VectorRetriever(
        embedder=_StaticEmbedder(vector=_vec_with_first(0.6)),
        session_factory=session_factory,
    )
    # Restrinjo al doc nuestro vía filtro de tipo+carpeta para que otros
    # tests no contaminen el conteo.
    out = await retriever.retrieve(
        "q", top_k=2, carpetas=["TEC"], tipos=["POL"]
    )
    ours = [c for c in out if c.document_id == doc_id]
    # No podemos asertar `len(out) == 2` globalmente (otros tests dejaron
    # datos), pero sí que el subset del doc nuestro respeta el límite
    # cuando es el único matcheante. Como no es garantizable, usamos LIMIT
    # del SQL — el resultado completo debe ser ≤ 2.
    assert len(out) <= 2
    assert all(c.chunk_index in {0, 1, 2, 3, 4} for c in ours)


async def test_hnsw_index_exists_after_migration(db_engine) -> None:  # type: ignore[no-untyped-def]
    """Smoke check: la migración `b3a7d1c2e0f4` creó el índice HNSW."""
    from sqlalchemy import text

    async with db_engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'document_chunks'
                  AND indexname = 'ix_document_chunks_embedding_hnsw'
                """
            )
        )
        row = result.first()
    assert row is not None, (
        "El índice HNSW no existe — ¿corriste `alembic upgrade head`?"
    )
