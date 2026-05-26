"""Fixtures para tests de integración con PostgreSQL real.

Estos tests requieren `docker compose up postgres` y la migración Alembic
aplicada. Si la BD no está disponible, los tests se skipean en lugar de
fallar (para que `pytest` sin docker no rompa).

Cada test corre en una transacción que se hace rollback al final, así no
necesitamos truncate manual y los tests son aislados entre sí.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from sqa_kb.adapters.repositories.postgres.session import (
    create_engine,
    create_session_factory,
)
from sqa_kb.config import Settings

DEFAULT_TEST_DSN = (
    "postgresql+asyncpg://sqa:sqa_dev_password@localhost:5432/sqa_kb"
)


def _skip_if_no_db() -> bool:
    """True si no hay DB para test — los tests se skipean."""
    # Permitir override para CI / explicit opt-out.
    return os.environ.get("SQA_KB_SKIP_DB_TESTS") == "1"


pytestmark = pytest.mark.skipif(
    _skip_if_no_db(), reason="DB tests deshabilitados (SQA_KB_SKIP_DB_TESTS=1)"
)


@pytest.fixture(scope="session", autouse=True)
def _db_env() -> None:
    """Setea la URL de DB de test si no está ya seteada."""
    os.environ.setdefault("SQA_KB_DATABASE_URL", DEFAULT_TEST_DSN)
    os.environ["SQA_KB_APP_ENV"] = "test"
    # Reset del cache de get_settings entre suites.
    from sqa_kb import config

    config.get_settings.cache_clear()


@pytest_asyncio.fixture(scope="session")
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """Engine compartido por toda la sesión de tests."""
    engine = create_engine(Settings())
    # Smoke: probar conexión antes de los tests. Si falla, skipear.
    try:
        async with engine.connect() as conn:
            await conn.execute(_select_one())
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        pytest.skip(f"PostgreSQL no disponible para tests de integración: {exc}")
        return  # type: ignore[unreachable]
    try:
        yield engine
    finally:
        await engine.dispose()


def _select_one():  # type: ignore[no-untyped-def]
    from sqlalchemy import text

    return text("SELECT 1")


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Session aislada por test, con rollback final.

    Useful para tests que escriben — al hacer rollback la DB queda limpia
    para el siguiente test sin truncate manual.
    """
    factory = create_session_factory(db_engine)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture(scope="session")
async def session_factory(db_engine: AsyncEngine):  # type: ignore[no-untyped-def]
    """Factory directo — scope session porque la factory no tiene estado
    mutable. Cada test abre/cierra su propia AsyncSession desde la factory."""
    return create_session_factory(db_engine)


# Anular el _isolated_env autouse del root conftest dentro de tests/integration.
# Los integration tests SÍ necesitan SQA_KB_DATABASE_URL del shell para conectar
# a la DB real, así que ese autouse del root no aplica acá.
@pytest.fixture(autouse=True)
def _isolated_env():  # type: ignore[no-untyped-def]
    """No-op — sobreescribe el del root para que NO limpie env vars en integration."""
    return
