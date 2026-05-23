"""Factory del checkpointer PostgreSQL para LangGraph.

`AsyncPostgresSaver` se construye con un `psycopg.AsyncConnection` o un
`AsyncConnectionPool`. Acá manejamos el pool nosotros para:
1. Compartir conexiones entre llamadas concurrentes del agente.
2. Cerrar limpiamente en el lifespan shutdown del app.
3. Health-check con un `SELECT 1` rápido.

`AsyncPostgresSaver` espera DSN psycopg (`postgresql://...`), no asyncpg
(`postgresql+asyncpg://...`). El helper `psycopg_dsn()` lo convierte.

Setup idempotente: `.setup()` verifica `checkpoint_migrations` y aplica
solo migraciones nuevas — se puede llamar en cada arranque sin riesgo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)


# ===========================================================================
# DSN conversion
# ===========================================================================


def psycopg_dsn(asyncpg_dsn: str) -> str:
    """Convierte `postgresql+asyncpg://...` a `postgresql://...`.

    SQLAlchemy con asyncpg usa el prefijo `postgresql+asyncpg`, pero
    `psycopg`/`AsyncPostgresSaver` solo conoce `postgresql`. Si el DSN ya
    viene en formato psycopg lo devolvemos intacto.

    Otros prefijos (`postgres://`, `postgresql+psycopg://`) también se
    normalizan a `postgresql://`.
    """
    if not asyncpg_dsn:
        raise ValueError("DSN vacío — setear SQA_KB_DATABASE_URL primero")
    # Casos contemplados:
    # - postgresql+asyncpg://...   → postgresql://...
    # - postgresql+psycopg://...   → postgresql://...
    # - postgres://...             → postgresql://... (alias histórico)
    # - postgresql://...           → idem (passthrough)
    for prefix, target in (
        ("postgresql+asyncpg://", "postgresql://"),
        ("postgresql+psycopg://", "postgresql://"),
        ("postgres://", "postgresql://"),
    ):
        if asyncpg_dsn.startswith(prefix):
            return target + asyncpg_dsn[len(prefix) :]
    if asyncpg_dsn.startswith("postgresql://"):
        return asyncpg_dsn
    raise ValueError(
        f"DSN no reconocido: {asyncpg_dsn!r}. "
        "Se esperaba un prefijo postgresql:// o postgresql+asyncpg://."
    )


# ===========================================================================
# Bundle returned to main.py
# ===========================================================================


@dataclass(slots=True)
class CheckpointerBundle:
    """Recursos del checkpointer que el lifespan del app necesita
    administrar. La idea es que `main.py` haga `await bundle.aclose()`
    al shutdown — no que cada caller se preocupe por el pool.
    """

    pool: AsyncConnectionPool
    saver: AsyncPostgresSaver

    async def aclose(self) -> None:
        """Cerrá el pool — el saver no tiene close propio, vive sobre el pool."""
        await self.pool.close()


# ===========================================================================
# Factory
# ===========================================================================


async def build_checkpointer(
    *,
    dsn: str,
    min_size: int = 1,
    max_size: int = 8,
    setup: bool = True,
) -> CheckpointerBundle:
    """Crea pool psycopg + saver listo para usar.

    Pasos:
    1. Convierte DSN si viene en formato asyncpg.
    2. Abre `AsyncConnectionPool` con `min_size..max_size` conexiones.
    3. Construye `AsyncPostgresSaver(pool)`.
    4. Si `setup=True`, llama `.setup()` (idempotente — crea/migra tablas).

    `setup=False` solo conviene cuando un test ya verificó que las tablas
    existen y no querés re-correr migraciones en cada arranque (p.ej. en
    paralelo).
    """
    target_dsn = psycopg_dsn(dsn)
    # `open=False` evita race en factories — `aopen()` lo hace explícito.
    pool = AsyncConnectionPool(
        conninfo=target_dsn,
        min_size=min_size,
        max_size=max_size,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0},
        # autocommit=True es obligatorio para AsyncPostgresSaver — los CTE
        # de upsert no funcionan dentro de una transacción larga.
        # prepare_threshold=0 desactiva prepared statements (compat con pgbouncer).
    )
    await pool.open(wait=True, timeout=10.0)
    saver = AsyncPostgresSaver(conn=pool)  # type: ignore[arg-type]
    if setup:
        try:
            await saver.setup()
        except Exception:
            # Si falla setup cerramos el pool para no dejar conexiones colgadas.
            logger.exception("setup del checkpointer falló — cerrando pool")
            await pool.close()
            raise
    return CheckpointerBundle(pool=pool, saver=saver)
