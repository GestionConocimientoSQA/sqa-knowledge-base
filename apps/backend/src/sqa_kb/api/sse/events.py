"""Tipos de eventos SSE + encoder al wire format.

Los 14 eventos están definidos en §15.2 del ROADMAP. La forma del payload
de cada uno debe matchear lo que `apps/frontend/src/types/agent.ts` espera
en la unión `AgentEvent` — sino el reducer del frontend (Fase 6) descarta
los eventos no reconocidos.

Diseño:
- `SseEventType` Enum para evitar typos.
- `SseEvent` dataclass inmutable con `id` (monotonic int), `type` y `data`.
- `encode_sse(event)` produce el wire format:
    `id: 42\nevent: text-delta\ndata: {"delta":"..."}\n\n`
- Multi-line `data:` se split por línea automáticamente (regla SSE).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

# Keepalive cada 15s según §15.2 del ROADMAP. Connections con menos
# tráfico se cortan en algunos proxies (nginx, ALB) a los 30-60s.
SSE_KEEPALIVE_INTERVAL_SECONDS: float = 15.0


class SseEventType(StrEnum):
    """Catálogo cerrado de eventos SSE — alineado con §15.2 ROADMAP y
    con la unión `AgentEvent` del frontend (`types/agent.ts`)."""

    MESSAGE_START = "message-start"
    STAGE_CHANGE = "stage-change"
    CLASSIFICATION = "classification"
    KB_SEARCH_RESULT = "kb-search-result"
    TEXT_DELTA = "text-delta"
    TOOL_USE = "tool-use"
    TOOL_RESULT = "tool-result"
    CITATION = "citation"
    SCORING = "scoring"
    DOCUMENT_GENERATED = "document-generated"
    TOKEN_USAGE = "token-usage"
    MESSAGE_END = "message-end"
    ERROR = "error"
    PING = "ping"


@dataclass(frozen=True, slots=True)
class SseEvent:
    """Evento listo para encodearse al wire SSE.

    `id` es un entero monotónico por sesión — el cliente lo envía de
    vuelta como `Last-Event-ID` al reconectar para que el buffer le
    reemita los que se perdió.

    `data` es un dict JSON-serializable. El payload concreto depende
    del `type`.
    """

    id: int
    type: SseEventType
    data: dict[str, Any]


def encode_sse(event: SseEvent) -> bytes:
    """Convierte un `SseEvent` al wire format SSE.

    Wire ejemplo:
        id: 42
        event: text-delta
        data: {"delta": "Hola "}
        \n
    """
    payload = json.dumps(event.data, ensure_ascii=False, separators=(",", ":"))
    lines = [
        f"id: {event.id}",
        f"event: {event.type.value}",
    ]
    # Si `data` tuviera saltos de línea, SSE exige un `data:` por línea.
    # JSON serializado en una sola línea no tendría saltos, pero somos
    # defensivos por si en el futuro emitimos texto crudo.
    for chunk in payload.splitlines() or [""]:
        lines.append(f"data: {chunk}")
    return ("\n".join(lines) + "\n\n").encode("utf-8")


def encode_comment(text: str) -> bytes:
    """Comentario SSE (línea que empieza con `:`). Útil como heartbeat
    cuando NO querés que cuente como evento (no incrementa el `id`).
    """
    return (f": {text}\n\n").encode()
