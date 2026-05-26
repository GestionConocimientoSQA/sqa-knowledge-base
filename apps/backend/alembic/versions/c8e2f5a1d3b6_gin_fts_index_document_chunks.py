"""gin fts index on document_chunks.content (spanish)

Crea el índice GIN funcional sobre `to_tsvector('spanish', content)` para
acelerar la búsqueda híbrida del `HybridSearcher` (Fase 3.4). Sin este
índice, `to_tsvector(...) @@ plainto_tsquery(...)` hace seq scan completo
de la tabla — inviable con 10k+ chunks.

Notas operativas:
- El índice es funcional (sobre una expresión), no sobre una columna —
  PG calcula `to_tsvector('spanish', content)` al insertar y mantiene
  los lexemas indexados.
- `to_tsvector('spanish', ...)` aplica stemming + stopwords del
  diccionario español (`pg_catalog.spanish`). Viene built-in en PG; no
  requiere extensions adicionales.
- El predicado de búsqueda en el hybrid searcher DEBE usar exactamente
  `to_tsvector('spanish', content)` (mismo formato) para que el planner
  use este índice. Cualquier divergencia (idioma distinto, columna
  diferente) hace fallback a seq scan.
- `IF NOT EXISTS` para idempotencia al reaplicar.

Revision ID: c8e2f5a1d3b6
Revises: b3a7d1c2e0f4
Create Date: 2026-05-25 14:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8e2f5a1d3b6"
down_revision: str | Sequence[str] | None = "b3a7d1c2e0f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea el índice GIN sobre `to_tsvector('spanish', content)`."""
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_content_fts
        ON document_chunks
        USING GIN (to_tsvector('spanish', content))
        """
    )


def downgrade() -> None:
    """Borra el índice GIN. La búsqueda FTS hace fallback a seq scan."""
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_content_fts")
