"""Adapter PostgreSQL — SQLAlchemy 2.0 async + asyncpg + pgvector.

- `base.py` — `DeclarativeBase` compartido por todos los models.
- `models.py` — ORM models mapeados a las entities del domain.
- `session.py` — AsyncEngine + AsyncSession factory + dependency injection
  para FastAPI.
- `users.py`, `sessions.py`, `documents.py`, ... — implementaciones
  concretas de los Protocols de `ports.repositories`.

Las funciones de conversión `entity ↔ model` viven en cada repo concreto,
no en los models, para que los models queden minimalistas.
"""

from sqa_kb.adapters.repositories.postgres.session import (
    DatabaseSession,
    create_engine,
    create_session_factory,
)

__all__ = ["DatabaseSession", "create_engine", "create_session_factory"]
