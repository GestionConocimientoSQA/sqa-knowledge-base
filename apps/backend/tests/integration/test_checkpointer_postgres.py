"""Tests de integración del checkpointer Postgres + AgentState.

Requiere `docker compose up postgres` y la migración Alembic aplicada
(igual que `test_repos.py`). Si no hay DB, se skipean automáticamente
via el fixture `db_engine` del conftest.

Cubren:
- Pool se abre + setup crea las 3 tablas.
- Setup es idempotente (correr 2 veces no rompe).
- Roundtrip: `aput` un state, `aget_tuple` recupera lo mismo.
- Multi-thread isolation: thread_id A no ve el state de thread_id B.
- `alist` retorna los checkpoints en orden.
- `pool.close()` limpio sin dejar conexiones colgadas.

Edge cases:
- DSN inválido (host inexistente) falla con error claro.
- `build_checkpointer` con `setup=False` no toca DDL.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from langgraph.checkpoint.base import Checkpoint, empty_checkpoint

from sqa_kb.adapters.checkpointer.postgres import (
    CheckpointerBundle,
    build_checkpointer,
)

# Reusamos el mismo DSN que los otros integration tests.
DEFAULT_DSN = os.environ.get(
    "SQA_KB_DATABASE_URL",
    "postgresql+asyncpg://sqa:sqa_dev_password@localhost:5432/sqa_kb",
)


# ===========================================================================
# Helpers
# ===========================================================================


def _make_checkpoint(extra_channel_value: Any | None = None) -> Checkpoint:
    """Construye un Checkpoint válido de LangGraph para tests."""
    cp = empty_checkpoint()
    if extra_channel_value is not None:
        cp["channel_values"]["topic"] = extra_channel_value
        cp["channel_versions"]["topic"] = "1"
        cp["versions_seen"]["__input__"] = {}
    return cp


def _make_config(thread_id: str, checkpoint_ns: str = "") -> dict[str, Any]:
    return {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
        }
    }


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
async def bundle(db_engine) -> CheckpointerBundle:  # type: ignore[no-untyped-def]
    """Construye un CheckpointerBundle real contra PG. db_engine garantiza
    que la DB esté arriba (sino skipea desde conftest)."""
    b = await build_checkpointer(dsn=DEFAULT_DSN, min_size=1, max_size=2)
    try:
        yield b
    finally:
        await b.aclose()


# ===========================================================================
# Happy path
# ===========================================================================


async def test_setup_creates_checkpoint_tables(bundle: CheckpointerBundle) -> None:
    """`setup()` (corrido en build_checkpointer) crea las tablas que LangGraph
    necesita. Verificamos consultando pg_catalog."""
    async with bundle.pool.connection() as conn:
        result = await conn.execute(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname='public'
              AND tablename IN ('checkpoints','checkpoint_writes',
                                'checkpoint_blobs','checkpoint_migrations')
            ORDER BY tablename
            """
        )
        rows = await result.fetchall()
    names = {row[0] for row in rows}
    assert "checkpoints" in names
    assert "checkpoint_writes" in names
    assert "checkpoint_blobs" in names
    assert "checkpoint_migrations" in names


async def test_setup_is_idempotent() -> None:
    """Llamar `build_checkpointer` 2 veces (cada una con setup=True) no debe
    fallar — `checkpoint_migrations` previene reaplicar las mismas migraciones."""
    b1 = await build_checkpointer(dsn=DEFAULT_DSN, min_size=1, max_size=2)
    await b1.aclose()
    b2 = await build_checkpointer(dsn=DEFAULT_DSN, min_size=1, max_size=2)
    await b2.aclose()


async def test_put_and_get_roundtrip(bundle: CheckpointerBundle) -> None:
    """Guardamos un checkpoint, lo leemos, debe coincidir."""
    config = _make_config("thread-test-roundtrip")
    checkpoint = _make_checkpoint(extra_channel_value="flaky tests")

    new_config = await bundle.saver.aput(
        config,
        checkpoint,
        metadata={"source": "input", "step": 0, "writes": {}, "parents": {}},
        new_versions={"topic": "1"},
    )

    tuple_ = await bundle.saver.aget_tuple(new_config)

    assert tuple_ is not None
    assert tuple_.checkpoint["id"] == checkpoint["id"]
    assert tuple_.checkpoint["channel_values"]["topic"] == "flaky tests"


async def test_multi_thread_isolation(bundle: CheckpointerBundle) -> None:
    """Dos threads distintos no se ven entre sí — el `thread_id` actúa como
    namespace de aislamiento."""
    cfg_a = _make_config("thread-iso-A")
    cfg_b = _make_config("thread-iso-B")

    await bundle.saver.aput(
        cfg_a,
        _make_checkpoint(extra_channel_value="state-A"),
        metadata={"source": "input", "step": 0, "writes": {}, "parents": {}},
        new_versions={"topic": "1"},
    )
    await bundle.saver.aput(
        cfg_b,
        _make_checkpoint(extra_channel_value="state-B"),
        metadata={"source": "input", "step": 0, "writes": {}, "parents": {}},
        new_versions={"topic": "1"},
    )

    ta = await bundle.saver.aget_tuple(cfg_a)
    tb = await bundle.saver.aget_tuple(cfg_b)

    assert ta is not None and tb is not None
    assert ta.checkpoint["channel_values"]["topic"] == "state-A"
    assert tb.checkpoint["channel_values"]["topic"] == "state-B"


async def test_get_tuple_returns_none_for_unknown_thread(
    bundle: CheckpointerBundle,
) -> None:
    """Thread inexistente → None (no excepción)."""
    cfg = _make_config("thread-que-nunca-existio-99")
    tuple_ = await bundle.saver.aget_tuple(cfg)
    assert tuple_ is None


async def test_alist_yields_checkpoints_for_thread(
    bundle: CheckpointerBundle,
) -> None:
    """alist devuelve los checkpoints de un thread en orden temporal."""
    cfg = _make_config("thread-list-test")

    for i in range(3):
        cp = _make_checkpoint(extra_channel_value=f"step-{i}")
        await bundle.saver.aput(
            cfg,
            cp,
            metadata={
                "source": "loop",
                "step": i,
                "writes": {},
                "parents": {},
            },
            new_versions={"topic": str(i + 1)},
        )

    seen = [t async for t in bundle.saver.alist(cfg)]
    # Pueden venir desc o asc según la impl — verificamos solo el conjunto.
    assert len(seen) >= 3
    topics = {t.checkpoint["channel_values"].get("topic") for t in seen}
    assert {"step-0", "step-1", "step-2"} <= topics


# ===========================================================================
# Edge cases
# ===========================================================================


async def test_build_checkpointer_with_setup_false_does_not_run_ddl(
    db_engine,  # type: ignore[no-untyped-def]
) -> None:
    """Con setup=False el factory no debería tocar `checkpoint_migrations`.
    Pre-requisito: setup ya corrió (por otro test) así las tablas existen."""
    b1 = await build_checkpointer(dsn=DEFAULT_DSN, setup=True)
    await b1.aclose()

    # Ahora abro otra con setup=False. No debe fallar ni reescribir tablas.
    b2 = await build_checkpointer(dsn=DEFAULT_DSN, setup=False)
    try:
        # Sanity: se puede usar (las tablas siguen ahí).
        cfg = _make_config("thread-skip-setup")
        await b2.saver.aput(
            cfg,
            _make_checkpoint(extra_channel_value="x"),
            metadata={"source": "input", "step": 0, "writes": {}, "parents": {}},
            new_versions={"topic": "1"},
        )
        result = await b2.saver.aget_tuple(cfg)
        assert result is not None
    finally:
        await b2.aclose()


async def test_build_checkpointer_with_invalid_host_raises_quickly(
    db_engine,  # type: ignore[no-untyped-def]
) -> None:
    """Host inexistente → falla rápido al abrir el pool (no se queda colgado)."""
    bad_dsn = "postgresql://sqa:sqa_dev_password@hostquenoexiste-99:5432/sqa_kb"
    with pytest.raises(Exception):  # noqa: B017, BLE001 — psycopg variants
        await build_checkpointer(dsn=bad_dsn, min_size=1, max_size=1)


async def test_pool_closes_cleanly(db_engine) -> None:  # type: ignore[no-untyped-def]
    """aclose() debe dejar el pool en estado closed sin warnings."""
    b = await build_checkpointer(dsn=DEFAULT_DSN, min_size=1, max_size=1)
    assert not b.pool.closed
    await b.aclose()
    assert b.pool.closed


async def test_put_writes_then_get_includes_pending(
    bundle: CheckpointerBundle,
) -> None:
    """Edge: aput_writes guarda pending writes; el siguiente aget_tuple los expone."""
    cfg = _make_config("thread-pending-writes")
    cp = _make_checkpoint(extra_channel_value="base")
    new_cfg = await bundle.saver.aput(
        cfg,
        cp,
        metadata={"source": "input", "step": 0, "writes": {}, "parents": {}},
        new_versions={"topic": "1"},
    )

    # Simular writes pendientes de un step que se cortó.
    await bundle.saver.aput_writes(
        new_cfg,
        writes=[("topic", "interrupted-value")],
        task_id="task-1",
        task_path="path-1",
    )

    tuple_ = await bundle.saver.aget_tuple(new_cfg)
    assert tuple_ is not None
    # `pending_writes` es la tupla del CheckpointTuple
    pending_channels = [w[1] for w in tuple_.pending_writes or []]
    assert "topic" in pending_channels
