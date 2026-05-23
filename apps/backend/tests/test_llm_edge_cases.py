"""Tests fuera del happy path para AnthropicDirectGateway + pricing.

Cubre:
- Validación de input (vacío, solo-system, role inválido).
- Forward correcto de `model`, `max_tokens`, `temperature` overrides.
- Defensividad ante respuestas del SDK con campos `None` o tipos mixtos.
- Stream con secuencias atípicas (sin texto, solo tool_use, eventos desconocidos).
- Pricing con counts extremos / sin input fresco.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from sqa_kb.adapters.llm.anthropic_direct import AnthropicDirectGateway
from sqa_kb.adapters.llm.pricing import estimate_cost_usd
from sqa_kb.ports.gateways import ChatMessage

# ===========================================================================
# Fakes (replicados acá para no acoplarse al otro test file)
# ===========================================================================


@dataclass
class _FakeUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class _FakeTextBlock:
    type: str = "text"
    text: str = ""


@dataclass
class _FakeToolUseBlock:
    type: str = "tool_use"
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class _FakeMessage:
    content: list[Any]
    usage: _FakeUsage | None = None
    stop_reason: str | None = "end_turn"


@dataclass
class _FakeDelta:
    type: str
    text: str = ""
    partial_json: str = ""


@dataclass
class _FakeStreamEvent:
    type: str
    delta: _FakeDelta | None = None
    content_block: Any | None = None


@dataclass
class _FakeContentBlock:
    type: str
    id: str = ""
    name: str = ""


class _FakeStreamCtx:
    def __init__(self, events: list[_FakeStreamEvent], final: _FakeMessage) -> None:
        self._events = events
        self._final = final

    async def __aenter__(self) -> _FakeStreamCtx:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    def __aiter__(self):  # type: ignore[no-untyped-def]
        return self._iter()

    async def _iter(self):  # type: ignore[no-untyped-def]
        for event in self._events:
            yield event

    async def get_final_message(self) -> _FakeMessage:
        return self._final


@dataclass
class _FakeMessagesNamespace:
    create_response: _FakeMessage | None = None
    stream_ctx: _FakeStreamCtx | None = None
    last_create_kwargs: dict[str, Any] = field(default_factory=dict)
    last_stream_kwargs: dict[str, Any] = field(default_factory=dict)

    async def create(self, **kwargs: Any) -> _FakeMessage:
        self.last_create_kwargs = kwargs
        assert self.create_response is not None
        return self.create_response

    def stream(self, **kwargs: Any) -> _FakeStreamCtx:
        self.last_stream_kwargs = kwargs
        assert self.stream_ctx is not None
        return self.stream_ctx


class _FakeAnthropic:
    def __init__(
        self,
        *,
        create_response: _FakeMessage | None = None,
        stream_ctx: _FakeStreamCtx | None = None,
    ) -> None:
        self.messages = _FakeMessagesNamespace(
            create_response=create_response,
            stream_ctx=stream_ctx,
        )


# ===========================================================================
# Validación de input
# ===========================================================================


async def test_complete_rejects_empty_messages() -> None:
    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(create_response=None),  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="messages no puede estar vacía"):
        await gateway.complete([])


async def test_complete_rejects_only_system_messages() -> None:
    """Sin user msg el SDK tira 400. Nosotros fallamos fast con ValueError
    descriptivo — ahorra round-trip y da mensaje más claro al caller."""
    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(create_response=None),  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="user/assistant"):
        await gateway.complete(
            [ChatMessage(role="system", content="Sos un asistente.")]
        )


async def test_stream_rejects_empty_messages() -> None:
    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(stream_ctx=None),  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="messages no puede estar vacía"):
        async for _ in gateway.stream([]):
            pass


async def test_stream_rejects_only_system_messages() -> None:
    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(stream_ctx=None),  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="user/assistant"):
        async for _ in gateway.stream(
            [ChatMessage(role="system", content="x")]
        ):
            pass


# ===========================================================================
# Forward de parámetros opcionales
# ===========================================================================


async def test_complete_forwards_max_tokens_and_temperature() -> None:
    fake = _FakeMessage(
        content=[_FakeTextBlock(text="ok")],
        usage=_FakeUsage(input_tokens=1, output_tokens=1),
    )
    client = _FakeAnthropic(create_response=fake)
    gateway = AnthropicDirectGateway(
        api_key="t", default_model="claude-sonnet-4-5", client=client  # type: ignore[arg-type]
    )

    await gateway.complete(
        [ChatMessage(role="user", content="hi")],
        max_tokens=512,
        temperature=0.1,
    )

    assert client.messages.last_create_kwargs["max_tokens"] == 512
    assert client.messages.last_create_kwargs["temperature"] == 0.1


async def test_complete_forwards_explicit_model_override() -> None:
    """Si el caller pasa `model=`, sobreescribe el default."""
    fake = _FakeMessage(
        content=[_FakeTextBlock(text="ok")],
        usage=_FakeUsage(input_tokens=1, output_tokens=1),
    )
    client = _FakeAnthropic(create_response=fake)
    gateway = AnthropicDirectGateway(
        api_key="t", default_model="claude-sonnet-4-5", client=client  # type: ignore[arg-type]
    )

    await gateway.complete(
        [ChatMessage(role="user", content="hi")],
        model="claude-haiku-4-5",
    )

    assert client.messages.last_create_kwargs["model"] == "claude-haiku-4-5"


async def test_stream_forwards_max_tokens_and_temperature() -> None:
    ctx = _FakeStreamCtx(
        events=[],
        final=_FakeMessage(
            content=[], usage=_FakeUsage(input_tokens=1, output_tokens=1)
        ),
    )
    client = _FakeAnthropic(stream_ctx=ctx)
    gateway = AnthropicDirectGateway(
        api_key="t", default_model="claude-sonnet-4-5", client=client  # type: ignore[arg-type]
    )

    async for _ in gateway.stream(
        [ChatMessage(role="user", content="hi")],
        max_tokens=2048,
        temperature=0.0,
    ):
        pass

    assert client.messages.last_stream_kwargs["max_tokens"] == 2048
    assert client.messages.last_stream_kwargs["temperature"] == 0.0


async def test_stream_forwards_explicit_model_override() -> None:
    ctx = _FakeStreamCtx(
        events=[],
        final=_FakeMessage(
            content=[], usage=_FakeUsage(input_tokens=1, output_tokens=1)
        ),
    )
    client = _FakeAnthropic(stream_ctx=ctx)
    gateway = AnthropicDirectGateway(
        api_key="t", default_model="claude-sonnet-4-5", client=client  # type: ignore[arg-type]
    )

    async for _ in gateway.stream(
        [ChatMessage(role="user", content="hi")],
        model="claude-opus-4-5",
    ):
        pass

    assert client.messages.last_stream_kwargs["model"] == "claude-opus-4-5"


# ===========================================================================
# Defensividad ante respuestas atípicas del SDK
# ===========================================================================


async def test_complete_extracts_text_ignoring_tool_use_blocks() -> None:
    """Si el modelo devuelve text + tool_use, complete() solo agarra text."""
    fake = _FakeMessage(
        content=[
            _FakeTextBlock(text="Voy a buscar. "),
            _FakeToolUseBlock(id="t1", name="search_kb", input={"q": "foo"}),
            _FakeTextBlock(text="Listo."),
        ],
        usage=_FakeUsage(input_tokens=5, output_tokens=3),
    )
    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(create_response=fake),  # type: ignore[arg-type]
    )

    result = await gateway.complete([ChatMessage(role="user", content="hi")])

    # Concatena los dos text blocks en orden, ignora tool_use.
    assert result.text == "Voy a buscar. Listo."


async def test_complete_handles_empty_content_blocks() -> None:
    """Modelo devuelve content vacío — texto resultante es string vacío."""
    fake = _FakeMessage(
        content=[],
        usage=_FakeUsage(input_tokens=2, output_tokens=0),
    )
    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(create_response=fake),  # type: ignore[arg-type]
    )

    result = await gateway.complete([ChatMessage(role="user", content="hi")])

    assert result.text == ""
    assert result.input_tokens == 2
    assert result.output_tokens == 0


async def test_complete_handles_usage_with_none_fields() -> None:
    """Anthropic devuelve `cache_*` como None cuando no hay caching."""
    fake = _FakeMessage(
        content=[_FakeTextBlock(text="ok")],
        usage=_FakeUsage(
            input_tokens=10,
            output_tokens=5,
            # cache_read_input_tokens y cache_creation_input_tokens quedan en 0,
            # que es como _FakeUsage los inicializa (replica el comportamiento
            # del SDK que entrega None cuando no hay caching).
        ),
    )
    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(create_response=fake),  # type: ignore[arg-type]
    )

    result = await gateway.complete([ChatMessage(role="user", content="hi")])

    assert result.input_tokens == 10
    assert result.output_tokens == 5


async def test_complete_handles_usage_object_none() -> None:
    """Borde: SDK devuelve `usage=None` en lugar de objeto."""

    class _MsgWithNoneUsage:
        content = [_FakeTextBlock(text="ok")]
        usage = None  # type: ignore[var-annotated]
        stop_reason = "end_turn"

    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(create_response=_MsgWithNoneUsage()),  # type: ignore[arg-type]
    )

    result = await gateway.complete([ChatMessage(role="user", content="hi")])

    # Sin usage trackeable, todo en 0 — no debe romper el grafo.
    assert result.input_tokens == 0
    assert result.output_tokens == 0
    assert result.cost_usd == 0.0


# ===========================================================================
# Stream con secuencias atípicas
# ===========================================================================


async def test_stream_no_events_just_stop() -> None:
    """Modelo no emite ningún content delta — solo el stop final."""
    ctx = _FakeStreamCtx(
        events=[],
        final=_FakeMessage(
            content=[],
            usage=_FakeUsage(input_tokens=3, output_tokens=0),
            stop_reason="max_tokens",
        ),
    )
    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(stream_ctx=ctx),  # type: ignore[arg-type]
    )

    events = [
        (ev.kind, dict(ev.payload))
        async for ev in gateway.stream([ChatMessage(role="user", content="hi")])
    ]

    assert len(events) == 1
    assert events[0][0] == "stop"
    assert events[0][1]["stop_reason"] == "max_tokens"


async def test_stream_only_tool_use_no_text() -> None:
    """Modelo decide invocar tool sin generar texto previo."""
    events = [
        _FakeStreamEvent(
            type="content_block_start",
            content_block=_FakeContentBlock(
                type="tool_use", id="t1", name="search_kb"
            ),
        ),
        _FakeStreamEvent(
            type="content_block_delta",
            delta=_FakeDelta(type="input_json_delta", partial_json='{"q":"flaky"}'),
        ),
    ]
    final = _FakeMessage(
        content=[],
        usage=_FakeUsage(input_tokens=8, output_tokens=12),
        stop_reason="tool_use",
    )
    ctx = _FakeStreamCtx(events=events, final=final)
    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(stream_ctx=ctx),  # type: ignore[arg-type]
    )

    kinds = [
        ev.kind
        async for ev in gateway.stream([ChatMessage(role="user", content="hi")])
    ]

    # tool_use_start + tool_use_delta + stop. No hay `text`.
    assert "text" not in kinds
    assert kinds == ["tool_use_start", "tool_use_delta", "stop"]


async def test_stream_ignores_unknown_event_types() -> None:
    """Eventos como `message_start`, `ping`, etc. NO se emiten al caller."""
    events = [
        _FakeStreamEvent(type="message_start"),
        _FakeStreamEvent(
            type="content_block_delta",
            delta=_FakeDelta(type="text_delta", text="hola"),
        ),
        _FakeStreamEvent(type="ping"),
        _FakeStreamEvent(type="content_block_stop"),
        _FakeStreamEvent(type="message_delta"),
        _FakeStreamEvent(type="message_stop"),
    ]
    final = _FakeMessage(
        content=[_FakeTextBlock(text="hola")],
        usage=_FakeUsage(input_tokens=2, output_tokens=1),
    )
    ctx = _FakeStreamCtx(events=events, final=final)
    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(stream_ctx=ctx),  # type: ignore[arg-type]
    )

    kinds = [
        ev.kind
        async for ev in gateway.stream([ChatMessage(role="user", content="hi")])
    ]

    # Solo se filtra al text_delta + stop final.
    assert kinds == ["text", "stop"]


async def test_stream_ignores_text_delta_with_no_text() -> None:
    """Edge: SDK manda `text_delta` con string vacío. Lo emitimos igual —
    el caller decide si filtrar. Documenta el comportamiento."""
    events = [
        _FakeStreamEvent(
            type="content_block_delta",
            delta=_FakeDelta(type="text_delta", text=""),
        ),
    ]
    final = _FakeMessage(
        content=[], usage=_FakeUsage(input_tokens=1, output_tokens=0)
    )
    ctx = _FakeStreamCtx(events=events, final=final)
    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(stream_ctx=ctx),  # type: ignore[arg-type]
    )

    collected = [
        (ev.kind, ev.payload.get("delta"))
        async for ev in gateway.stream([ChatMessage(role="user", content="hi")])
    ]

    assert collected[0] == ("text", "")
    assert collected[-1][0] == "stop"


async def test_stream_handles_none_stop_reason() -> None:
    """SDK podría devolver stop_reason=None — emitimos string vacío sin romper."""
    final = _FakeMessage(
        content=[_FakeTextBlock(text="ok")],
        usage=_FakeUsage(input_tokens=1, output_tokens=1),
        stop_reason=None,
    )
    ctx = _FakeStreamCtx(events=[], final=final)
    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(stream_ctx=ctx),  # type: ignore[arg-type]
    )

    events = [
        ev async for ev in gateway.stream([ChatMessage(role="user", content="hi")])
    ]

    assert events[-1].kind == "stop"
    assert events[-1].payload["stop_reason"] == ""


async def test_stream_handles_content_block_start_for_text_block() -> None:
    """Un content_block_start de tipo `text` NO debe emitirse como tool_use_start."""
    events = [
        _FakeStreamEvent(
            type="content_block_start",
            content_block=_FakeContentBlock(type="text"),
        ),
        _FakeStreamEvent(
            type="content_block_delta",
            delta=_FakeDelta(type="text_delta", text="hola"),
        ),
    ]
    final = _FakeMessage(
        content=[_FakeTextBlock(text="hola")],
        usage=_FakeUsage(input_tokens=1, output_tokens=1),
    )
    ctx = _FakeStreamCtx(events=events, final=final)
    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(stream_ctx=ctx),  # type: ignore[arg-type]
    )

    kinds = [
        ev.kind
        async for ev in gateway.stream([ChatMessage(role="user", content="hi")])
    ]

    assert kinds == ["text", "stop"]  # ni tool_use_start ni nada raro


async def test_stream_propagates_error_emitted_mid_stream() -> None:
    """Si `get_final_message()` falla después de yieldear deltas, el caller
    recibe los deltas previos + un evento `error` al final."""

    class _BadStreamCtx(_FakeStreamCtx):
        async def get_final_message(self) -> _FakeMessage:  # type: ignore[override]
            raise RuntimeError("upstream cut")

    events = [
        _FakeStreamEvent(
            type="content_block_delta",
            delta=_FakeDelta(type="text_delta", text="parc"),
        ),
        _FakeStreamEvent(
            type="content_block_delta",
            delta=_FakeDelta(type="text_delta", text="ial"),
        ),
    ]
    ctx = _BadStreamCtx(
        events=events, final=_FakeMessage(content=[], usage=_FakeUsage())
    )
    gateway = AnthropicDirectGateway(
        api_key="t",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(stream_ctx=ctx),  # type: ignore[arg-type]
    )

    collected = [
        ev async for ev in gateway.stream([ChatMessage(role="user", content="hi")])
    ]

    assert [ev.kind for ev in collected] == ["text", "text", "error"]
    assert collected[0].payload["delta"] == "parc"
    assert collected[1].payload["delta"] == "ial"
    assert "upstream cut" in str(collected[2].payload["message"])


# ===========================================================================
# Pricing — escenarios extremos
# ===========================================================================


def test_estimate_cost_large_token_counts_no_overflow() -> None:
    """1M input + 1M output no debe overflow ni perder precisión drástica."""
    cost = estimate_cost_usd(
        model="claude-sonnet-4-5",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    # 1M * $3 + 1M * $15 = $3 + $15 = $18 (por 1M tokens)
    assert cost == pytest.approx(18.0, rel=1e-6)


def test_estimate_cost_only_cache_reads_no_fresh_input() -> None:
    """Caso útil: todo el input viene del cache (sesión continuada)."""
    cost = estimate_cost_usd(
        model="claude-sonnet-4-5",
        input_tokens=0,
        output_tokens=500,
        cache_read_tokens=10_000,
    )
    # 0*3 + 500*15 + 10000*0.30 = 0 + 7500 + 3000 = 10500 / 1M = 0.0105
    assert cost == pytest.approx(0.0105, rel=1e-6)


def test_estimate_cost_haiku_cheaper_than_sonnet_same_load() -> None:
    """A igual workload Haiku tiene que salir menos. Sanity check de la tabla."""
    workload = {"input_tokens": 5_000, "output_tokens": 2_000}
    sonnet = estimate_cost_usd(model="claude-sonnet-4-5", **workload)
    haiku = estimate_cost_usd(model="claude-haiku-4-5", **workload)
    assert haiku < sonnet
    # Haiku es ~3× más barato que Sonnet a la carga típica
    assert haiku < sonnet / 2


def test_estimate_cost_unknown_model_with_cache_still_zero() -> None:
    """Modelo desconocido con cache tokens sigue devolviendo 0 sin romper."""
    cost = estimate_cost_usd(
        model="claude-future-99",
        input_tokens=100,
        output_tokens=100,
        cache_read_tokens=1000,
        cache_write_tokens=500,
    )
    assert cost == 0.0
