"""Tests unitarios del VectorRetriever (Fase 3.3).

Usan fakes para `EmbedderPort` y para el `session_factory` — sin tocar
Cohere ni PostgreSQL. La integración real con PG y pgvector va en
`tests/integration/test_rag_retriever_pg.py`.

Estrategia:
- `_FakeEmbedder.embed_query` devuelve un vector determinista y registra
  el texto pedido (para verificar que el retriever lo usó).
- `_FakeSessionFactory` captura el SQL + params de cada `.execute()` y
  devuelve un set de rows predefinido. Así podemos aseverar:
    1. los filtros se inyectan como bind params (no como string
       concatenado al SQL → defensa anti SQL injection),
    2. el SELECT incluye el boost y el ORDER BY usa la distancia cruda.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest

from sqa_kb.ports.gateways import EmbeddingBatch
from sqa_kb.rag.retriever import (
    DEFAULT_AUTHORITATIVE_BOOST,
    DEFAULT_SNIPPET_MAX_CHARS,
    RetrievedChunk,
    VectorRetriever,
    _build_snippet,
    _format_pgvector_literal,
)

# ===========================================================================
# Fakes
# ===========================================================================


@dataclass
class _FakeEmbedder:
    """Devuelve un vector determinista para todas las queries."""

    seed: float = 0.1
    queries_seen: list[str] = field(default_factory=list)
    return_empty: bool = False

    async def embed_documents(self, texts: Sequence[str]) -> EmbeddingBatch:  # noqa: ARG002
        raise NotImplementedError("retriever no llama embed_documents")

    async def embed_query(self, text: str) -> EmbeddingBatch:
        self.queries_seen.append(text)
        if self.return_empty:
            return EmbeddingBatch(
                vectors=(),
                input_tokens=0,
                cost_usd=0.0,
                model="embed-multilingual-v3.0",
            )
        vector = tuple([self.seed] + [0.0] * 1023)
        return EmbeddingBatch(
            vectors=(vector,),
            input_tokens=len(text),
            cost_usd=0.00001,
            model="embed-multilingual-v3.0",
        )


@dataclass
class _CapturedCall:
    sql: str
    params: Mapping[str, Any]


class _FakeResult:
    """Imita `Result` de SQLAlchemy: tiene `.mappings().all()`."""

    def __init__(self, rows: Sequence[Mapping[str, Any]]) -> None:
        self._rows = list(rows)

    def mappings(self) -> "_FakeResult":
        return self

    def all(self) -> list[Mapping[str, Any]]:
        return self._rows


class _FakeSession:
    def __init__(
        self,
        *,
        rows: Sequence[Mapping[str, Any]],
        captured: list[_CapturedCall],
    ) -> None:
        self._rows = rows
        self._captured = captured

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def execute(self, sql: Any, params: Mapping[str, Any]) -> _FakeResult:
        # `sql` es un TextClause; lo guardamos como string para inspección.
        self._captured.append(_CapturedCall(sql=str(sql), params=dict(params)))
        return _FakeResult(self._rows)


@dataclass
class _FakeSessionFactory:
    """Imita `async_sessionmaker`: callable que devuelve un context manager."""

    rows: list[Mapping[str, Any]] = field(default_factory=list)
    captured: list[_CapturedCall] = field(default_factory=list)

    def __call__(self) -> _FakeSession:
        return _FakeSession(rows=self.rows, captured=self.captured)


_UNSET: Any = object()


def _row(
    *,
    chunk_id: str = "chk-1",
    document_id: str = "POL-test-2026-01-01",
    chunk_index: int = 0,
    content: str = "Texto del chunk",
    metadata: Any = _UNSET,
    titulo: str = "Política de QA",
    tipo: str = "POL",
    carpeta: str = "TEC",
    autoritativo: bool = False,
    score: float = 0.8,
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
        "score": score,
    }


# ===========================================================================
# Helpers de formato
# ===========================================================================


def test_format_pgvector_literal_basic() -> None:
    """Convierte una lista de floats al formato `'[...]'` que pgvector acepta."""
    out = _format_pgvector_literal([0.1, 0.2, 0.3])
    assert out.startswith("[") and out.endswith("]")
    # Cada componente parseable a float.
    components = out.strip("[]").split(",")
    assert [float(c) for c in components] == pytest.approx([0.1, 0.2, 0.3])


def test_format_pgvector_literal_coerces_to_float() -> None:
    """Inputs `int` o `numpy` son normalizados a float."""
    out = _format_pgvector_literal([1, 2, 3])
    assert "1.0" in out and "3.0" in out


def test_build_snippet_pass_through_when_short() -> None:
    out = _build_snippet("corto", max_chars=240)
    assert out == "corto"


def test_build_snippet_truncates_with_ellipsis() -> None:
    long_text = "x" * 500
    out = _build_snippet(long_text, max_chars=100)
    assert out.endswith("…")
    assert len(out) == 100


def test_build_snippet_collapses_whitespace() -> None:
    out = _build_snippet("línea uno\nlínea dos\t\ttab", max_chars=240)
    assert "\n" not in out
    assert "\t" not in out
    assert out == "línea uno línea dos tab"


# ===========================================================================
# retrieve() — happy path
# ===========================================================================


async def test_retrieve_embeds_query_text_and_returns_chunks() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[_row(content="Resultado de prueba.", score=0.91)])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    chunks = await retriever.retrieve("¿qué dice la política de QA?")

    assert embedder.queries_seen == ["¿qué dice la política de QA?"]
    assert len(chunks) == 1
    chunk = chunks[0]
    assert isinstance(chunk, RetrievedChunk)
    assert chunk.chunk_id == "chk-1"
    assert chunk.score == pytest.approx(0.91)
    assert chunk.snippet == "Resultado de prueba."
    assert chunk.section_title == "Intro"
    assert chunk.authoritative is False


async def test_retrieve_top_k_zero_returns_empty_and_does_not_embed() -> None:
    """Cortocircuito: top_k <= 0 evita gastar tokens en el embedder."""
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[_row()])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    out = await retriever.retrieve("query", top_k=0)
    assert out == []
    assert embedder.queries_seen == []
    assert factory.captured == []


async def test_retrieve_no_rows_returns_empty_list() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    out = await retriever.retrieve("nada matchea")
    assert out == []
    assert len(factory.captured) == 1  # sí pegó a la DB


async def test_retrieve_handles_embedder_returning_empty_vectors() -> None:
    """Si el embedder devuelve `vectors=()`, no hay que romper la DB."""
    embedder = _FakeEmbedder(return_empty=True)
    factory = _FakeSessionFactory(rows=[_row()])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    out = await retriever.retrieve("query")
    assert out == []
    assert factory.captured == []  # ni intentó consultar


# ===========================================================================
# retrieve() — filtros pasan como bind params (anti SQL injection)
# ===========================================================================


async def test_retrieve_passes_carpetas_as_bind_param_not_string() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    await retriever.retrieve("q", carpetas=["TEC", "ARQ"])
    call = factory.captured[0]

    # El SQL contiene placeholder, no los valores concatenados.
    assert "d.carpeta IN" in call.sql
    assert "TEC" not in call.sql
    assert "ARQ" not in call.sql
    # Los valores entran por params (lista — SQLAlchemy expanding bind).
    assert call.params["carpetas"] == ["TEC", "ARQ"]


async def test_retrieve_passes_tipos_as_bind_param() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    await retriever.retrieve("q", tipos=["POL", "PROC"])
    call = factory.captured[0]

    assert "d.tipo IN" in call.sql
    assert "POL" not in call.sql
    assert call.params["tipos"] == ["POL", "PROC"]


async def test_retrieve_authoritative_only_adds_predicate() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    await retriever.retrieve("q", authoritative_only=True)
    call = factory.captured[0]

    assert "d.autoritativo = TRUE" in call.sql


async def test_retrieve_omits_filters_when_not_provided() -> None:
    """Sin filtros, el SQL no debe contener `carpeta IN` ni `tipo IN`."""
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    await retriever.retrieve("q")
    call = factory.captured[0]

    assert "d.carpeta IN" not in call.sql
    assert "d.tipo IN" not in call.sql
    assert "d.autoritativo = TRUE" not in call.sql
    # Igual el predicado base contra NULL siempre va.
    assert "c.embedding IS NOT NULL" in call.sql


async def test_retrieve_empty_filter_lists_are_treated_as_no_filter() -> None:
    """`carpetas=[]` es alias semántico de "sin filtro" — espejo del contrato
    del frontend (`apps/frontend/src/lib/api/documents.ts`)."""
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    await retriever.retrieve("q", carpetas=[], tipos=[])
    call = factory.captured[0]
    assert "d.carpeta IN" not in call.sql
    assert "d.tipo IN" not in call.sql


# ===========================================================================
# retrieve() — boost autoritativos
# ===========================================================================


async def test_retrieve_default_boost_is_passed_as_param() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    await retriever.retrieve("q")
    call = factory.captured[0]

    assert call.params["boost"] == pytest.approx(DEFAULT_AUTHORITATIVE_BOOST)
    # El SQL aplica el CASE con :boost para autoritativos.
    assert "CASE WHEN d.autoritativo THEN :boost" in call.sql


async def test_retrieve_boost_override_per_call() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    await retriever.retrieve("q", authoritative_boost=1.5)
    assert factory.captured[0].params["boost"] == pytest.approx(1.5)


async def test_retrieve_boost_override_at_construction() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    retriever = VectorRetriever(
        embedder=embedder, session_factory=factory, default_authoritative_boost=1.3
    )

    await retriever.retrieve("q")
    assert factory.captured[0].params["boost"] == pytest.approx(1.3)


# ===========================================================================
# retrieve() — re-rank en Python + top_k + qvec
# ===========================================================================


async def test_retrieve_reranks_by_score_desc() -> None:
    """El SELECT ya devuelve el score con boost; el retriever ordena desc.

    La DB ordenó por distancia cruda (para usar HNSW). Acá probamos que el
    re-rank final respeta el score final.
    """
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(
        rows=[
            _row(chunk_id="A", score=0.70, autoritativo=False),
            _row(chunk_id="B", score=0.95, autoritativo=True),  # boosted ganador
            _row(chunk_id="C", score=0.85, autoritativo=False),
        ]
    )
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    out = await retriever.retrieve("q")
    assert [c.chunk_id for c in out] == ["B", "C", "A"]


async def test_retrieve_top_k_propagates_to_sql_param() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    await retriever.retrieve("q", top_k=12)
    assert factory.captured[0].params["top_k"] == 12


async def test_retrieve_qvec_is_serialized_pgvector_literal() -> None:
    """El vector se manda como string `'[...]'` casteable a `::vector`."""
    embedder = _FakeEmbedder(seed=0.42)
    factory = _FakeSessionFactory(rows=[])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    await retriever.retrieve("q")
    qvec = factory.captured[0].params["qvec"]
    assert isinstance(qvec, str)
    assert qvec.startswith("[") and qvec.endswith("]")
    # El primer componente vino del seed.
    first = float(qvec.strip("[]").split(",")[0])
    assert first == pytest.approx(0.42)
    # El SQL hace el cast explícito.
    assert "CAST(:qvec AS vector)" in factory.captured[0].sql


# ===========================================================================
# retrieve() — edge cases de metadata + snippet
# ===========================================================================


async def test_retrieve_handles_chunk_without_section_title_metadata() -> None:
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[_row(metadata={"strategy": "semantic"})])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    out = await retriever.retrieve("q")
    assert out[0].section_title == ""


async def test_retrieve_handles_null_chunk_metadata() -> None:
    """Defensa: si la columna metadata vino como None (no debería, pero...),
    no debe romper — `section_title` queda vacío."""
    embedder = _FakeEmbedder()
    factory = _FakeSessionFactory(rows=[_row(metadata=None)])
    retriever = VectorRetriever(embedder=embedder, session_factory=factory)

    out = await retriever.retrieve("q")
    assert out[0].section_title == ""


async def test_retrieve_snippet_respects_construction_max_chars() -> None:
    embedder = _FakeEmbedder()
    long = "palabra " * 200
    factory = _FakeSessionFactory(rows=[_row(content=long)])
    retriever = VectorRetriever(
        embedder=embedder, session_factory=factory, snippet_max_chars=50
    )

    out = await retriever.retrieve("q")
    assert len(out[0].snippet) == 50
    assert out[0].snippet.endswith("…")
    # El `content` original queda intacto.
    assert out[0].content == long


async def test_retrieved_chunk_is_immutable() -> None:
    """`RetrievedChunk` es `frozen` — defensa contra mutación accidental
    desde callers que asumen referencia compartida."""
    chunk = RetrievedChunk(
        chunk_id="c1",
        document_id="d1",
        chunk_index=0,
        content="x",
        snippet="x",
        section_title="",
        score=0.5,
        document_title="T",
        document_type="POL",
        document_category="TEC",
        authoritative=False,
    )
    with pytest.raises(Exception):  # FrozenInstanceError de dataclass
        chunk.score = 1.0  # type: ignore[misc]


async def test_default_snippet_max_chars_is_240() -> None:
    """Smoke: la constante exportada coincide con el default del retriever."""
    assert DEFAULT_SNIPPET_MAX_CHARS == 240
