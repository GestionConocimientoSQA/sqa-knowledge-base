"""DeclarativeBase compartido por todos los SQLAlchemy models.

Una sola raíz hace que Alembic descubra automáticamente todas las
tablas desde el `metadata` único.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base SQLAlchemy 2.0. Sin `MappedAsDataclass` para evitar el orden
    estricto de defaults — los repos instancian con kwargs y los tipos
    `Mapped[]` ya dan strict typing en mypy."""
