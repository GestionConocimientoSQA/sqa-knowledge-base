"""Tests del adapter AnthropicDirectGateway.

Mockean el SDK con stubs minimalistas — no se golpea api.anthropic.com.
Los stubs replican la forma de los objetos del SDK:
- Message.content: list de bloques con .type y .text
- Message.usage: objeto con input_tokens / output_tokens / cache_*
- messages.stream(...): async context manager que itera eventos del modelo
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from sqa_kb.adapters.llm.anthropic_direct import AnthropicDirectGateway
from sqa_kb.ports.gateways import ChatMessage

# ===========================================================================
# Fakes
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
class _FakeMessage:
    content: list[Any]
    usage: _FakeUsage
    stop_reason: str = "end_turn"


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
    """Async context manager que el SDK devuelve desde messages.stream()."""

    def __init__(self, events: list[_FakeStreamEvent], final: _FakeMessage) -> None:
        self._events = events
        self._final = final
        self.last_call_kwargs: dict[str, Any] = {}

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
# complete()
# ===========================================================================


async def test_complete_returns_concatenated_text_and_usage() -> None:
    fake_msg = _FakeMessage(
        content=[
            _FakeTextBlock(text="Hola "),
            _FakeTextBlock(text="mundo"),
        ],
        usage=_FakeUsage(input_tokens=10, output_tokens=5),
    )
    gateway = AnthropicDirectGateway(
        api_key="test",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(create_response=fake_msg),  # type: ignore[arg-type]
    )

    result = await gateway.complete(
        [ChatMessage(role="user", content="hola")],
    )

    assert result.text == "Hola mundo"
    assert result.input_tokens == 10
    assert result.output_tokens == 5
    assert result.model == "claude-sonnet-4-5"
    # Sonnet 4.5: (10*3 + 5*15)/1_000_000 = 0.000105
    assert result.cost_usd == pytest.approx(0.000105, rel=1e-4)


async def test_complete_separates_system_from_messages() -> None:
    fake_msg = _FakeMessage(
        content=[_FakeTextBlock(text="ok")],
        usage=_FakeUsage(input_tokens=1, output_tokens=1),
    )
    fake_client = _FakeAnthropic(create_response=fake_msg)
    gateway = AnthropicDirectGateway(
        api_key="test",
        default_model="claude-sonnet-4-5",
        client=fake_client,  # type: ignore[arg-type]
    )

    await gateway.complete(
        [
            ChatMessage(role="system", content="Sos un asistente."),
            ChatMessage(role="user", content="hola"),
        ],
    )

    kwargs = fake_client.messages.last_create_kwargs
    # System extraído al nivel top-level del SDK.
    assert kwargs["system"] == "Sos un asistente."
    # `messages` solo lleva user/assistant.
    assert kwargs["messages"] == [{"role": "user", "content": "hola"}]


async def test_complete_concatenates_multiple_system_messages() -> None:
    fake_msg = _FakeMessage(
        content=[_FakeTextBlock(text="ok")],
        usage=_FakeUsage(input_tokens=1, output_tokens=1),
    )
    fake_client = _FakeAnthropic(create_response=fake_msg)
    gateway = AnthropicDirectGateway(
        api_key="test",
        default_model="claude-sonnet-4-5",
        client=fake_client,  # type: ignore[arg-type]
    )

    await gateway.complete(
        [
            ChatMessage(role="system", content="Skill 1."),
            ChatMessage(role="system", content="Skill 2."),
            ChatMessage(role="user", content="hola"),
        ],
    )

    assert fake_client.messages.last_create_kwargs["system"] == "Skill 1.\n\nSkill 2."


async def test_complete_uses_default_model_when_not_specified() -> None:
    fake_msg = _FakeMessage(
        content=[_FakeTextBlock(text="ok")],
        usage=_FakeUsage(input_tokens=1, output_tokens=1),
    )
    fake_client = _FakeAnthropic(create_response=fake_msg)
    gateway = AnthropicDirectGateway(
        api_key="test",
        default_model="claude-haiku-4-5",
        client=fake_client,  # type: ignore[arg-type]
    )

    await gateway.complete([ChatMessage(role="user", content="hi")])

    assert fake_client.messages.last_create_kwargs["model"] == "claude-haiku-4-5"


async def test_complete_passes_metadata_through() -> None:
    fake_msg = _FakeMessage(
        content=[_FakeTextBlock(text="ok")],
        usage=_FakeUsage(input_tokens=1, output_tokens=1),
    )
    fake_client = _FakeAnthropic(create_response=fake_msg)
    gateway = AnthropicDirectGateway(
        api_key="test",
        default_model="claude-sonnet-4-5",
        client=fake_client,  # type: ignore[arg-type]
    )

    await gateway.complete(
        [ChatMessage(role="user", content="hi")],
        metadata={"user_id": "oid-123", "session_id": "ses-abc"},
    )

    assert fake_client.messages.last_create_kwargs["metadata"] == {
        "user_id": "oid-123",
        "session_id": "ses-abc",
    }


async def test_complete_rejects_invalid_role() -> None:
    gateway = AnthropicDirectGateway(
        api_key="test",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(create_response=None),  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="role inválido"):
        await gateway.complete([ChatMessage(role="banana", content="hi")])


async def test_complete_includes_cache_tokens_in_cost() -> None:
    fake_msg = _FakeMessage(
        content=[_FakeTextBlock(text="ok")],
        usage=_FakeUsage(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=200,
            cache_read_input_tokens=1000,
        ),
    )
    gateway = AnthropicDirectGateway(
        api_key="test",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(create_response=fake_msg),  # type: ignore[arg-type]
    )

    result = await gateway.complete([ChatMessage(role="user", content="hi")])

    # Total "input" reportado al caller = fresh + cache write + cache read
    assert result.input_tokens == 100 + 200 + 1000
    # 100*3 + 50*15 + 200*3.75 + 1000*0.30 = 300 + 750 + 750 + 300 = 2100
    # / 1_000_000 = 0.0021
    assert result.cost_usd == pytest.approx(0.0021, rel=1e-4)


# ===========================================================================
# stream()
# ===========================================================================


async def test_stream_yields_text_deltas_then_stop() -> None:
    events = [
        _FakeStreamEvent(
            type="content_block_delta",
            delta=_FakeDelta(type="text_delta", text="Hola"),
        ),
        _FakeStreamEvent(
            type="content_block_delta",
            delta=_FakeDelta(type="text_delta", text=" mundo"),
        ),
    ]
    final = _FakeMessage(
        content=[_FakeTextBlock(text="Hola mundo")],
        usage=_FakeUsage(input_tokens=8, output_tokens=4),
    )
    ctx = _FakeStreamCtx(events=events, final=final)
    gateway = AnthropicDirectGateway(
        api_key="test",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(stream_ctx=ctx),  # type: ignore[arg-type]
    )

    collected: list[tuple[str, dict[str, object]]] = []
    async for ev in gateway.stream([ChatMessage(role="user", content="hi")]):
        collected.append((ev.kind, dict(ev.payload)))

    # Dos text + un stop
    assert [k for k, _ in collected] == ["text", "text", "stop"]
    assert collected[0][1]["delta"] == "Hola"
    assert collected[1][1]["delta"] == " mundo"
    assert collected[2][1]["input_tokens"] == 8
    assert collected[2][1]["output_tokens"] == 4
    assert collected[2][1]["model"] == "claude-sonnet-4-5"
    assert collected[2][1]["stop_reason"] == "end_turn"


async def test_stream_emits_tool_use_start_event() -> None:
    """Cuando el modelo arranca un bloque tool_use, emitimos `tool_use_start`."""
    events = [
        _FakeStreamEvent(
            type="content_block_start",
            content_block=_FakeContentBlock(
                type="tool_use", id="tool_1", name="search_kb"
            ),
        ),
        _FakeStreamEvent(
            type="content_block_delta",
            delta=_FakeDelta(type="input_json_delta", partial_json='{"q":'),
        ),
        _FakeStreamEvent(
            type="content_block_delta",
            delta=_FakeDelta(type="input_json_delta", partial_json='"flaky"}'),
        ),
    ]
    final = _FakeMessage(
        content=[],
        usage=_FakeUsage(input_tokens=5, output_tokens=10),
    )
    ctx = _FakeStreamCtx(events=events, final=final)
    gateway = AnthropicDirectGateway(
        api_key="test",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(stream_ctx=ctx),  # type: ignore[arg-type]
    )

    events_out = [
        (ev.kind, dict(ev.payload))
        async for ev in gateway.stream([ChatMessage(role="user", content="hi")])
    ]
    kinds = [k for k, _ in events_out]
    assert "tool_use_start" in kinds
    tool_start = next(e for k, e in events_out if k == "tool_use_start")
    assert tool_start["id"] == "tool_1"
    assert tool_start["name"] == "search_kb"


async def test_stream_emits_error_event_when_sdk_raises() -> None:
    class _ExplodingCtx(_FakeStreamCtx):
        async def __aenter__(self) -> _FakeStreamCtx:  # type: ignore[override]
            raise RuntimeError("network down")

    ctx = _ExplodingCtx(events=[], final=_FakeMessage([], _FakeUsage()))
    gateway = AnthropicDirectGateway(
        api_key="test",
        default_model="claude-sonnet-4-5",
        client=_FakeAnthropic(stream_ctx=ctx),  # type: ignore[arg-type]
    )

    events_out = [
        (ev.kind, dict(ev.payload))
        async for ev in gateway.stream([ChatMessage(role="user", content="hi")])
    ]
    assert events_out[-1][0] == "error"
    assert "network down" in str(events_out[-1][1]["message"])
    assert events_out[-1][1]["type"] == "RuntimeError"
