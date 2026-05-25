"""Orchestrator SSE — corre el grafo y traduce state diffs a eventos SSE.

Responsabilidades:
1. Recibir un user message + session_id + last_event_id (opcional).
2. Si hay last_event_id, replayar eventos buffereados.
3. Emitir `message-start`.
4. Invocar el grafo y observar state changes vía `astream(stream_mode="values")`.
5. Por cada diff emitir el evento SSE correspondiente (stage-change,
   classification, text-delta, citation, etc.).
6. Emitir `message-end` al cerrar.
7. Manejar cancelación (`asyncio.CancelledError` cuando el cliente
   cierra la conexión).
8. Heartbeat `ping` cada ~15s si la generación toma más tiempo.

Diseño:
- **Diff-based emission**: comparamos `state_prev` vs `state_new` después
  de cada paso del grafo. Los cambios discretos (classification nueva,
  citations agregadas, etc.) se traducen a eventos.
- **`text-delta` por mensaje completo**: en 2.6 emitimos un solo
  text-delta por mensaje del agente con el contenido entero (no
  streaming token-por-token). Fase 5+ podría usar `gateway.stream()`
  para granularidad real — el contrato del frontend ya lo soporta.
- **Sin LLM real**: el orchestrator no llama al LLM directo. Los nodos
  del grafo son quienes invocan `gateway.complete/stream`. El
  orchestrator solo observa.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqa_kb.api.sse.buffer import SseEventBuffer
from sqa_kb.api.sse.events import (
    SSE_KEEPALIVE_INTERVAL_SECONDS,
    SseEvent,
    SseEventType,
    encode_comment,
    encode_sse,
)

logger = logging.getLogger(__name__)


class SseOrchestrator:
    """Stream de eventos SSE para una invocación del grafo.

    `graph`: el `CompiledStateGraph` construido por `build_graph`.
    `buffer`: instancia compartida para reconexión.

    No mantiene estado entre llamadas — cada `run` es independiente.
    """

    def __init__(self, *, graph: Any, buffer: SseEventBuffer) -> None:
        self._graph = graph
        self._buffer = buffer

    async def run(
        self,
        *,
        session_id: str,
        user_message: dict[str, Any] | None,
        last_event_id: int | None = None,
    ) -> AsyncIterator[bytes]:
        """Generador async que yields chunks de bytes (formato SSE).

        - `user_message`: si None, el orchestrator no inyecta nada y solo
          continúa el grafo desde donde quedó (útil para retry/resume).
        - `last_event_id`: si presente, replayamos eventos `> N` antes de
          iniciar nuevo flujo.
        """
        start_time = time.monotonic()
        message_id = f"msg-{uuid.uuid4().hex[:12]}"

        # 1) Replay si reconectó
        async for chunk in self._replay(session_id, last_event_id):
            yield chunk

        # 2) message-start
        async for chunk in self._emit(
            session_id,
            SseEventType.MESSAGE_START,
            {"message_id": message_id, "session_id": session_id},
        ):
            yield chunk

        config = {"configurable": {"thread_id": session_id}}

        # 3) Snapshot del state previo (lo usamos para diff)
        prev_state = await self._snapshot(config)

        # 4) Ejecutar el grafo. Usamos `stream_mode="values"` para recibir
        # el state completo después de cada nodo.
        input_payload: dict[str, Any] | None = None
        if user_message is not None:
            input_payload = {"messages": [user_message]}

        try:
            async for value_state in self._graph.astream(
                input_payload, config, stream_mode="values"
            ):
                async for chunk in self._emit_diff_events(
                    session_id, prev_state, value_state
                ):
                    yield chunk
                prev_state = value_state
        except asyncio.CancelledError:
            # Cliente cerró conexión → no emitimos error, solo cortamos.
            logger.info(
                "SSE cancelled by client for session %s", session_id
            )
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Grafo falló durante streaming")
            async for chunk in self._emit(
                session_id,
                SseEventType.ERROR,
                {
                    "type": "internal",
                    "message": str(exc),
                    "retryable": False,
                },
            ):
                yield chunk

        # 5) message-end
        duration_ms = int((time.monotonic() - start_time) * 1000)
        async for chunk in self._emit(
            session_id,
            SseEventType.MESSAGE_END,
            {"message_id": message_id, "duration_ms": duration_ms},
        ):
            yield chunk

    # ===========================================================================
    # Internals
    # ===========================================================================

    async def _replay(
        self, session_id: str, last_event_id: int | None
    ) -> AsyncIterator[bytes]:
        if last_event_id is None or last_event_id <= 0:
            return
        events = await self._buffer.replay_after(session_id, last_event_id)
        for event in events:
            yield encode_sse(event)

    async def _emit(
        self, session_id: str, event_type: SseEventType, data: dict[str, Any]
    ) -> AsyncIterator[bytes]:
        event_id = await self._buffer.next_id(session_id)
        event = SseEvent(id=event_id, type=event_type, data=data)
        await self._buffer.append(session_id, event)
        yield encode_sse(event)

    async def _snapshot(self, config: dict[str, Any]) -> dict[str, Any]:
        """Devuelve el state actual del thread (o dict vacío si no existe).

        El checkpointer carga lo último persistido. Lo usamos como
        baseline para detectar diffs en el primer step.
        """
        try:
            snap = await self._graph.aget_state(config)
        except Exception:  # noqa: BLE001 — defensivo
            return {}
        if snap is None or snap.values is None:
            return {}
        return dict(snap.values)

    async def _emit_diff_events(
        self,
        session_id: str,
        prev: dict[str, Any],
        new: dict[str, Any],
    ) -> AsyncIterator[bytes]:
        """Traduce diffs prev→new en SSE events.

        Orden de emisión (importa porque el frontend procesa en secuencia):
        1. stage-change (si cambió el stage)
        2. classification (si nueva o cambió)
        3. kb-search-result (si existing_documents creció)
        4. text-delta + citation (mensajes nuevos del agente)
        5. scoring (si llegó capture_scoring)
        6. document-generated (si llegó generated_document_id)
        7. token-usage (si cambió total_input/output_tokens)
        """
        # 1) stage-change
        prev_stage = prev.get("current_stage")
        new_stage = new.get("current_stage")
        if new_stage and new_stage != prev_stage:
            async for chunk in self._emit(
                session_id,
                SseEventType.STAGE_CHANGE,
                {"from": prev_stage, "to": new_stage, "reason": ""},
            ):
                yield chunk

        # 2) classification
        new_classification = new.get("classification") or new.get(
            "suggested_classification"
        )
        prev_classification = prev.get("classification") or prev.get(
            "suggested_classification"
        )
        if new_classification and new_classification != prev_classification:
            payload = _model_dump(new_classification)
            async for chunk in self._emit(
                session_id, SseEventType.CLASSIFICATION, payload
            ):
                yield chunk

        # 3) kb-search-result
        prev_existing = prev.get("existing_documents") or []
        new_existing = new.get("existing_documents") or []
        if len(new_existing) > len(prev_existing):
            async for chunk in self._emit(
                session_id,
                SseEventType.KB_SEARCH_RESULT,
                {"existing_documents": [_model_dump(d) for d in new_existing]},
            ):
                yield chunk

        # 4) text-delta + citation
        prev_msgs = prev.get("messages") or []
        new_msgs = new.get("messages") or []
        if len(new_msgs) > len(prev_msgs):
            for msg in new_msgs[len(prev_msgs) :]:
                if msg.get("role") != "agent":
                    continue
                content = msg.get("content", "")
                if content:
                    async for chunk in self._emit(
                        session_id,
                        SseEventType.TEXT_DELTA,
                        {"delta": content},
                    ):
                        yield chunk

        # 4b) citations agregadas
        prev_citations = prev.get("citations") or []
        new_citations = new.get("citations") or []
        if len(new_citations) > len(prev_citations):
            for cit in new_citations[len(prev_citations) :]:
                async for chunk in self._emit(
                    session_id,
                    SseEventType.CITATION,
                    _model_dump(cit),
                ):
                    yield chunk

        # 5) scoring
        new_scoring = new.get("capture_scoring")
        prev_scoring = prev.get("capture_scoring")
        if new_scoring and new_scoring != prev_scoring:
            async for chunk in self._emit(
                session_id, SseEventType.SCORING, _model_dump(new_scoring)
            ):
                yield chunk

        # 6) document-generated
        new_doc_id = new.get("generated_document_id")
        prev_doc_id = prev.get("generated_document_id")
        if new_doc_id and new_doc_id != prev_doc_id:
            async for chunk in self._emit(
                session_id,
                SseEventType.DOCUMENT_GENERATED,
                {
                    "document_id": new_doc_id,
                    "filename": f"{new_doc_id}.md",
                    "download_url": f"/documents/{new_doc_id}/download",
                    "blob_path": "",
                },
            ):
                yield chunk

        # 7) token-usage
        prev_input = prev.get("total_input_tokens") or 0
        prev_output = prev.get("total_output_tokens") or 0
        prev_cost = prev.get("total_cost_usd") or 0.0
        new_input = new.get("total_input_tokens") or 0
        new_output = new.get("total_output_tokens") or 0
        new_cost = new.get("total_cost_usd") or 0.0
        if (
            new_input > prev_input
            or new_output > prev_output
            or new_cost > prev_cost
        ):
            async for chunk in self._emit(
                session_id,
                SseEventType.TOKEN_USAGE,
                {
                    "input_tokens": new_input - prev_input,
                    "output_tokens": new_output - prev_output,
                    "cost_usd": round(new_cost - prev_cost, 6),
                    "model": "",
                },
            ):
                yield chunk


def _model_dump(value: Any) -> dict[str, Any]:
    """Pydantic v2 model o dict → dict serializable JSON."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    # Fallback defensivo — JSON-encode + decode
    return json.loads(json.dumps(value, default=str))


# ===========================================================================
# Keepalive (helper público para el endpoint)
# ===========================================================================


async def keepalive_pings(interval: float = SSE_KEEPALIVE_INTERVAL_SECONDS) -> AsyncIterator[bytes]:
    """Async iter de comments `: ping`. Se mezcla con el stream real
    en el endpoint para mantener conexiones vivas detrás de proxies.

    Comentarios NO incrementan el id ni cuentan como eventos — son
    invisibles para el cliente excepto por el efecto de keep-alive.
    """
    while True:
        await asyncio.sleep(interval)
        yield encode_comment("ping")
