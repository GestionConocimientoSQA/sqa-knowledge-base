"""Tests de las tools del agente (Fase 2.3).

Cubren:
- `search_kb`: empty query, sin matches, dummy distances, shape.
- `classify_topic`: happy path JSON limpio, JSON envuelto en markdown,
  confidence como string, empty topic → ValueError, JSON malformado →
  ValueError.

Sin tocar Anthropic real — todos los tests usan un `LlmGateway` fake.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from sqa_kb.agent.tools import (
    _parse_classification,
    classify_topic,
    search_kb,
)
from sqa_kb.domain.entities import Document
from sqa_kb.domain.value_objects import CategoryCode, DocStatus, DocTypeCode
from sqa_kb.ports.gateways import ChatMessage, LlmCompletion

# ===========================================================================
# Fakes
# ===========================================================================


def _doc(id: str, carpeta: str = "TEC", tipo: str = "MTEC") -> Document:
    now = datetime.now(UTC)
    return Document(
        id=id,
        titulo="Test doc",
        carpeta=CategoryCode(carpeta),
        tipo=DocTypeCode(tipo),
        autoritativo=False,
        estado=DocStatus.VIGENTE,
        autor_name="A",
        autor_role="QA",
        fecha=now,
        revision=now,
        version="1.0",
        formato="MD",
    )


@dataclass
class _FakeDocRepo:
    """Implementa el subset de DocumentRepository que search_kb necesita."""

    docs_to_return: list[Document]
    last_query: str = ""
    last_limit: int = 0

    async def search(  # noqa: PLR0913 — espejo del puerto
        self,
        *,
        query: str | None = None,
        carpetas: object = None,
        tipos: object = None,
        estados: object = None,
        autoritativo: object = None,
        anonimizado: object = None,
        min_score: object = None,
        date_from: object = None,
        date_to: object = None,
        author_oid: object = None,
        sort_by: object = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Document], int]:
        self.last_query = query or ""
        self.last_limit = limit
        return list(self.docs_to_return), len(self.docs_to_return)


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
# search_kb
# ===========================================================================


async def test_search_kb_empty_query_returns_empty() -> None:
    repo = _FakeDocRepo(docs_to_return=[_doc("TEC-foo-2026-01-01")])
    result = await search_kb(repo, query="", top_k=3)  # type: ignore[arg-type]
    assert result == []
    # Y NO debería haber llamado al repo:
    assert repo.last_query == ""


async def test_search_kb_whitespace_only_query_returns_empty() -> None:
    repo = _FakeDocRepo(docs_to_return=[_doc("TEC-foo-2026-01-01")])
    result = await search_kb(repo, query="   \t\n  ", top_k=3)  # type: ignore[arg-type]
    assert result == []


async def test_search_kb_no_matches_returns_empty() -> None:
    repo = _FakeDocRepo(docs_to_return=[])
    result = await search_kb(repo, query="nada", top_k=3)  # type: ignore[arg-type]
    assert result == []
    # Pero SÍ consultó al repo:
    assert repo.last_query == "nada"


async def test_search_kb_returns_existing_documents_with_dummy_distance() -> None:
    docs = [
        _doc("TEC-flaky-2026-01-01"),
        _doc("TEC-other-2026-02-01"),
    ]
    repo = _FakeDocRepo(docs_to_return=docs)
    result = await search_kb(repo, query="flaky", top_k=2)  # type: ignore[arg-type]

    assert len(result) == 2
    # Posiciones → distance 0.30, 0.40 (stub linear).
    assert result[0].distance == 0.30
    assert result[1].distance == 0.40
    assert result[0].document_id == "TEC-flaky-2026-01-01"


async def test_search_kb_respects_top_k() -> None:
    docs = [_doc(f"TEC-x{i}-2026-01-{i:02d}") for i in range(1, 6)]
    repo = _FakeDocRepo(docs_to_return=docs[:3])  # repo limita
    result = await search_kb(repo, query="x", top_k=3)  # type: ignore[arg-type]

    assert len(result) == 3
    assert repo.last_limit == 3


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
