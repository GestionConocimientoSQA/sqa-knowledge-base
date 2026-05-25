"""Ring buffer in-memory de eventos SSE por sesión.

Permite reconexión: cuando el cliente reconecta enviando
`Last-Event-ID: N`, el orchestrator replaya los eventos `> N` que
quedaron en el buffer.

Diseño:
- **Por sesión**: un deque acotado por `max_per_session`. Si una sesión
  emite más eventos que ese cap, los más viejos se descartan (el
  cliente que reconecte muy tarde pierde esos).
- **TTL global**: 1 hora (§15.2 del ROADMAP). Después de TTL se purga la
  entrada de la sesión completa.
- **In-memory**: single-instance dev/staging. Cuando TI escale a
  multi-instancia, swap a Redis con misma interfaz pública.
- **Thread-safe**: usamos `asyncio.Lock` por sesión. No mezclamos
  async + threading.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field

from sqa_kb.api.sse.events import SseEvent

DEFAULT_TTL_SECONDS: float = 3600.0
"""1 hora — recomendación del ROADMAP."""

DEFAULT_MAX_PER_SESSION: int = 500
"""Cap de eventos por sesión. Un flow completo de captura emite ~50
eventos; 500 cubre con margen y reconexiones rápidas."""


@dataclass
class _SessionEntry:
    """Estado interno por sesión."""

    events: deque[SseEvent] = field(default_factory=deque)
    last_id: int = 0
    last_activity: float = field(default_factory=time.monotonic)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SseEventBuffer:
    """Buffer en memoria de eventos por sesión.

    Operaciones públicas:
    - `next_id(session_id)`: devuelve el próximo ID monotónico.
    - `append(event, session_id)`: guarda evento para futura reconexión.
    - `replay_after(session_id, last_event_id)`: yields eventos con
      `id > last_event_id` (en orden).
    - `purge_expired()`: borra entradas vencidas. Llamar periódicamente.
    """

    def __init__(
        self,
        *,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_per_session: int = DEFAULT_MAX_PER_SESSION,
    ) -> None:
        self._ttl = ttl_seconds
        self._max = max_per_session
        self._sessions: dict[str, _SessionEntry] = {}
        self._global_lock = asyncio.Lock()

    async def next_id(self, session_id: str) -> int:
        """Reserva y devuelve el próximo ID monotónico para la sesión.

        El caller usa este ID al construir el `SseEvent`. Si después
        descarta el evento sin `append`-earlo, el ID queda "gap" — no es
        un problema porque el cliente solo usa IDs para Last-Event-ID,
        no espera contigüidad.
        """
        entry = await self._get_or_create(session_id)
        async with entry.lock:
            entry.last_id += 1
            entry.last_activity = time.monotonic()
            return entry.last_id

    async def append(self, session_id: str, event: SseEvent) -> None:
        """Almacena el evento en el buffer. Drop oldest si supera `max`."""
        entry = await self._get_or_create(session_id)
        async with entry.lock:
            entry.events.append(event)
            entry.last_activity = time.monotonic()
            while len(entry.events) > self._max:
                entry.events.popleft()

    async def replay_after(
        self, session_id: str, last_event_id: int | None
    ) -> list[SseEvent]:
        """Devuelve los eventos con `id > last_event_id` (en orden).

        - `last_event_id=None` o `0` → no replaya nada (sesión nueva).
        - Si la sesión no existe → lista vacía.
        - Si el cap ya descartó eventos viejos, sólo replaya los que
          siguen presentes.
        """
        if last_event_id is None or last_event_id <= 0:
            return []
        entry = self._sessions.get(session_id)
        if entry is None:
            return []
        async with entry.lock:
            return [ev for ev in entry.events if ev.id > last_event_id]

    async def purge_expired(self, *, now: float | None = None) -> int:
        """Borra entradas con TTL vencido. Devuelve cantidad purgada.

        Llamar desde un background task (Fase 2.7+) cada algunos minutos.
        En tests podés inyectar `now` para forzar el tiempo.
        """
        current = now if now is not None else time.monotonic()
        expired: list[str] = []
        async with self._global_lock:
            for sid, entry in self._sessions.items():
                if current - entry.last_activity > self._ttl:
                    expired.append(sid)
            for sid in expired:
                del self._sessions[sid]
        return len(expired)

    async def drop_session(self, session_id: str) -> None:
        """Elimina la entrada de una sesión (p.ej. al cerrar manualmente)."""
        async with self._global_lock:
            self._sessions.pop(session_id, None)

    async def _get_or_create(self, session_id: str) -> _SessionEntry:
        async with self._global_lock:
            entry = self._sessions.get(session_id)
            if entry is None:
                entry = _SessionEntry()
                self._sessions[session_id] = entry
            return entry
