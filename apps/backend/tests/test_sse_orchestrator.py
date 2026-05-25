"""Tests del SseOrchestrator.

Estrategia: un `_FakeGraph` con la interfaz mínima que el orchestrator usa
(`astream`, `aget_state`). Eso nos permite definir los state changes paso
a paso y verificar exactamente qué eventos emite el orchestrator.

NO usamos un grafo real (LangGraph) para no acoplar los tests al runtime
del agente — esos tests viven en `test_agent_graph.py` y los nodos en
`test_agent_nodes_*.py`.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from sqa_kb.api.sse.buffer import SseEventBuffer
from sqa_kb.api.sse.events import SseEvent, SseEventType
from sqa_kb.api.sse.orchestrator import SseOrchestrator

# ===========================================================================
# Fake graph
# ===========================================================================


@dataclass
class _FakeStateSnapshot:
    values: dict[str, Any]


@dataclass
class _FakeGraph:
    """Imita la API que el orchestrator usa.

    `state_sequence`: lista de state dicts que astream va yieldeando uno
    por iteración. El primero es el state después del nodo de entrada,
    el segundo después del próximo, etc.

    `initial_state`: lo que aget_state devuelve antes del primer step
    (snapshot del checkpointer).

    `raise_on_stream`: si está, lo lanza desde astream para simular crash.
    """

    state_sequence: list[dict[str, Any]] = field(default_factory=list)
    initial_state: dict[str, Any] = field(default_factory=dict)
    raise_on_stream: Exception | None = None

    async def aget_state(self, config: dict[str, Any]) -> _FakeStateSnapshot:
        return _FakeStateSnapshot(values=self.initial_state)

    def astream(
        self,
        input_payload: dict[str, Any] | None,
        config: dict[str, Any],
        stream_mode: str = "values",
    ) -> AsyncIterator[dict[str, Any]]:
        # Async generator function (defined outside) — closure-friendly.
        outer = self

        async def gen() -> AsyncIterator[dict[str, Any]]:
            if outer.raise_on_stream is not None:
                raise outer.raise_on_stream
            for state in outer.state_sequence:
                yield state

        return gen()


def _parse_sse_events(payload: bytes) -> list[dict[str, Any]]:
    """Parsea el wire SSE en una lista de dicts {id, event, data}."""
    text = payload.decode("utf-8")
    blocks = [b for b in text.split("\n\n") if b.strip()]
    result: list[dict[str, Any]] = []
    for block in blocks:
        ev: dict[str, Any] = {}
        for line in block.splitlines():
            if line.startswith(": "):  # comentario
                ev["_comment"] = line[2:]
                continue
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if key == "id":
                ev["id"] = int(value)
            elif key == "event":
                ev["event"] = value
            elif key == "data":
                ev["data"] = json.loads(value) if value.startswith("{") else value
        if ev:
            result.append(ev)
    return result


async def _collect(stream: AsyncIterator[bytes]) -> bytes:
    out = b""
    async for chunk in stream:
        out += chunk
    return out


# ===========================================================================
# Empty state changes
# ===========================================================================


async def test_run_emits_message_start_and_end_when_no_state_changes() -> None:
    """Grafo sin diffs → solo message-start + message-end."""
    graph = _FakeGraph(state_sequence=[])
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())

    payload = await _collect(
        orch.run(session_id="s1", user_message={"role": "user", "content": "hi"})
    )
    events = _parse_sse_events(payload)
    event_types = [e.get("event") for e in events]
    assert event_types == [
        SseEventType.MESSAGE_START.value,
        SseEventType.MESSAGE_END.value,
    ]


async def test_run_includes_session_id_in_message_start() -> None:
    graph = _FakeGraph()
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())
    payload = await _collect(orch.run(session_id="s42", user_message=None))
    events = _parse_sse_events(payload)
    start = next(e for e in events if e["event"] == "message-start")
    assert start["data"]["session_id"] == "s42"
    assert start["data"]["message_id"].startswith("msg-")


async def test_run_message_end_includes_duration_ms() -> None:
    graph = _FakeGraph()
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())
    payload = await _collect(orch.run(session_id="s", user_message=None))
    events = _parse_sse_events(payload)
    end = next(e for e in events if e["event"] == "message-end")
    assert isinstance(end["data"]["duration_ms"], int)
    assert end["data"]["duration_ms"] >= 0


# ===========================================================================
# State diff → events
# ===========================================================================


async def test_emits_stage_change_when_stage_advances() -> None:
    graph = _FakeGraph(
        initial_state={"current_stage": "ETAPA_0"},
        state_sequence=[
            {"current_stage": "ETAPA_1"},
        ],
    )
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())
    payload = await _collect(
        orch.run(session_id="s", user_message={"role": "user", "content": "x"})
    )
    events = _parse_sse_events(payload)
    stage = next(e for e in events if e["event"] == "stage-change")
    assert stage["data"] == {"from": "ETAPA_0", "to": "ETAPA_1", "reason": ""}


async def test_emits_classification_when_new() -> None:
    graph = _FakeGraph(
        state_sequence=[
            {
                "classification": {
                    "category": "TEC",
                    "document_type": "MTEC",
                    "confidence": 0.9,
                    "reasoning": "x",
                }
            },
        ],
    )
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())
    payload = await _collect(
        orch.run(session_id="s", user_message={"role": "user", "content": "x"})
    )
    events = _parse_sse_events(payload)
    cls = next(e for e in events if e["event"] == "classification")
    assert cls["data"]["category"] == "TEC"


async def test_emits_kb_search_result_when_existing_docs_grow() -> None:
    graph = _FakeGraph(
        state_sequence=[
            {
                "existing_documents": [
                    {
                        "document_id": "TEC-x-2026-01-01",
                        "filename": "x.md",
                        "category": "TEC",
                        "document_type": "MTEC",
                        "distance": 0.3,
                        "created_at": "2026-01-01",
                    }
                ]
            }
        ],
    )
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())
    payload = await _collect(
        orch.run(session_id="s", user_message={"role": "user", "content": "x"})
    )
    events = _parse_sse_events(payload)
    kb = next(e for e in events if e["event"] == "kb-search-result")
    assert len(kb["data"]["existing_documents"]) == 1


async def test_emits_text_delta_for_new_agent_messages_only() -> None:
    """Mensajes nuevos del agente → text-delta. Mensajes user → ignorados."""
    graph = _FakeGraph(
        initial_state={"messages": [{"role": "user", "content": "hi"}]},
        state_sequence=[
            {
                "messages": [
                    {"role": "user", "content": "hi"},
                    {
                        "role": "agent",
                        "content": "Hola Andrés",
                        "stage": "ETAPA_0",
                    },
                ]
            }
        ],
    )
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())
    payload = await _collect(
        orch.run(session_id="s", user_message={"role": "user", "content": "hi"})
    )
    events = _parse_sse_events(payload)
    deltas = [e for e in events if e["event"] == "text-delta"]
    assert len(deltas) == 1
    assert deltas[0]["data"]["delta"] == "Hola Andrés"


async def test_emits_text_delta_skips_messages_without_content() -> None:
    """Mensajes con content vacío no generan text-delta (sino el cliente
    recibiría updates fantasma)."""
    graph = _FakeGraph(
        state_sequence=[
            {
                "messages": [
                    {"role": "agent", "content": "", "stage": "ETAPA_0"}
                ]
            }
        ],
    )
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())
    payload = await _collect(
        orch.run(session_id="s", user_message=None)
    )
    events = _parse_sse_events(payload)
    deltas = [e for e in events if e["event"] == "text-delta"]
    assert deltas == []


async def test_emits_citation_for_each_new_citation() -> None:
    graph = _FakeGraph(
        state_sequence=[
            {
                "citations": [
                    {
                        "document_id": "TEC-x-2026-01-01",
                        "filename": "x.md",
                        "chunk_id": "c1",
                        "section": None,
                        "snippet": "...",
                        "position": 1,
                    },
                    {
                        "document_id": "TEC-y-2026-02-01",
                        "filename": "y.md",
                        "chunk_id": "c2",
                        "section": None,
                        "snippet": "...",
                        "position": 2,
                    },
                ]
            }
        ],
    )
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())
    payload = await _collect(
        orch.run(session_id="s", user_message={"role": "user", "content": "x"})
    )
    events = _parse_sse_events(payload)
    citations = [e for e in events if e["event"] == "citation"]
    assert len(citations) == 2
    assert citations[0]["data"]["document_id"] == "TEC-x-2026-01-01"


async def test_emits_scoring_when_capture_scoring_set() -> None:
    graph = _FakeGraph(
        state_sequence=[
            {
                "capture_scoring": {
                    "specificity": 4,
                    "depth": 4,
                    "reusability": 3,
                    "uniqueness": 4,
                    "value_score": 3.8,
                    "observations": "buena",
                }
            }
        ],
    )
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())
    payload = await _collect(
        orch.run(session_id="s", user_message={"role": "user", "content": "x"})
    )
    events = _parse_sse_events(payload)
    scoring = next(e for e in events if e["event"] == "scoring")
    assert scoring["data"]["value_score"] == 3.8


async def test_emits_document_generated_when_id_set() -> None:
    graph = _FakeGraph(
        state_sequence=[
            {"generated_document_id": "MTEC-x-2026-05-23"}
        ],
    )
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())
    payload = await _collect(
        orch.run(session_id="s", user_message={"role": "user", "content": "x"})
    )
    events = _parse_sse_events(payload)
    doc = next(e for e in events if e["event"] == "document-generated")
    assert doc["data"]["document_id"] == "MTEC-x-2026-05-23"


async def test_emits_token_usage_with_delta_only() -> None:
    """Si el state acumula totales, el evento expone solo el delta del paso."""
    graph = _FakeGraph(
        initial_state={
            "total_input_tokens": 100,
            "total_output_tokens": 50,
            "total_cost_usd": 0.001,
        },
        state_sequence=[
            {
                "total_input_tokens": 150,
                "total_output_tokens": 70,
                "total_cost_usd": 0.0015,
            }
        ],
    )
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())
    payload = await _collect(
        orch.run(session_id="s", user_message={"role": "user", "content": "x"})
    )
    events = _parse_sse_events(payload)
    usage = next(e for e in events if e["event"] == "token-usage")
    assert usage["data"]["input_tokens"] == 50
    assert usage["data"]["output_tokens"] == 20
    assert usage["data"]["cost_usd"] == 0.0005


async def test_no_token_usage_event_when_no_change() -> None:
    graph = _FakeGraph(state_sequence=[{"total_input_tokens": 0}])
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())
    payload = await _collect(
        orch.run(session_id="s", user_message=None)
    )
    events = _parse_sse_events(payload)
    assert not any(e["event"] == "token-usage" for e in events)


# ===========================================================================
# Errores y cancelación
# ===========================================================================


async def test_error_in_graph_emits_error_event() -> None:
    graph = _FakeGraph(raise_on_stream=RuntimeError("LLM down"))
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())
    payload = await _collect(
        orch.run(session_id="s", user_message={"role": "user", "content": "x"})
    )
    events = _parse_sse_events(payload)
    err = next(e for e in events if e["event"] == "error")
    assert "LLM down" in err["data"]["message"]
    # Después del error, debe emitir message-end igual (cierre limpio).
    assert events[-1]["event"] == "message-end"


async def test_cancelled_error_propagates_without_emitting_error() -> None:
    """Cliente cierra → CancelledError. NO emitimos error event, solo cortamos."""
    graph = _FakeGraph(raise_on_stream=asyncio.CancelledError())
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())

    import pytest

    with pytest.raises(asyncio.CancelledError):
        async for _ in orch.run(
            session_id="s", user_message={"role": "user", "content": "x"}
        ):
            pass


# ===========================================================================
# Buffer integration + reconexión
# ===========================================================================


async def test_run_appends_events_to_buffer() -> None:
    buf = SseEventBuffer()
    graph = _FakeGraph()
    orch = SseOrchestrator(graph=graph, buffer=buf)

    await _collect(orch.run(session_id="s", user_message=None))
    # Después del run, el buffer guardó message-start + message-end. El
    # próximo `next_id` debe ser >= 3 (2 emitidos + reserva nueva).
    next_id = await buf.next_id("s")
    assert next_id > 2


async def test_replay_emits_buffered_events_before_new_ones() -> None:
    buf = SseEventBuffer()
    # Pre-cargamos 3 eventos viejos en el buffer.
    for i in range(1, 4):
        await buf.next_id("s")
        await buf.append(
            "s",
            SseEvent(id=i, type=SseEventType.TEXT_DELTA, data={"delta": f"old-{i}"}),
        )

    graph = _FakeGraph()
    orch = SseOrchestrator(graph=graph, buffer=buf)
    payload = await _collect(
        orch.run(session_id="s", user_message=None, last_event_id=1)
    )
    events = _parse_sse_events(payload)
    # Los primeros 2 deben ser los buffered (id=2 y id=3).
    assert events[0]["id"] == 2
    assert events[0]["data"]["delta"] == "old-2"
    assert events[1]["id"] == 3


async def test_reconnect_with_no_last_event_id_skips_replay() -> None:
    buf = SseEventBuffer()
    for i in range(1, 4):
        await buf.next_id("s")
        await buf.append(
            "s",
            SseEvent(id=i, type=SseEventType.TEXT_DELTA, data={"x": i}),
        )

    graph = _FakeGraph()
    orch = SseOrchestrator(graph=graph, buffer=buf)
    payload = await _collect(orch.run(session_id="s", user_message=None))
    events = _parse_sse_events(payload)
    # Solo eventos nuevos (message-start, message-end). No los viejos.
    assert all("delta" not in e.get("data", {}) for e in events)


# ===========================================================================
# Edge: stage None
# ===========================================================================


async def test_no_stage_change_event_when_new_stage_is_none() -> None:
    """Caso edge: nodo no setea current_stage (defensa)."""
    graph = _FakeGraph(
        initial_state={"current_stage": "ETAPA_0"},
        state_sequence=[{"messages": []}],  # no stage en update
    )
    orch = SseOrchestrator(graph=graph, buffer=SseEventBuffer())
    payload = await _collect(orch.run(session_id="s", user_message=None))
    events = _parse_sse_events(payload)
    assert not any(e["event"] == "stage-change" for e in events)
