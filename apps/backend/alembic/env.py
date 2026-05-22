"""Alembic env — async + introspección automática del metadata.

Lee el DSN desde `SQA_KB_DATABASE_URL` (via `sqa_kb.config.Settings`) en
lugar del `alembic.ini`. Esto centraliza la config y respeta el principio
12-factor: el mismo binario corre en dev, staging y prod cambiando solo
env vars.

Importa explícitamente el módulo de models para que `Base.metadata`
quede poblado cuando Alembic detecta cambios con `--autogenerate`.
"""

from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Asegurar que `src/` esté en sys.path antes de importar el paquete.
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sqa_kb.adapters.repositories.postgres import models  # noqa: F401  (load tables)
from sqa_kb.adapters.repositories.postgres.base import Base
from sqa_kb.config import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Sobrescribir la URL del .ini con la de las env vars (12-factor).
settings = get_settings()
if settings.database_url is not None:
    config.set_main_option("sqlalchemy.url", settings.database_url.get_secret_value())


def run_migrations_offline() -> None:
    """Modo offline — genera el SQL sin conectar a la DB."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
