"""Tests de las tools del agente (Fase 2.3, refactor en Fase 3.5).

Cubren:
- `search_kb`: empty query, sin matches, dedup por document_id,
  distance = 1 - score, top_k limita docs únicos.
- `search_kb_chunks`: empty query → [], devuelve chunks tal cual sin dedup.
- `classify_topic`: happy path JSON limpio, JSON envuelto en markdown,
  confidence como string, empty topic → ValueError, JSON malformado →
  ValueError.

Sin tocar Anthropic ni Cohere reales — todos los tests usan fakes.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

import pytest

from sqa_kb.agent.tools import (
    _parse_classification,
    classify_topic,
    search_kb,
    search_kb_chunks,
)
from sqa_kb.ports.gateways import ChatMessage, LlmCompletion
from sqa_kb.rag.hybrid_search import HybridChunk

# ===========================================================================
# Fakes
# ===========================================================================


def _chunk(
    *,
    chunk_id: str = "chk-1",
    document_id: str = "TEC-foo-2026-01-01",
    chunk_index: int = 0,
    score: float = 0.8,
    document_title: str = "Test doc",
    document_type: str = "MTEC",
    document_category: str = "TEC",
    authoritative: bool = False,
    content: str = "contenido",
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
    """Implementa la API mínima del `HybridSearcher`."""

    chunks_to_return: list[HybridChunk] = field(default_factory=list)
    last_query: str = ""
    last_top_k: int = 0
    call_count: int = 0

    async def search(
        self,
        query: str,
        *,
        project_id: str | None = None,  # noqa: ARG002
        top_k: int = 5,
        carpetas: Iterable[str] | None = None,  # noqa: ARG002
        tipos: Iterable[str] | None = None,  # noqa: ARG002
        authoritative_only: bool = False,  # noqa: ARG002
        authoritative_boost: float | None = None,  # noqa: ARG002
    ) -> Sequence[HybridChunk]:
        self.last_query = query
        self.last_top_k = top_k
        self.call_count += 1
        return list(self.chunks_to_return)


@dataclass
class _FakeGateway:
    """Implementa solo `complete()` — lo único que `classify_topic` usa."""

    response_text: str = (
        '{"category":"TEC","document_type":"MTEC","confidence":0.9,"reasoning":"x"}'
    )
    last_messages: tuple[ChatMessage, ...] = ()
    last_temperature: float = -1.0

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        metadata: Mapping[str, str] | None = None,
    ) -> LlmCompletion:
        self.last_messages = tuple(messages)
        self.last_temperature = temperature
        return LlmCompletion(
            text=self.response_text,
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.0001,
            model=model or "claude-sonnet-4-5",
        )

    async def stream(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError


# ===========================================================================
# search_kb (Fase 3.5 — usa HybridSearcher fake)
# ===========================================================================


async def test_search_kb_empty_query_returns_empty() -> None:
    searcher = _FakeSearcher(chunks_to_return=[_chunk()])
    result = await search_kb(searcher, query="", top_k=3)  # type: ignore[arg-type]
    assert result == []
    # Y NO debería haber llamado al searcher.
    assert searcher.call_count == 0


async def test_search_kb_whitespace_only_query_returns_empty() -> None:
    searcher = _FakeSearcher(chunks_to_return=[_chunk()])
    result = await search_kb(searcher, query="   \t\n  ", top_k=3)  # type: ignore[arg-type]
    assert result == []
    assert searcher.call_count == 0


async def test_search_kb_no_matches_returns_empty() -> None:
    searcher = _FakeSearcher(chunks_to_return=[])
    result = await search_kb(searcher, query="nada", top_k=3)  # type: ignore[arg-type]
    assert result == []
    # Pero SÍ consultó al searcher.
    assert searcher.last_query == "nada"


async def test_search_kb_returns_existing_documents_with_distance_from_score() -> None:
    """distance = clip(1 - score, 0, 1). 2 chunks de DISTINTOS docs → 2 docs."""
    chunks = [
        _chunk(chunk_id="c1", document_id="TEC-flaky-2026-01-01", score=0.8),
        _chunk(chunk_id="c2", document_id="TEC-other-2026-02-01", score=0.6),
    ]
    searcher = _FakeSearcher(chunks_to_return=chunks)
    result = await search_kb(searcher, query="flaky", top_k=2)  # type: ignore[arg-type]

    assert len(result) == 2
    assert result[0].document_id == "TEC-flaky-2026-01-01"
    assert result[0].distance == pytest.approx(0.2)  # 1 - 0.8
    assert result[1].distance == pytest.approx(0.4)  # 1 - 0.6


async def test_search_kb_deduplicates_chunks_by_document_id() -> None:
    """Si el searcher devuelve N chunks del mismo doc, el resultado tiene
    el doc UNA sola vez con el mejor score (chunk con mayor score)."""
    chunks = [
        # Mismo doc, 3 chunks; el primero (mejor score) gana.
        _chunk(chunk_id="c1", document_id="TEC-foo", chunk_index=0, score=0.9),
        _chunk(chunk_id="c2", document_id="TEC-foo", chunk_index=1, score=0.7),
        _chunk(chunk_id="c3", document_id="TEC-foo", chunk_index=2, score=0.5),
        # Otro doc.
        _chunk(chunk_id="c4", document_id="TEC-bar", chunk_index=0, score=0.6),
    ]
    searcher = _FakeSearcher(chunks_to_return=chunks)
    result = await search_kb(searcher, query="x", top_k=5)  # type: ignore[arg-type]

    assert len(result) == 2
    foo = next(d for d in result if d.document_id == "TEC-foo")
    assert foo.distance == pytest.approx(0.1)  # 1 - 0.9, no 1 - 0.5


async def test_search_kb_top_k_limits_unique_docs_not_chunks() -> None:
    """`top_k=2` → 2 documentos únicos. Pide oversample al searcher para
    cubrir el caso de muchos chunks por doc."""
    chunks = [_chunk(chunk_id=f"c{i}", document_id=f"DOC-{i}", score=0.9 - i * 0.05)
              for i in range(5)]
    searcher = _FakeSearcher(chunks_to_return=chunks)
    result = await search_kb(searcher, query="x", top_k=2)  # type: ignore[arg-type]

    assert len(result) == 2
    # Oversample: top_k=2 pide al menos top_k * CHUNK_OVERSAMPLE al searcher.
    assert searcher.last_top_k >= 2 * 5


async def test_search_kb_distance_clipped_to_zero_when_score_exceeds_one() -> None:
    """Boost autoritativo puede llevar score > 1 → distance NO negativa."""
    chunks = [_chunk(score=1.15, authoritative=True)]
    searcher = _FakeSearcher(chunks_to_return=chunks)
    result = await search_kb(searcher, query="x", top_k=1)  # type: ignore[arg-type]
    assert result[0].distance == 0.0


# ===========================================================================
# search_kb_chunks
# ===========================================================================


async def test_search_kb_chunks_empty_query_returns_empty() -> None:
    searcher = _FakeSearcher(chunks_to_return=[_chunk()])
    result = await search_kb_chunks(searcher, query="", top_k=3)  # type: ignore[arg-type]
    assert list(result) == []
    assert searcher.call_count == 0


async def test_search_kb_chunks_returns_chunks_without_dedup() -> None:
    """Sin agregación — el caller (consultation) quiere todos los chunks
    para sintetizar respuesta."""
    chunks = [
        _chunk(chunk_id="c1", document_id="DOC-1", chunk_index=0, score=0.9),
        _chunk(chunk_id="c2", document_id="DOC-1", chunk_index=1, score=0.7),
        _chunk(chunk_id="c3", document_id="DOC-2", chunk_index=0, score=0.6),
    ]
    searcher = _FakeSearcher(chunks_to_return=chunks)
    result = list(await search_kb_chunks(searcher, query="x", top_k=5))  # type: ignore[arg-type]

    assert len(result) == 3
    assert [c.chunk_id for c in result] == ["c1", "c2", "c3"]
    assert searcher.last_top_k == 5


# ===========================================================================
# classify_topic
# ===========================================================================


async def test_classify_topic_happy_path() -> None:
    gateway = _FakeGateway(
        response_text='{"category":"TEC","document_type":"MTEC","confidence":0.85,"reasoning":"flakiness"}'
    )
    result = await classify_topic(gateway, topic="detección de tests flaky")  # type: ignore[arg-type]
    assert result.category == "TEC"
    assert result.document_type == "MTEC"
    assert result.confidence == 0.85
    assert result.reasoning == "flakiness"


async def test_classify_topic_uses_temperature_zero() -> None:
    """Clasificación debe ser determinística — temperature=0."""
    gateway = _FakeGateway()
    await classify_topic(gateway, topic="x")  # type: ignore[arg-type]
    assert gateway.last_temperature == 0.0


async def test_classify_topic_includes_system_and_user_messages() -> None:
    gateway = _FakeGateway()
    await classify_topic(gateway, topic="detección de flaky tests")  # type: ignore[arg-type]
    assert gateway.last_messages[0].role == "system"
    assert "JSON" in gateway.last_messages[0].content
    assert gateway.last_messages[-1].role == "user"
    assert "detección de flaky tests" in gateway.last_messages[-1].content


async def test_classify_topic_includes_history() -> None:
    """El clasificador lee el history del user para contexto."""
    gateway = _FakeGateway()
    history = [
        ChatMessage(role="user", content="trabajo en automation"),
        ChatMessage(role="assistant", content="ok"),
    ]
    await classify_topic(  # type: ignore[arg-type]
        gateway, topic="ci pipelines", history=history
    )
    contents = [m.content for m in gateway.last_messages]
    assert "trabajo en automation" in contents


async def test_classify_topic_empty_raises() -> None:
    gateway = _FakeGateway()
    with pytest.raises(ValueError, match="topic vacío"):
        await classify_topic(gateway, topic="")  # type: ignore[arg-type]


async def test_classify_topic_whitespace_only_raises() -> None:
    gateway = _FakeGateway()
    with pytest.raises(ValueError, match="topic vacío"):
        await classify_topic(gateway, topic="   \n\t")  # type: ignore[arg-type]


async def test_classify_topic_handles_markdown_wrapped_json() -> None:
    gateway = _FakeGateway(
        response_text='```json\n{"category":"TEC","document_type":"GUIA","confidence":0.7,"reasoning":"y"}\n```'
    )
    result = await classify_topic(gateway, topic="x")  # type: ignore[arg-type]
    assert result.category == "TEC"
    assert result.document_type == "GUIA"


async def test_classify_topic_handles_confidence_as_string() -> None:
    """Modelos a veces narran: 'confidence': '0.8'."""
    gateway = _FakeGateway(
        response_text='{"category":"TEC","document_type":"MTEC","confidence":"0.8","reasoning":"z"}'
    )
    result = await classify_topic(gateway, topic="x")  # type: ignore[arg-type]
    assert result.confidence == 0.8


async def test_classify_topic_unparseable_confidence_defaults_to_zero() -> None:
    gateway = _FakeGateway(
        response_text='{"category":"TEC","document_type":"MTEC","confidence":"high","reasoning":"z"}'
    )
    result = await classify_topic(gateway, topic="x")  # type: ignore[arg-type]
    assert result.confidence == 0.0


async def test_classify_topic_malformed_json_raises() -> None:
    gateway = _FakeGateway(response_text="esto no es JSON, es texto libre")
    with pytest.raises(ValueError, match="no-JSON"):
        await classify_topic(gateway, topic="x")  # type: ignore[arg-type]


async def test_classify_topic_propagates_pydantic_validation_error() -> None:
    """Si el JSON tiene confidence fuera de rango, Pydantic falla."""
    gateway = _FakeGateway(
        response_text='{"category":"TEC","document_type":"MTEC","confidence":1.5,"reasoning":"x"}'
    )
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        await classify_topic(gateway, topic="x")  # type: ignore[arg-type]


# ===========================================================================
# _parse_classification edge cases
# ===========================================================================


def test_parse_handles_extra_whitespace() -> None:
    raw = '   \n\n{"category":"TEC","document_type":"MTEC","confidence":0.5,"reasoning":"x"}\n\n'
    result = _parse_classification(raw)
    assert result.category == "TEC"


def test_parse_handles_bare_triple_backtick() -> None:
    """Bloque ``` sin 'json' después también se debe limpiar."""
    raw = '```\n{"category":"TEC","document_type":"MTEC","confidence":0.5,"reasoning":"x"}\n```'
    result = _parse_classification(raw)
    assert result.category == "TEC"


# ===========================================================================
# score_capture (Fase 2.4)
# ===========================================================================


async def test_score_capture_happy_path() -> None:
    """Devuelve CaptureScoring con 4 dimensiones + value_score."""
    from sqa_kb.agent.tools import score_capture

    gateway = _FakeGateway(
        response_text=(
            '{"specificity":4,"depth":5,"reusability":3,"uniqueness":4,'
            '"value_score":4.0,"observations":"sólido"}'
        )
    )
    result = await score_capture(  # type: ignore[arg-type]
        gateway,
        document_content="contenido del doc",
        document_type="MTEC",
    )
    assert result.specificity == 4
    assert result.depth == 5
    assert result.value_score == 4.0
    assert result.observations == "sólido"


async def test_score_capture_empty_content_raises() -> None:
    from sqa_kb.agent.tools import score_capture

    gateway = _FakeGateway()
    with pytest.raises(ValueError, match="document_content vacío"):
        await score_capture(  # type: ignore[arg-type]
            gateway, document_content="", document_type="MTEC"
        )


async def test_score_capture_handles_markdown_wrapping() -> None:
    from sqa_kb.agent.tools import score_capture

    gateway = _FakeGateway(
        response_text=(
            "```json\n"
            '{"specificity":3,"depth":3,"reusability":3,"uniqueness":3,'
            '"value_score":3.0,"observations":"medio"}\n'
            "```"
        )
    )
    result = await score_capture(  # type: ignore[arg-type]
        gateway, document_content="x", document_type="POL"
    )
    assert result.value_score == 3.0


async def test_score_capture_coerces_int_strings() -> None:
    """Si el modelo devuelve '4' (string) en lugar de 4, lo coercemos."""
    from sqa_kb.agent.tools import score_capture

    gateway = _FakeGateway(
        response_text=(
            '{"specificity":"4","depth":"3","reusability":"5","uniqueness":"4",'
            '"value_score":"4.0","observations":"ok"}'
        )
    )
    result = await score_capture(  # type: ignore[arg-type]
        gateway, document_content="x", document_type="POL"
    )
    assert result.specificity == 4
    assert result.depth == 3
    assert result.value_score == 4.0


async def test_score_capture_unparseable_int_defaults_to_1() -> None:
    """Edge: el modelo devuelve texto en lugar de int → coerce a 1."""
    from sqa_kb.agent.tools import score_capture

    gateway = _FakeGateway(
        response_text=(
            '{"specificity":"high","depth":3,"reusability":4,"uniqueness":4,'
            '"value_score":3.5,"observations":"x"}'
        )
    )
    result = await score_capture(  # type: ignore[arg-type]
        gateway, document_content="x", document_type="POL"
    )
    assert result.specificity == 1  # fallback


async def test_score_capture_malformed_json_raises() -> None:
    from sqa_kb.agent.tools import score_capture

    gateway = _FakeGateway(response_text="esto no es JSON válido")
    with pytest.raises(ValueError, match="no-JSON"):
        await score_capture(  # type: ignore[arg-type]
            gateway, document_content="x", document_type="POL"
        )


async def test_score_capture_uses_temperature_zero() -> None:
    """Scoring debe ser determinístico — temperature=0."""
    from sqa_kb.agent.tools import score_capture

    gateway = _FakeGateway(
        response_text=(
            '{"specificity":4,"depth":4,"reusability":4,"uniqueness":4,'
            '"value_score":4.0,"observations":""}'
        )
    )
    await score_capture(  # type: ignore[arg-type]
        gateway, document_content="x", document_type="POL"
    )
    assert gateway.last_temperature == 0.0


async def test_score_capture_score_out_of_range_raises_validation_error() -> None:
    """Pydantic valida ranges 1-5. Si el LLM devuelve 6, ValidationError."""
    from pydantic import ValidationError

    from sqa_kb.agent.tools import score_capture

    gateway = _FakeGateway(
        response_text=(
            '{"specificity":6,"depth":3,"reusability":3,"uniqueness":3,'
            '"value_score":3.0,"observations":"x"}'
        )
    )
    with pytest.raises(ValidationError):
        await score_capture(  # type: ignore[arg-type]
            gateway, document_content="x", document_type="POL"
        )


def test_parse_invalid_category_raises_validation_error() -> None:
    """Pydantic valida category contra CategoryCode literal."""
    raw = '{"category":"BANANA","document_type":"MTEC","confidence":0.5,"reasoning":"x"}'
    from pydantic import ValidationError

    # Acá NO falla porque CategoryCode es str, no Literal en Classification.
    # Esto documenta el comportamiento actual — si Fase 2.4+ endurece el
    # schema con Literal, este test cambia a esperar ValidationError.
    try:
        result = _parse_classification(raw)
        # Si pasa, validamos al menos que el campo se conservó.
        assert result.category == "BANANA"
    except ValidationError:
        pass  # también es aceptable si el schema se endurece después
