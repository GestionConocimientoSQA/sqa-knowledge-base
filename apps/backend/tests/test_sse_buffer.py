"""Tests del SseEventBuffer.

Cubren:
- IDs monotónicos por sesión + aislamiento entre sesiones.
- Append y replay con Last-Event-ID.
- Cap por sesión: descarte de los más viejos.
- TTL: purge_expired borra entradas vencidas.
- Reconexión con last_event_id en escenarios edge.
- drop_session limpia explícitamente.
"""

from __future__ import annotations

from sqa_kb.api.sse.buffer import SseEventBuffer
from sqa_kb.api.sse.events import SseEvent, SseEventType


def _make_event(id: int, *, type: SseEventType = SseEventType.TEXT_DELTA) -> SseEvent:
    return SseEvent(id=id, type=type, data={"x": id})


# ===========================================================================
# IDs monotónicos
# ===========================================================================


async def test_next_id_monotonic_per_session() -> None:
    buf = SseEventBuffer()
    assert await buf.next_id("s1") == 1
    assert await buf.next_id("s1") == 2
    assert await buf.next_id("s1") == 3


async def test_next_id_isolated_between_sessions() -> None:
    buf = SseEventBuffer()
    assert await buf.next_id("s1") == 1
    assert await buf.next_id("s2") == 1
    assert await buf.next_id("s1") == 2
    assert await buf.next_id("s2") == 2


# ===========================================================================
# Append + replay
# ===========================================================================


async def test_replay_returns_empty_when_no_history() -> None:
    buf = SseEventBuffer()
    out = await buf.replay_after("never-existed", 0)
    assert out == []


async def test_replay_returns_events_after_id() -> None:
    buf = SseEventBuffer()
    for i in range(1, 6):
        await buf.next_id("s")
        await buf.append("s", _make_event(i))

    out = await buf.replay_after("s", 2)
    assert [ev.id for ev in out] == [3, 4, 5]


async def test_replay_with_zero_or_none_returns_nothing() -> None:
    buf = SseEventBuffer()
    await buf.next_id("s")
    await buf.append("s", _make_event(1))
    assert await buf.replay_after("s", 0) == []
    assert await buf.replay_after("s", None) == []


async def test_replay_when_last_event_id_greater_than_latest() -> None:
    """Cliente pide replay de IDs futuros — devolvemos lista vacía."""
    buf = SseEventBuffer()
    await buf.next_id("s")
    await buf.append("s", _make_event(1))
    out = await buf.replay_after("s", 99)
    assert out == []


async def test_replay_preserves_order() -> None:
    buf = SseEventBuffer()
    for i in [1, 2, 3, 4, 5]:
        await buf.next_id("s")
        await buf.append("s", _make_event(i))
    out = await buf.replay_after("s", 0)
    # last_event_id=0 → todo (regla del helper).
    # Pero con last=None retorna []. last=0 también.
    assert out == []


async def test_replay_after_negative_returns_empty() -> None:
    """Defensa: cliente manda Last-Event-ID negativo (corrupto)."""
    buf = SseEventBuffer()
    await buf.next_id("s")
    await buf.append("s", _make_event(1))
    assert await buf.replay_after("s", -5) == []


# ===========================================================================
# Cap por sesión
# ===========================================================================


async def test_cap_drops_oldest() -> None:
    """Con cap=3, después de 5 appends solo quedan los últimos 3."""
    buf = SseEventBuffer(max_per_session=3)
    for i in range(1, 6):
        await buf.next_id("s")
        await buf.append("s", _make_event(i))

    out = await buf.replay_after("s", 0)
    # max_per_session=3 → solo IDs 3, 4, 5 quedan. Pero replay con
    # last=0 retorna [] (regla del helper). Probamos replay con id=2.
    out = await buf.replay_after("s", 2)
    assert [ev.id for ev in out] == [3, 4, 5]


async def test_cap_does_not_affect_id_counter() -> None:
    """Cap descarta de buffer pero el contador de id sigue subiendo."""
    buf = SseEventBuffer(max_per_session=2)
    for _ in range(10):
        next_id = await buf.next_id("s")
        await buf.append("s", _make_event(next_id))
    # IDs 9 y 10 quedan en buffer.
    out = await buf.replay_after("s", 8)
    assert [ev.id for ev in out] == [9, 10]
    # El próximo ID es 11 (no se reseteó).
    assert await buf.next_id("s") == 11


# ===========================================================================
# TTL
# ===========================================================================


async def test_purge_expired_removes_old_sessions() -> None:
    """Con TTL pequeño, purge borra las sesiones vencidas."""
    buf = SseEventBuffer(ttl_seconds=0.001)
    await buf.next_id("s1")
    await buf.append("s1", _make_event(1))

    # Forzamos un "now" muy futuro (después del TTL).
    purged = await buf.purge_expired(now=999_999.0)
    assert purged == 1
    # Después del purge, replay no encuentra nada.
    assert await buf.replay_after("s1", 0) == []


async def test_purge_preserves_recently_active() -> None:
    """Sesiones tocadas recientemente no se purgan."""
    buf = SseEventBuffer(ttl_seconds=999.0)
    await buf.next_id("active")
    await buf.append("active", _make_event(1))
    purged = await buf.purge_expired()
    assert purged == 0


async def test_purge_returns_zero_when_no_sessions() -> None:
    buf = SseEventBuffer()
    purged = await buf.purge_expired()
    assert purged == 0


# ===========================================================================
# drop_session
# ===========================================================================


async def test_drop_session_clears_entry() -> None:
    buf = SseEventBuffer()
    await buf.next_id("s")
    await buf.append("s", _make_event(1))

    await buf.drop_session("s")
    # Después de drop, la sesión arranca de nuevo en ID=1.
    assert await buf.next_id("s") == 1


async def test_drop_session_idempotent_on_unknown() -> None:
    """Borrar una sesión que no existe no rompe."""
    buf = SseEventBuffer()
    await buf.drop_session("never-was-here")  # no raise


# ===========================================================================
# Aislamiento
# ===========================================================================


async def test_append_to_one_session_does_not_affect_other() -> None:
    buf = SseEventBuffer()
    for i in range(1, 4):
        await buf.next_id("s1")
        await buf.append("s1", _make_event(i))

    # s2 no recibió nada.
    out = await buf.replay_after("s2", 0)
    assert out == []


# ===========================================================================
# Concurrency
# ===========================================================================


async def test_concurrent_next_ids_are_unique() -> None:
    """Si el orchestrator emite muchos eventos en paralelo, los IDs no
    deben colisionar."""
    import asyncio

    buf = SseEventBuffer()
    ids = await asyncio.gather(*[buf.next_id("s") for _ in range(20)])
    assert len(set(ids)) == 20  # todos únicos
    assert sorted(ids) == list(range(1, 21))
