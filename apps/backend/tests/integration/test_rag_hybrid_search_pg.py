"""Tests de integración del HybridSearcher (Fase 3.4).

Requieren PG real con las migraciones Alembic aplicadas, en particular
`c8e2f5a1d3b6_gin_fts_index_document_chunks` que crea el índice GIN
sobre `to_tsvector('spanish', content)`.

Validan que:
- El SQL combinado parsea y ejecuta contra pgvector + tsvector.
- El JOIN combina chunks que matchean en ambas ramas, una sola o ninguna.
- Los pesos vec/fts mueven el ranking de forma medible.
- El boost autoritativo aplica al combined_score.
- El índice GIN existe tras la migración.

Embedder fake — sin pegarle a Cohere.
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
from sqa_kb.rag.hybrid_search import HybridSearcher

# ===========================================================================
# Cleanup
# ===========================================================================


@pytest_asyncio.fixture(autouse=True)
async def _clean_chunks_table(db_engine) -> None:  # type: ignore[no-untyped-def]
    """Trunca `document_chunks` antes de cada test (mismo patrón que el
    retriever — los suites previos committean filas que contaminan el
    ranking global)."""
    async with db_engine.connect() as conn:
        await conn.execute(text("TRUNCATE TABLE document_chunks"))
        await conn.commit()


# ===========================================================================
# Fakes + helpers
# ===========================================================================


@dataclass
class _StaticEmbedder:
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


def _vec_with_first(value: float) -> list[float]:
    """Vector 1024-dim con `value` en posición 0 — el resto en cero."""
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
    session_factory, *, doc_id: str, vector: list[float], content: str,
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
                metadata={"section_title": section_title, "strategy": "semantic"},
            )
        ]
    )


# ===========================================================================
# Tests
# ===========================================================================


async def test_search_finds_chunk_with_fts_match_even_when_vector_far(
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Un chunk con keyword exacta pero embedding lejano debe aparecer.

    Es justamente el caso de uso de hybrid search: el retriever vector
    solo lo perdería; el FTS lo rescata.
    """
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"POL-fts-{suffix}-2026-05-25"
    await _ensure_doc(session_factory, doc_id=doc_id)
    await _seed_chunk(
        session_factory,
        doc_id=doc_id,
        vector=_vec_with_first(0.01),  # lejos del query
        content="Playwright es la herramienta de E2E elegida.",
    )

    # Query lejana en embedding pero con keyword "Playwright".
    searcher = HybridSearcher(
        embedder=_StaticEmbedder(vector=_vec_with_first(0.99)),
        session_factory=session_factory,
    )
    out = await searcher.search("Playwright", project_id=GK_GENERAL_PROJECT_ID, top_k=10)

    ours = [c for c in out if c.document_id == doc_id]
    assert len(ours) == 1
    assert ours[0].fulltext_score > 0
    # El vector_score puede ser bajo pero el combined_score positivo gracias al FTS.
    assert ours[0].score > 0


async def test_search_finds_chunk_with_vector_match_no_fts(
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Chunk semánticamente parecido pero sin coincidencia léxica debe
    aparecer vía vector_results (fts_score=0 vía COALESCE)."""
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"POL-vec-{suffix}-2026-05-25"
    await _ensure_doc(session_factory, doc_id=doc_id)
    await _seed_chunk(
        session_factory,
        doc_id=doc_id,
        vector=_vec_with_first(0.95),
        content="Texto sobre tema completamente ajeno al término buscado.",
    )

    searcher = HybridSearcher(
        embedder=_StaticEmbedder(vector=_vec_with_first(0.95)),
        session_factory=session_factory,
    )
    out = await searcher.search("zzzqxq", project_id=GK_GENERAL_PROJECT_ID, top_k=10)
    ours = [c for c in out if c.document_id == doc_id]
    assert len(ours) == 1
    assert ours[0].vector_score > 0
    # El término "zzzqxq" no existe en el contenido → fts_score=0.
    assert ours[0].fulltext_score == 0.0


async def test_search_chunk_with_both_matches_outranks_single_branch(
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Con pesos 0.7/0.3, un chunk que matchea AMBAS ramas debe rankear
    mejor que uno que solo matchea una."""
    suffix = uuid.uuid4().hex[:6]
    doc_both = f"POL-both-{suffix}-2026-05-25"
    doc_vec = f"POL-vonly-{suffix}-2026-05-25"
    doc_fts = f"POL-fonly-{suffix}-2026-05-25"

    await _ensure_doc(session_factory, doc_id=doc_both)
    await _ensure_doc(session_factory, doc_id=doc_vec)
    await _ensure_doc(session_factory, doc_id=doc_fts)

    # Vector similar al query + keyword "playwright".
    await _seed_chunk(
        session_factory, doc_id=doc_both, vector=_vec_with_first(0.95),
        content="Playwright como framework de pruebas automatizadas.",
    )
    # Solo vector similar.
    await _seed_chunk(
        session_factory, doc_id=doc_vec, vector=_vec_with_first(0.95),
        content="Marco general de calidad sin mencionar herramientas concretas.",
    )
    # Solo keyword.
    await _seed_chunk(
        session_factory, doc_id=doc_fts, vector=_vec_with_first(0.01),
        content="Playwright en un contexto histórico totalmente irrelevante.",
    )

    searcher = HybridSearcher(
        embedder=_StaticEmbedder(vector=_vec_with_first(0.95)),
        session_factory=session_factory,
    )
    out = await searcher.search("Playwright", project_id=GK_GENERAL_PROJECT_ID, top_k=10)

    # Mapeo rápido por document_id.
    by_doc = {c.document_id: c for c in out}
    assert doc_both in by_doc, "el chunk con ambas señales debería aparecer"
    # El de ambas señales debe rankear primero entre los nuestros.
    ours = [c for c in out if c.document_id in {doc_both, doc_vec, doc_fts}]
    ours_sorted = sorted(ours, key=lambda c: c.score, reverse=True)
    assert ours_sorted[0].document_id == doc_both


async def test_search_filters_by_carpeta(session_factory) -> None:  # type: ignore[no-untyped-def]
    suffix = uuid.uuid4().hex[:6]
    doc_tec = f"POL-fc-tec-{suffix}-2026-05-25"
    doc_proc = f"POL-fc-proc-{suffix}-2026-05-25"
    await _ensure_doc(session_factory, doc_id=doc_tec, carpeta="TEC")
    await _ensure_doc(session_factory, doc_id=doc_proc, carpeta="PROC")
    await _seed_chunk(
        session_factory, doc_id=doc_tec, vector=_vec_with_first(0.7),
        content="Playwright en TEC.",
    )
    await _seed_chunk(
        session_factory, doc_id=doc_proc, vector=_vec_with_first(0.7),
        content="Playwright en PROC.",
    )

    searcher = HybridSearcher(
        embedder=_StaticEmbedder(vector=_vec_with_first(0.7)),
        session_factory=session_factory,
    )
    out = await searcher.search("Playwright", project_id=GK_GENERAL_PROJECT_ID, top_k=50, carpetas=["TEC"])
    ids = {c.document_id for c in out}
    assert doc_tec in ids
    assert doc_proc not in ids


async def test_search_filters_by_tipo(session_factory) -> None:  # type: ignore[no-untyped-def]
    suffix = uuid.uuid4().hex[:6]
    doc_pol = f"POL-ft-{suffix}-2026-05-25"
    doc_proc = f"PROC-ft-{suffix}-2026-05-25"
    await _ensure_doc(session_factory, doc_id=doc_pol, tipo="POL")
    await _ensure_doc(session_factory, doc_id=doc_proc, tipo="PROC")
    await _seed_chunk(
        session_factory, doc_id=doc_pol, vector=_vec_with_first(0.7),
        content="Playwright POL.",
    )
    await _seed_chunk(
        session_factory, doc_id=doc_proc, vector=_vec_with_first(0.7),
        content="Playwright PROC.",
    )

    searcher = HybridSearcher(
        embedder=_StaticEmbedder(vector=_vec_with_first(0.7)),
        session_factory=session_factory,
    )
    out = await searcher.search("Playwright", project_id=GK_GENERAL_PROJECT_ID, top_k=50, tipos=["PROC"])
    ids = {c.document_id for c in out}
    assert doc_proc in ids
    assert doc_pol not in ids


async def test_search_authoritative_only_excludes_non_authoritative(
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    suffix = uuid.uuid4().hex[:6]
    doc_normal = f"POL-ao-norm-{suffix}-2026-05-25"
    doc_auth = f"POL-ao-auth-{suffix}-2026-05-25"
    await _ensure_doc(session_factory, doc_id=doc_normal, autoritativo=False)
    await _ensure_doc(session_factory, doc_id=doc_auth, autoritativo=True)
    await _seed_chunk(
        session_factory, doc_id=doc_normal, vector=_vec_with_first(0.99),
        content="Playwright en doc normal.",
    )
    await _seed_chunk(
        session_factory, doc_id=doc_auth, vector=_vec_with_first(0.5),
        content="Playwright en doc autoritativo.",
    )

    searcher = HybridSearcher(
        embedder=_StaticEmbedder(vector=_vec_with_first(0.99)),
        session_factory=session_factory,
    )
    out = await searcher.search("Playwright", project_id=GK_GENERAL_PROJECT_ID, top_k=50, authoritative_only=True)
    ids = {c.document_id for c in out}
    assert doc_auth in ids
    assert doc_normal not in ids


async def test_search_authoritative_boost_promotes_authoritative(
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Con boost 1.15, dos chunks idénticos en vec+fts: autoritativo gana."""
    suffix = uuid.uuid4().hex[:6]
    doc_normal = f"POL-bst-norm-{suffix}-2026-05-25"
    doc_auth = f"POL-bst-auth-{suffix}-2026-05-25"
    await _ensure_doc(session_factory, doc_id=doc_normal, autoritativo=False)
    await _ensure_doc(session_factory, doc_id=doc_auth, autoritativo=True)
    same_vec = _vec_with_first(0.7)
    same_content = "Playwright pipeline."
    await _seed_chunk(
        session_factory, doc_id=doc_normal, vector=same_vec, content=same_content
    )
    await _seed_chunk(
        session_factory, doc_id=doc_auth, vector=same_vec, content=same_content
    )

    searcher = HybridSearcher(
        embedder=_StaticEmbedder(vector=same_vec),
        session_factory=session_factory,
    )
    out = await searcher.search("Playwright", project_id=GK_GENERAL_PROJECT_ID, top_k=50)
    ours = [c for c in out if c.document_id in {doc_normal, doc_auth}]
    assert len(ours) == 2
    # Autoritativo gana por el boost.
    assert ours[0].document_id == doc_auth
    # El score del auth es ~1.15× el del normal.
    assert ours[0].score == pytest.approx(ours[1].score * 1.15, rel=1e-3)


async def test_search_special_characters_in_query_do_not_break(
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    """`plainto_tsquery` neutraliza operadores especiales — el SQL no debe
    fallar con input adversarial."""
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"POL-sp-{suffix}-2026-05-25"
    await _ensure_doc(session_factory, doc_id=doc_id)
    await _seed_chunk(
        session_factory, doc_id=doc_id, vector=_vec_with_first(0.5),
        content="contenido normal",
    )

    searcher = HybridSearcher(
        embedder=_StaticEmbedder(vector=_vec_with_first(0.5)),
        session_factory=session_factory,
    )
    # Caracteres tsquery (&, |, !, :, paréntesis) + comilla simple.
    out = await searcher.search("foo & bar | !baz : (qux) 'drop'", project_id=GK_GENERAL_PROJECT_ID, top_k=10)
    # No revienta — devuelve lo que matchee (probablemente vacío o solo vector).
    assert isinstance(out, list)


async def test_gin_fts_index_exists_after_migration(db_engine) -> None:  # type: ignore[no-untyped-def]
    """Smoke check: la migración `c8e2f5a1d3b6` creó el índice GIN."""
    async with db_engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'document_chunks'
                  AND indexname = 'ix_document_chunks_content_fts'
                """
            )
        )
        row = result.first()
    assert row is not None, (
        "El índice GIN no existe — ¿corriste `alembic upgrade head`?"
    )


async def test_search_top_k_caps_result_count(session_factory) -> None:  # type: ignore[no-untyped-def]
    """`top_k=2` recorta resultados aun habiendo más chunks que matchean."""
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"POL-tk-{suffix}-2026-05-25"
    await _ensure_doc(session_factory, doc_id=doc_id)
    for i in range(5):
        await _seed_chunk(
            session_factory, doc_id=doc_id,
            vector=_vec_with_first(0.5 + i * 0.05),
            content=f"Playwright chunk {i}",
            chunk_index=i,
        )

    searcher = HybridSearcher(
        embedder=_StaticEmbedder(vector=_vec_with_first(0.6)),
        session_factory=session_factory,
    )
    out = await searcher.search("Playwright", project_id=GK_GENERAL_PROJECT_ID, top_k=2)
    assert len(out) <= 2
