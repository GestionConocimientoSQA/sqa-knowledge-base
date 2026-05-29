"""Tests unitarios del HybridSearcher (Fase 3.4).

Mismo enfoque que `test_rag_retriever.py`: fakes para `EmbedderPort` y
para el `session_factory`. Sin tocar Cohere ni PostgreSQL.

Estrategia:
- `_FakeEmbedder.embed_query` devuelve un vector determinista y registra
  el texto pedido.
- `_FakeSessionFactory` captura el SQL + params de cada `.execute()`.
  Permite aseverar que:
    1. Ambas CTE (vector_results + fts_results) están presentes,
    2. el FULL OUTER JOIN está,
    3. los pesos/boost/candidates/top_k entran como bind params,
    4. los filtros se aplican en AMBAS sub-queries.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest

from sqa_kb.ports.gateways import EmbeddingBatch
from sqa_kb.rag.hybrid_search import (
    DEFAULT_AUTHORITATIVE_BOOST,
    DEFAULT_CANDIDATES_PER_BRANCH,
    DEFAULT_FTS_WEIGHT,
    DEFAULT_VECTOR_WEIGHT,
    HybridChunk,
    HybridSearcher,
)

# ===========================================================================
# Fakes
# ===========================================================================


@dataclass
class _FakeEmbedder:
    seed: float = 0.1
    queries_seen: list[str] = field(default_factory=list)
    return_empty: bool = False

    async def embed_documents(self, texts: Sequence[str]) -> EmbeddingBatch:  # noqa: ARG002
        raise NotImplementedError

    async def embed_query(self, text: str) -> EmbeddingBatch:
        self.queries_seen.append(text)
        if self.return_empty:
            return EmbeddingBatch(
                vectors=(), input_tokens=0, cost_usd=0.0, model="fake"
            )
        vector = tuple([self.seed] + [0.0] * 1023)
        return EmbeddingBatch(
            vectors=(vector,),
            input_tokens=len(text),
            cost_usd=0.0,
            model="fake",
        )


@dataclass
class _CapturedCall:
    sql: str
    params: Mapping[str, Any]


class _FakeResult:
    def __init__(self, rows: Sequence[Mapping[str, Any]]) -> None:
        self._rows = list(rows)

    def mappings(self) -> _FakeResult:
        return self

    def all(self) -> list[Mapping[str, Any]]:
        return self._rows


class _FakeSession:
    def __init__(
        self, *, rows: Sequence[Mapping[str, Any]], captured: list[_CapturedCall]
    ) -> None:
        self._rows = rows
        self._captured = captured

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def execute(self, sql: Any, params: Mapping[str, Any]) -> _FakeResult:
        self._captured.append(_CapturedCall(sql=str(sql), params=dict(params)))
        return _FakeResult(self._rows)


@dataclass
class _FakeSessionFactory:
    rows: list[Mapping[str, Any]] = field(default_factory=list)
    captured: list[_CapturedCall] = field(default_factory=list)

    def __call__(self) -> _FakeSession:
        return _FakeSession(rows=self.rows, captured=self.captured)


_UNSET: Any = object()


def _row(
    *,
    chunk_id: str = "chk-1",
    document_id: str = "POL-test",
    chunk_index: int = 0,
    content: str = "Texto del chunk",
    metadata: Any = _UNSET,
    titulo: str = "Política",
    tipo: str = "POL",
    carpeta: str = "TEC",
    autoritativo: bool = False,
    vec_score: float = 0.8,
    fts_score: float = 0.5,
    combined_score: float = 0.71,
) -> dict[str, Any]:
    if metadata is _UNSET:
        metadata = {"section_title": "Intro"}
    return {
        "chunk_id": chunk_id,
        "document_id": document_id,
        "chunk_index": chunk_index,
        "content": content,
        "chunk_metadata": metadata,
        "doc_titulo": titulo,
        "doc_tipo": tipo,
        "doc_carpeta": carpeta,
        "doc_autoritativo": autoritativo,
        "vec_score": vec_score,
        "fts_score": fts_score,
        "combined_score": combined_score,
    }


# ===========================================================================
# search() — happy path + estructura del SQL
# ===========================================================================


async def test_search_embeds_query_and_returns_hybrid_chunks() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(
        rows=[_row(content="Match exacto", combined_score=0.93)]
    )
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    chunks = await searcher.search("playwright e2e", project_id="proj-test")

    assert embedder.queries_seen == ["playwright e2e"]
    assert len(chunks) == 1
    chunk = chunks[0]
    assert isinstance(chunk, HybridChunk)
    assert chunk.score == pytest.approx(0.93)
    assert chunk.vector_score == pytest.approx(0.8)
    assert chunk.fulltext_score == pytest.approx(0.5)
    assert chunk.snippet == "Match exacto"


async def test_search_sql_contains_both_ctes() -> None:
    """El SQL debe componer vector_results + fts_results + FULL OUTER JOIN."""
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    await searcher.search("q", project_id="proj-test")
    sql = factory.captured[0].sql

    assert "vector_results AS" in sql
    assert "fts_results AS" in sql
    assert "FULL OUTER JOIN" in sql
    # Combinación lineal explícita.
    assert "vec_score * :vec_weight + comb.fts_score * :fts_weight" in sql.replace(
        "comb.", ""
    ) or "vec_score * :vec_weight" in sql


async def test_search_sql_uses_spanish_plainto_tsquery() -> None:
    """El predicado FTS debe matchear EXACTO la expresión del índice GIN."""
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    await searcher.search("q", project_id="proj-test")
    sql = factory.captured[0].sql

    assert "to_tsvector('spanish', c.content)" in sql
    assert "plainto_tsquery('spanish', :query_text)" in sql


async def test_search_uses_ts_rank_cd_with_normalization_flag_32() -> None:
    """Sin flag 32, ts_rank_cd no está acotado y rompe la combinación lineal."""
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    await searcher.search("q", project_id="proj-test")
    # Normalizamos whitespace para que el SQL multilínea matchee igual
    # que single-line.
    sql_flat = " ".join(factory.captured[0].sql.split())

    assert "ts_rank_cd(" in sql_flat
    # El tercer argumento de `ts_rank_cd` (tras el tsvector y la tsquery)
    # debe ser `32`.
    assert ":query_text), 32" in sql_flat


# ===========================================================================
# Cortocircuitos
# ===========================================================================


async def test_search_top_k_zero_returns_empty_without_embedding() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[_row()])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    out = await searcher.search("q", project_id="proj-test", top_k=0)
    assert out == []
    assert embedder.queries_seen == []
    assert factory.captured == []


async def test_search_empty_query_returns_empty_without_embedding() -> None:
    """Query vacía → plainto_tsquery vacío → matchea cero. Cortocircuito
    para ahorrar el embed."""
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[_row()])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    out = await searcher.search("", project_id="proj-test")
    assert out == []
    assert embedder.queries_seen == []


async def test_search_whitespace_only_query_returns_empty() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[_row()])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    out = await searcher.search("   \t\n  ", project_id="proj-test")
    assert out == []
    assert embedder.queries_seen == []


async def test_search_handles_embedder_returning_empty_vectors() -> None:
    embedder = _FakeEmbedder(return_empty=True)
    factory = _FakeSessionFactory(rows=[_row()])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    out = await searcher.search("q", project_id="proj-test")
    assert out == []
    assert factory.captured == []


async def test_search_no_rows_returns_empty() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    out = await searcher.search("nada matchea", project_id="proj-test")
    assert out == []
    assert len(factory.captured) == 1


# ===========================================================================
# Pesos + boost + candidates como bind params
# ===========================================================================


async def test_search_default_weights_passed_as_params() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    await searcher.search("q", project_id="proj-test")
    p = factory.captured[0].params

    assert p["vec_weight"] == pytest.approx(DEFAULT_VECTOR_WEIGHT)
    assert p["fts_weight"] == pytest.approx(DEFAULT_FTS_WEIGHT)
    assert p["boost"] == pytest.approx(DEFAULT_AUTHORITATIVE_BOOST)
    assert p["candidates"] == DEFAULT_CANDIDATES_PER_BRANCH


async def test_search_custom_weights_at_construction() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(
        embedder=embedder,
        session_factory=factory,
        vector_weight=0.5,
        fts_weight=0.5,
    )

    await searcher.search("q", project_id="proj-test")
    p = factory.captured[0].params
    assert p["vec_weight"] == pytest.approx(0.5)
    assert p["fts_weight"] == pytest.approx(0.5)


async def test_search_custom_candidates_at_construction() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(
        embedder=embedder, session_factory=factory, candidates_per_branch=100
    )

    await searcher.search("q", project_id="proj-test")
    assert factory.captured[0].params["candidates"] == 100


async def test_search_boost_override_per_call() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    await searcher.search("q", project_id="proj-test", authoritative_boost=1.5)
    assert factory.captured[0].params["boost"] == pytest.approx(1.5)


async def test_search_top_k_propagates_to_sql() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    await searcher.search("q", project_id="proj-test", top_k=12)
    assert factory.captured[0].params["top_k"] == 12


# ===========================================================================
# Filtros aplican en AMBAS CTE
# ===========================================================================


async def test_search_carpetas_filter_applied_in_both_ctes() -> None:
    """Si solo se filtrara una rama, la otra traería chunks fuera del
    scope y contaminarían el JOIN."""
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    await searcher.search("q", project_id="proj-test", carpetas=["TEC", "ARQ"])
    sql = factory.captured[0].sql

    # El filtro debe aparecer 2 veces (una por CTE).
    assert sql.count("d.carpeta IN") == 2
    # Y los valores en params, no en el SQL.
    assert "TEC" not in sql
    assert factory.captured[0].params["carpetas"] == ["TEC", "ARQ"]


async def test_search_tipos_filter_applied_in_both_ctes() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    await searcher.search("q", project_id="proj-test", tipos=["POL"])
    sql = factory.captured[0].sql

    assert sql.count("d.tipo IN") == 2
    assert factory.captured[0].params["tipos"] == ["POL"]


async def test_search_authoritative_only_applied_in_both_ctes() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    await searcher.search("q", project_id="proj-test", authoritative_only=True)
    sql = factory.captured[0].sql

    assert sql.count("d.autoritativo = TRUE") == 2


async def test_search_empty_filter_lists_no_filter_clause() -> None:
    """`carpetas=[]` y `tipos=[]` = sin filtro — espejo del retriever."""
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    await searcher.search("q", project_id="proj-test", carpetas=[], tipos=[])
    sql = factory.captured[0].sql
    assert "d.carpeta IN" not in sql
    assert "d.tipo IN" not in sql


async def test_search_no_filters_keeps_base_predicates() -> None:
    """Sin filtros, igual sigue el predicado del FTS y del NOT NULL."""
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    await searcher.search("q", project_id="proj-test")
    sql = factory.captured[0].sql
    assert "c.embedding IS NOT NULL" in sql
    assert "@@ plainto_tsquery" in sql


# ===========================================================================
# qvec + query_text + boost en SQL
# ===========================================================================


async def test_search_qvec_serialized_as_pgvector_literal() -> None:
    embedder = _FakeEmbedder(seed=0.42)
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    await searcher.search("q", project_id="proj-test")
    p = factory.captured[0].params
    assert isinstance(p["qvec"], str)
    assert p["qvec"].startswith("[") and p["qvec"].endswith("]")
    assert "CAST(:qvec AS vector)" in factory.captured[0].sql


async def test_search_query_text_passed_as_bind_param() -> None:
    """El input del usuario nunca se concatena al SQL."""
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    await searcher.search("playwright '; DROP TABLE documents;--", project_id="proj-test")
    sql = factory.captured[0].sql
    # No hay concatenación del input al SQL.
    assert "DROP TABLE" not in sql
    assert "playwright" not in sql
    # Sí entra como bind param.
    assert factory.captured[0].params["query_text"] == (
        "playwright '; DROP TABLE documents;--"
    )


async def test_search_boost_applied_in_combined_score() -> None:
    """El boost se aplica al score combinado, no solo a una rama."""
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    await searcher.search("q", project_id="proj-test")
    sql = factory.captured[0].sql

    # CASE con boost aplicado al combined_score.
    assert "CASE WHEN d.autoritativo THEN :boost" in sql


# ===========================================================================
# HybridChunk inmutabilidad + edge cases
# ===========================================================================


async def test_hybrid_chunk_is_immutable() -> None:
    chunk = HybridChunk(
        chunk_id="c1",
        document_id="d1",
        chunk_index=0,
        content="x",
        snippet="x",
        section_title="",
        score=0.5,
        vector_score=0.3,
        fulltext_score=0.2,
        document_title="T",
        document_type="POL",
        document_category="TEC",
        authoritative=False,
    )
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        chunk.score = 1.0  # type: ignore[misc]


async def test_search_handles_null_chunk_metadata() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[_row(metadata=None)])
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    out = await searcher.search("q", project_id="proj-test")
    assert out[0].section_title == ""


async def test_search_snippet_uses_custom_max_chars() -> None:
    embedder = _FakeEmbedder()
    long_text = "palabra " * 200
    factory = _FakeSessionFactory(rows=[_row(content=long_text)])
    searcher = HybridSearcher(
        embedder=embedder, session_factory=factory, snippet_max_chars=40
    )

    out = await searcher.search("q", project_id="proj-test")
    assert len(out[0].snippet) == 40
    assert out[0].snippet.endswith("…")
    assert out[0].content == long_text


async def test_search_chunk_only_in_vector_branch_has_zero_fts() -> None:
    """COALESCE en la CTE combined → un chunk que solo matcheó por vector
    llega con fts_score=0."""
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(
        rows=[_row(vec_score=0.85, fts_score=0.0, combined_score=0.595)]
    )
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    out = await searcher.search("q", project_id="proj-test")
    assert out[0].vector_score == pytest.approx(0.85)
    assert out[0].fulltext_score == 0.0


async def test_search_chunk_only_in_fts_branch_has_zero_vector() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(
        rows=[_row(vec_score=0.0, fts_score=0.9, combined_score=0.27)]
    )
    searcher = HybridSearcher(embedder=embedder, session_factory=factory)

    out = await searcher.search("q", project_id="proj-test")
    assert out[0].vector_score == 0.0
    assert out[0].fulltext_score == pytest.approx(0.9)
