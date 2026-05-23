"""AsyncEngine + AsyncSession factory + dependencias FastAPI.

Una sola instancia de `AsyncEngine` por proceso (pool reusable). Cada request
abre/cierra su propia `AsyncSession` para evitar leakage de transacciones.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from sqa_kb.config import AppEnv, Settings
from sqa_kb.domain.errors import ExternalServiceError
from sqa_kb.observability.logging import get_logger
from sqa_kb.ports.gateways import HealthCheckResult

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# Type alias para que las dependencies de FastAPI tengan un nombre claro
# en sus signatures (`session: DatabaseSession`).
DatabaseSession = AsyncSession


def create_engine(settings: Settings) -> AsyncEngine:
    """Crea el AsyncEngine con la URL configurada. Llama UNA vez al startup."""
    if settings.database_url is None:
        raise ExternalServiceError(
            "SQA_KB_DATABASE_URL no está configurada — el backend no puede arrancar persistencia.",
            service="postgres",
        )

    # En tests usamos NullPool: TestClient crea/destruye event loops por
    # request y un connection pool persistente intenta cerrar connections
    # contra loops ya cerrados ("Event loop is closed"). NullPool abre
    # connection nueva cada vez — más lento pero estable en tests.
    extra: dict[str, object] = {}
    if settings.app_env is AppEnv.TEST:
        extra["poolclass"] = NullPool
    else:
        extra["pool_size"] = settings.database_pool_size
        extra["max_overflow"] = settings.database_pool_max_overflow
        extra["pool_pre_ping"] = True

    return create_async_engine(
        settings.database_url.get_secret_value(),
        echo=settings.database_echo,
        future=True,
        **extra,  # type: ignore[arg-type]
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Factory de sessions. Cada llamada al sessionmaker abre una nueva
    AsyncSession lista para usar dentro de un `async with`."""
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@asynccontextmanager
async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Helper para abrir una session con commit/rollback automáticos.

    Uso:
        async with session_scope(factory) as session:
            await session.execute(...)
            # commit automático al salir; rollback si hay excepción
    """
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()


class PostgresHealthCheck:
    """Verifica que el engine puede ejecutar `SELECT 1`."""

    name = "postgres"

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> HealthCheckResult:
        start = time.perf_counter()
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            duration_ms = (time.perf_counter() - start) * 1000
            return HealthCheckResult(
                name=self.name, healthy=True, duration_ms=duration_ms
            )
        except Exception as exc:  # noqa: BLE001
            duration_ms = (time.perf_counter() - start) * 1000
            return HealthCheckResult(
                name=self.name,
                healthy=False,
                detail=f"{type(exc).__name__}: {exc}",
                duration_ms=duration_ms,
            )
