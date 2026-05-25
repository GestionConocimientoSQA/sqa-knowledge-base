"""Tests del adapter CohereEmbedder.

Mockean el SDK con stubs minimalistas — no se golpea api.cohere.com.
Los stubs replican la forma de los objetos del SDK:
- EmbedByTypeResponse.embeddings.float: lista de listas de floats.
- EmbedByTypeResponse.meta.billed_units.input_tokens: int.

Cubre happy path + edge cases + límites de batch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from sqa_kb.adapters.embeddings.cohere import MAX_BATCH_SIZE, CohereEmbedder

# ===========================================================================
# Fakes
# ===========================================================================


@dataclass
class _FakeBilledUnits:
    input_tokens: int = 0


@dataclass
class _FakeMeta:
    billed_units: _FakeBilledUnits = field(default_factory=_FakeBilledUnits)


@dataclass
class _FakeEmbeddings:
    """Imita `EmbedByTypeResponse.embeddings`."""

    float: list[list[float]] = field(default_factory=list)


@dataclass
class _FakeResponse:
    embeddings: _FakeEmbeddings = field(default_factory=_FakeEmbeddings)
    meta: _FakeMeta = field(default_factory=_FakeMeta)


@dataclass
class _FakeCohere:
    """Imita `AsyncClientV2`. Solo necesita `.embed(...)`."""

    response: _FakeResponse = field(default_factory=_FakeResponse)
    last_kwargs: dict[str, Any] = field(default_factory=dict)
    raise_on_call: Exception | None = None

    async def embed(self, **kwargs: Any) -> _FakeResponse:
        self.last_kwargs = kwargs
        if self.raise_on_call is not None:
            raise self.raise_on_call
        return self.response


# ===========================================================================
# embed_documents
# ===========================================================================


async def test_embed_documents_happy_path() -> None:
    vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    client = _FakeCohere(
        response=_FakeResponse(
            embeddings=_FakeEmbeddings(float=vectors),
            meta=_FakeMeta(billed_units=_FakeBilledUnits(input_tokens=42)),
        )
    )
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]

    result = await embedder.embed_documents(["hola", "mundo"])

    assert result.vectors == ((0.1, 0.2, 0.3), (0.4, 0.5, 0.6))
    assert result.input_tokens == 42
    assert result.model == "embed-multilingual-v3.0"
    # 42 * 0.10 / 1M = 0.0000042
    assert result.cost_usd == pytest.approx(4.2e-6, rel=1e-4)


async def test_embed_documents_uses_search_document_input_type() -> None:
    """Cohere distingue indexar vs buscar — al indexar mandamos `search_document`."""
    client = _FakeCohere()
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    await embedder.embed_documents(["x"])
    assert client.last_kwargs["input_type"] == "search_document"


async def test_embed_documents_passes_default_model() -> None:
    client = _FakeCohere()
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    await embedder.embed_documents(["x"])
    assert client.last_kwargs["model"] == "embed-multilingual-v3.0"


async def test_embed_documents_accepts_custom_model() -> None:
    client = _FakeCohere()
    embedder = CohereEmbedder(
        api_key="t",
        model="embed-multilingual-light-v3.0",
        client=client,  # type: ignore[arg-type]
    )
    await embedder.embed_documents(["x"])
    assert client.last_kwargs["model"] == "embed-multilingual-light-v3.0"


async def test_embed_documents_requests_float_type() -> None:
    client = _FakeCohere()
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    await embedder.embed_documents(["x"])
    assert client.last_kwargs["embedding_types"] == ["float"]


# ===========================================================================
# embed_documents — edge cases
# ===========================================================================


async def test_embed_documents_empty_raises() -> None:
    client = _FakeCohere()
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="texts vacía"):
        await embedder.embed_documents([])


async def test_embed_documents_oversize_batch_raises() -> None:
    """Batch > 96 → ValueError. El indexer debe dividir antes."""
    client = _FakeCohere()
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    too_many = ["x"] * (MAX_BATCH_SIZE + 1)
    with pytest.raises(ValueError, match="batch demasiado grande"):
        await embedder.embed_documents(too_many)


async def test_embed_documents_exact_max_batch_works() -> None:
    """96 textos exactos pasan sin error."""
    client = _FakeCohere(
        response=_FakeResponse(
            embeddings=_FakeEmbeddings(float=[[0.0] * 1024 for _ in range(96)])
        )
    )
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    result = await embedder.embed_documents(["x"] * 96)
    assert len(result.vectors) == 96


async def test_embed_documents_handles_missing_billed_units() -> None:
    """Sin meta.billed_units → input_tokens=0, cost=0 (defensivo)."""
    response = _FakeResponse(
        embeddings=_FakeEmbeddings(float=[[0.1]]),
    )
    response.meta = None  # type: ignore[assignment]
    client = _FakeCohere(response=response)
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    result = await embedder.embed_documents(["x"])
    assert result.input_tokens == 0
    assert result.cost_usd == 0.0


# ===========================================================================
# embed_query
# ===========================================================================


async def test_embed_query_happy_path() -> None:
    client = _FakeCohere(
        response=_FakeResponse(
            embeddings=_FakeEmbeddings(float=[[0.7, 0.8, 0.9]]),
            meta=_FakeMeta(billed_units=_FakeBilledUnits(input_tokens=5)),
        )
    )
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    result = await embedder.embed_query("qué son flaky tests")
    assert result.vectors == ((0.7, 0.8, 0.9),)
    assert result.input_tokens == 5


async def test_embed_query_uses_search_query_input_type() -> None:
    """Al buscar, Cohere espera `search_query` para mejorar recall."""
    client = _FakeCohere()
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    await embedder.embed_query("x")
    assert client.last_kwargs["input_type"] == "search_query"


async def test_embed_query_sends_only_one_text() -> None:
    """Aunque el SDK acepta lista, embed_query pasa un solo elemento."""
    client = _FakeCohere()
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    await embedder.embed_query("la pregunta")
    assert client.last_kwargs["texts"] == ["la pregunta"]


async def test_embed_query_empty_raises() -> None:
    client = _FakeCohere()
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="text vacío"):
        await embedder.embed_query("")


async def test_embed_query_whitespace_only_raises() -> None:
    client = _FakeCohere()
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="text vacío"):
        await embedder.embed_query("   \n\t")


# ===========================================================================
# Robustez del adapter
# ===========================================================================


async def test_propagates_sdk_exceptions() -> None:
    """Errores del SDK suben tal cual — el caller decide retry / degradar."""
    client = _FakeCohere(raise_on_call=RuntimeError("cohere 500"))
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="cohere 500"):
        await embedder.embed_documents(["x"])


async def test_response_with_empty_embeddings_list() -> None:
    """Edge: SDK devuelve embeddings vacíos (no debería pero defensivo)."""
    client = _FakeCohere(
        response=_FakeResponse(embeddings=_FakeEmbeddings(float=[]))
    )
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    result = await embedder.embed_documents(["x"])
    assert result.vectors == ()


async def test_vectors_are_tuples_not_lists() -> None:
    """EmbeddingBatch usa tuples (immutable) — sanity check."""
    client = _FakeCohere(
        response=_FakeResponse(
            embeddings=_FakeEmbeddings(float=[[1.0, 2.0]])
        )
    )
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    result = await embedder.embed_documents(["x"])
    assert isinstance(result.vectors, tuple)
    assert isinstance(result.vectors[0], tuple)


async def test_floats_in_vector_are_python_floats() -> None:
    """Algunos SDKs devuelven np.float32 — verificamos coerce a float Python."""
    client = _FakeCohere(
        response=_FakeResponse(
            embeddings=_FakeEmbeddings(float=[[1, 2, 3]])  # ints en lugar de floats
        )
    )
    embedder = CohereEmbedder(api_key="t", client=client)  # type: ignore[arg-type]
    result = await embedder.embed_documents(["x"])
    assert all(isinstance(v, float) for v in result.vectors[0])
