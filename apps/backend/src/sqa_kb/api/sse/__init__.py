"""Subsistema SSE — Fase 2.6.

Composición:
- `events.py`: tipos de evento (14) + encoder al wire format SSE.
- `buffer.py`: ring buffer in-memory por sesión con TTL para `Last-Event-ID`.
- `orchestrator.py`: corre el grafo y traduce state changes → SSE events.

El endpoint `POST /sessions/{id}/messages` (en `api/messages.py`) usa
estos componentes — no hace falta importarlos directo desde el router.
"""

from sqa_kb.api.sse.buffer import SseEventBuffer
from sqa_kb.api.sse.events import (
    SSE_KEEPALIVE_INTERVAL_SECONDS,
    SseEvent,
    SseEventType,
    encode_sse,
)
from sqa_kb.api.sse.orchestrator import SseOrchestrator

__all__ = [
    "SSE_KEEPALIVE_INTERVAL_SECONDS",
    "SseEvent",
    "SseEventBuffer",
    "SseEventType",
    "SseOrchestrator",
    "encode_sse",
]
