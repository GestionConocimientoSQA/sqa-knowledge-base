"""Tests del endpoint POST /queries (Fase 3.5).

Usan `TestClient` + `dependency_overrides` para inyectar fakes de
`KbSearcher`, `QueryRepository` y `CurrentUser`. Sin DB.

El test integration end-to-end contra Postgres real va en
`tests/integration/test_api_queries_pg.py`.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from sqa_kb.api.dependencies import (
    get_current_user,
    get_kb_searcher,
    get_query_repo,
)
from sqa_kb.domain.entities import Query, QueryCitation, User
from sqa_kb.domain.value_objects import RoleId
from sqa_kb.main import create_app
from sqa_kb.rag.hybrid_search import HybridChunk


# ===========================================================================
# Fakes
# ===========================================================================


def _chunk(
    *,
    chunk_id: str = "chk-1",
    document_id: str = "TEC-foo-2026-01-01",
    chunk_index: int = 0,
    score: float = 0.85,
    document_title: str = "Doc foo",
    document_type: str = "POL",
    document_category: str = "TEC",
    authoritative: bool = False,
    content: str = "Contenido completo del chunk.",
    section_title: str = "Intro",
) -> HybridChunk:
    return HybridChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=chunk_index,
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
class _FakeSearcher:
    chunks_to_return: list[HybridChunk] = field(default_factory=list)
    last_call: dict | None = None  # type: ignore[type-arg]

    async def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        carpetas: Iterable[str] | None = None,
        tipos: Iterable[str] | None = None,
        authoritative_only: bool = False,
        authoritative_boost: float | None = None,
    ) -> Sequence[HybridChunk]:
        self.last_call = {
            "query": query,
            "top_k": top_k,
            "carpetas": list(carpetas) if carpetas else None,
            "tipos": list(tipos) if tipos else None,
            "authoritative_only": authoritative_only,
            "authoritative_boost": authoritative_boost,
        }
        return list(self.chunks_to_return)


@dataclass
class _FakeQueryRepo:
    recorded: list[Query] = field(default_factory=list)
    citations: list[QueryCitation] = field(default_factory=list)

    async def record(self, query: Query) -> Query:
        self.recorded.append(query)
        return query

    async def add_citation(self, citation: QueryCitation) -> QueryCitation:
        self.citations.append(citation)
        return citation

    async def hot_topics(self, *, since_days: int = 30, limit: int = 8):  # type: ignore[no-untyped-def] # noqa: ARG002
        return []


def _user(oid: str = "stub-capturador-00000000") -> User:
    now = datetime.now(UTC)
    return User(
        oid=oid,
        email="t@sqasa.co",
        name="Tester",
        role_id=RoleId.CAPTURADOR,
        carpetas_owned=[],
        created_at=now,
        updated_at=now,
    )


# ===========================================================================
# Fixture
# ===========================================================================


@pytest.fixture
def client_with_overrides() -> Iterator[tuple[TestClient, _FakeSearcher, _FakeQueryRepo]]:
    """TestClient con `dependency_overrides` para los fakes del test."""
    app = create_app()
    searcher = _FakeSearcher()
    query_repo = _FakeQueryRepo()
    app.dependency_overrides[get_kb_searcher] = lambda: searcher
    app.dependency_overrides[get_query_repo] = lambda: query_repo
    app.dependency_overrides[get_current_user] = lambda: _user()
    with TestClient(app) as client:
        yield client, searcher, query_repo
    app.dependency_overrides.clear()


# ===========================================================================
# Happy path
# ===========================================================================
#
# Auth (401 sin Bearer) está cubierto por `tests/integration/test_auth.py`
# contra todos los endpoints autenticados — el `CurrentUser` dependency
# es el mismo aquí.


def test_post_queries_returns_chunks_and_persists_query(
    client_with_overrides,  # type: ignore[no-untyped-def]
) -> None:
    client, searcher, query_repo = client_with_overrides
    searcher.chunks_to_return = [
        _chunk(chunk_id="c1", document_id="TEC-foo", score=0.9),
        _chunk(chunk_id="c2", document_id="TEC-bar", score=0.7),
    ]

    resp = client.post("/queries", json={"query": "flaky tests"})
    assert resp.status_code == 200
    body = resp.json()

    # Response shape (camelCase wire).
    assert body["totalReturned"] == 2
    assert body["hasResult"] is True
    assert len(body["items"]) == 2
    assert body["items"][0]["chunkId"] == "c1"
    assert body["items"][0]["score"] == pytest.approx(0.9)
    assert body["items"][0]["vectorScore"] == pytest.approx(0.9)
    assert body["items"][0]["documentTitle"] == "Doc foo"

    # Persistencia: 1 query + 2 citaciones.
    assert len(query_repo.recorded) == 1
    assert query_repo.recorded[0].text == "flaky tests"
    assert query_repo.recorded[0].has_result is True
    assert query_repo.recorded[0].user_oid == "stub-capturador-00000000"
    assert len(query_repo.citations) == 2
    cited_ids = {c.document_id for c in query_repo.citations}
    assert cited_ids == {"TEC-foo", "TEC-bar"}


def test_post_queries_no_results_persists_query_with_has_result_false(
    client_with_overrides,  # type: ignore[no-untyped-def]
) -> None:
    client, searcher, query_repo = client_with_overrides
    searcher.chunks_to_return = []  # sin matches

    resp = client.post("/queries", json={"query": "no existe esto"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["hasResult"] is False
    assert body["totalReturned"] == 0
    assert body["items"] == []

    # Sí se persiste — alimenta gap detection del dashboard.
    assert len(query_repo.recorded) == 1
    assert query_repo.recorded[0].has_result is False
    # Sin citaciones.
    assert query_repo.citations == []


# ===========================================================================
# Filtros
# ===========================================================================


def test_post_queries_passes_filters_to_searcher(
    client_with_overrides,  # type: ignore[no-untyped-def]
) -> None:
    client, searcher, _ = client_with_overrides

    resp = client.post(
        "/queries",
        json={
            "query": "x",
            "topK": 3,
            "carpetas": ["TEC", "ARQ"],
            "tipos": ["POL"],
            "authoritativeOnly": True,
        },
    )
    assert resp.status_code == 200

    assert searcher.last_call is not None
    assert searcher.last_call["query"] == "x"
    assert searcher.last_call["top_k"] == 3
    assert searcher.last_call["carpetas"] == ["TEC", "ARQ"]
    assert searcher.last_call["tipos"] == ["POL"]
    assert searcher.last_call["authoritative_only"] is True


def test_post_queries_no_filters_defaults(
    client_with_overrides,  # type: ignore[no-untyped-def]
) -> None:
    """Sin filtros en body, el searcher recibe None / False / defaults."""
    client, searcher, _ = client_with_overrides

    resp = client.post("/queries", json={"query": "x"})
    assert resp.status_code == 200

    assert searcher.last_call["top_k"] == 5  # default del schema
    assert searcher.last_call["carpetas"] is None
    assert searcher.last_call["tipos"] is None
    assert searcher.last_call["authoritative_only"] is False


# ===========================================================================
# Validación
# ===========================================================================


def test_post_queries_empty_query_returns_422(
    client_with_overrides,  # type: ignore[no-untyped-def]
) -> None:
    client, _, _ = client_with_overrides
    resp = client.post("/queries", json={"query": ""})
    assert resp.status_code == 422


def test_post_queries_top_k_out_of_range_returns_422(
    client_with_overrides,  # type: ignore[no-untyped-def]
) -> None:
    client, _, _ = client_with_overrides
    resp = client.post("/queries", json={"query": "x", "topK": 100})
    assert resp.status_code == 422


def test_post_queries_top_k_zero_returns_422(
    client_with_overrides,  # type: ignore[no-untyped-def]
) -> None:
    client, _, _ = client_with_overrides
    resp = client.post("/queries", json={"query": "x", "topK": 0})
    assert resp.status_code == 422


def test_post_queries_invalid_carpeta_returns_422(
    client_with_overrides,  # type: ignore[no-untyped-def]
) -> None:
    """`carpetas` debe contener `CategoryCode` válidos."""
    client, _, _ = client_with_overrides
    resp = client.post(
        "/queries", json={"query": "x", "carpetas": ["NOEXISTE"]}
    )
    assert resp.status_code == 422


def test_post_queries_invalid_tipo_returns_422(
    client_with_overrides,  # type: ignore[no-untyped-def]
) -> None:
    client, _, _ = client_with_overrides
    resp = client.post("/queries", json={"query": "x", "tipos": ["NOTIPO"]})
    assert resp.status_code == 422


# ===========================================================================
# Citation: section fallback
# ===========================================================================


def test_post_queries_chunk_without_section_persists_dash_placeholder(
    client_with_overrides,  # type: ignore[no-untyped-def]
) -> None:
    """`QueryCitation.section` es NonEmptyStr — si el chunk no tiene
    section_title, el endpoint persiste un guion como placeholder."""
    client, searcher, query_repo = client_with_overrides
    searcher.chunks_to_return = [
        _chunk(chunk_id="c1", document_id="DOC", section_title="")
    ]

    resp = client.post("/queries", json={"query": "x"})
    assert resp.status_code == 200
    assert len(query_repo.citations) == 1
    assert query_repo.citations[0].section == "—"
