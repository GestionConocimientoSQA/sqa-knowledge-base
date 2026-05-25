"""Tests E2E del POST /queries contra PostgreSQL real (Fase 3.5).

Cubren el flujo completo:
1. Bearer dev token → CurrentUser.
2. HybridSearcher (override con fake — no pegamos a Cohere) → HybridChunks.
3. Persistencia: filas reales en `queries` y `query_citations`.
4. Response del endpoint con `items`, `totalReturned`, `hasResult`.

El `HybridSearcher` se overridea porque NO queremos pegarle a Cohere en
tests (regla del usuario). El resto del stack (auth, DB, routers) es real.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from sqa_kb.adapters.repositories.postgres import models
from sqa_kb.adapters.repositories.postgres.seed import seed
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.api.dependencies import get_kb_searcher
from sqa_kb.main import create_app
from sqa_kb.rag.hybrid_search import HybridChunk

CAPTURADOR = "Bearer dev:stub-capturador-00000000"


# ===========================================================================
# Fake searcher (sin Cohere)
# ===========================================================================


def _chunk(
    *,
    chunk_id: str,
    document_id: str,
    score: float = 0.85,
    content: str = "Texto del chunk",
    section_title: str = "Intro",
    document_type: str = "POL",
    document_category: str = "TEC",
    document_title: str = "Doc",
    authoritative: bool = False,
) -> HybridChunk:
    return HybridChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        content=content,
        snippet=content[:240],
        section_title=section_title,
        score=score,
        vector_score=score,
        fulltext_score=0.0,
        document_title=document_title,
        document_type=document_type,
        document_category=document_category,
        authoritative=authoritative,
    )


@dataclass
class _ScriptedSearcher:
    """Devuelve los chunks que se le configuren — el test los persiste
    como docs reales antes de invocar el endpoint."""

    chunks_to_return: list[HybridChunk] = field(default_factory=list)

    async def search(
        self,
        query: str,  # noqa: ARG002
        *,
        top_k: int = 5,  # noqa: ARG002
        carpetas: Iterable[str] | None = None,  # noqa: ARG002
        tipos: Iterable[str] | None = None,  # noqa: ARG002
        authoritative_only: bool = False,  # noqa: ARG002
        authoritative_boost: float | None = None,  # noqa: ARG002
    ) -> Sequence[HybridChunk]:
        return list(self.chunks_to_return)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest_asyncio.fixture
async def _clean_queries_tables(db_engine) -> None:  # type: ignore[no-untyped-def]
    """Trunca `query_citations` + `queries` antes de cada test.

    `query_citations` primero por la FK que apunta a `queries.id`. La
    cascada de la FK también lo haría al borrar la query, pero ser
    explícito acá deja el test obviamente aislado.
    """
    async with db_engine.connect() as conn:
        await conn.execute(text("TRUNCATE TABLE query_citations RESTART IDENTITY"))
        await conn.execute(text("TRUNCATE TABLE queries CASCADE"))
        await conn.commit()


@pytest_asyncio.fixture
async def _seed_db(session_factory) -> None:  # type: ignore[no-untyped-def]
    await seed(session_factory)


@pytest.fixture
def client_with_fake_searcher(  # type: ignore[no-untyped-def]
    _seed_db,
    _clean_queries_tables,
) -> Iterator[tuple[TestClient, _ScriptedSearcher]]:
    """TestClient con `kb_searcher` overrideado. Auth + DB son reales."""
    app = create_app()
    searcher = _ScriptedSearcher()
    app.dependency_overrides[get_kb_searcher] = lambda: searcher
    with TestClient(app) as client:
        yield client, searcher
    app.dependency_overrides.clear()


async def _create_doc_in_db(  # type: ignore[no-untyped-def]
    session_factory, *, doc_id: str, carpeta: str = "TEC", tipo: str = "POL",
) -> None:
    """Crea un doc real en la tabla para que las FK del citation aguanten."""
    async with session_scope(session_factory) as db:
        db.add(
            models.DocumentModel(
                id=doc_id,
                titulo="Doc test",
                carpeta=carpeta,
                tipo=tipo,
                autoritativo=False,
                estado="vigente",
                autor_oid=None,
                autor_name="T",
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


# ===========================================================================
# Tests
# ===========================================================================


async def test_post_queries_persists_query_row_in_db(
    client_with_fake_searcher,  # type: ignore[no-untyped-def]
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    """POST /queries → fila en `queries` con `user_oid`, `text`, `has_result`."""
    client, searcher = client_with_fake_searcher
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"POL-q-{suffix}-2026-05-25"
    await _create_doc_in_db(session_factory, doc_id=doc_id)
    searcher.chunks_to_return = [_chunk(chunk_id="c1", document_id=doc_id)]

    resp = client.post(
        "/queries",
        json={"query": "qué es flaky"},
        headers={"Authorization": CAPTURADOR},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["hasResult"] is True
    query_id = body["queryId"]

    # Verificamos la fila en DB.
    async with session_factory() as db:
        result = await db.execute(
            select(models.QueryModel).where(models.QueryModel.id == query_id)
        )
        row = result.scalar_one()
    assert row.text == "qué es flaky"
    assert row.user_oid == "stub-capturador-00000000"
    assert row.has_result is True
    assert row.answered_at is not None


async def test_post_queries_persists_one_citation_per_chunk(
    client_with_fake_searcher,  # type: ignore[no-untyped-def]
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Cada chunk top-K → fila en `query_citations`."""
    client, searcher = client_with_fake_searcher
    suffix = uuid.uuid4().hex[:6]
    doc_a = f"POL-a-{suffix}-2026-05-25"
    doc_b = f"POL-b-{suffix}-2026-05-25"
    await _create_doc_in_db(session_factory, doc_id=doc_a)
    await _create_doc_in_db(session_factory, doc_id=doc_b)
    searcher.chunks_to_return = [
        _chunk(chunk_id="c1", document_id=doc_a, content="alpha"),
        _chunk(chunk_id="c2", document_id=doc_b, content="bravo"),
    ]

    resp = client.post(
        "/queries",
        json={"query": "x"},
        headers={"Authorization": CAPTURADOR},
    )
    assert resp.status_code == 200
    query_id = resp.json()["queryId"]

    async with session_factory() as db:
        result = await db.execute(
            select(models.QueryCitationModel).where(
                models.QueryCitationModel.query_id == query_id
            )
        )
        rows = result.scalars().all()
    assert len(rows) == 2
    doc_ids = {r.document_id for r in rows}
    assert doc_ids == {doc_a, doc_b}


async def test_post_queries_no_results_persists_query_without_citations(
    client_with_fake_searcher,  # type: ignore[no-untyped-def]
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    """`hasResult=False` igual persiste la query (gap detection)."""
    client, searcher = client_with_fake_searcher
    searcher.chunks_to_return = []

    resp = client.post(
        "/queries",
        json={"query": "no matchea nada"},
        headers={"Authorization": CAPTURADOR},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["hasResult"] is False
    query_id = body["queryId"]

    async with session_factory() as db:
        result = await db.execute(
            select(models.QueryModel).where(models.QueryModel.id == query_id)
        )
        row = result.scalar_one()
        assert row.has_result is False
        assert row.text == "no matchea nada"

        citations = await db.execute(
            select(models.QueryCitationModel).where(
                models.QueryCitationModel.query_id == query_id
            )
        )
        assert len(citations.scalars().all()) == 0


async def test_post_queries_without_bearer_returns_401(
    client_with_fake_searcher,  # type: ignore[no-untyped-def]
) -> None:
    """Sin token → 401 (espejo del enforcement de los otros endpoints)."""
    client, _ = client_with_fake_searcher
    resp = client.post("/queries", json={"query": "x"})
    assert resp.status_code == 401
