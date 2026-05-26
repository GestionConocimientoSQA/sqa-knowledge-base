"""hnsw index on document_chunks.embedding

Crea el índice HNSW para acelerar la búsqueda vectorial del retriever
(Fase 3.3). Con m=16 y ef_construction=64 según ROADMAP §17.4 — valores
default recomendados por pgvector para datasets de hasta ~100k vectores.

El índice es sobre el operador `vector_cosine_ops` porque el adapter de
Cohere normaliza vectores y `cosine` es la métrica natural. Si en el
futuro se cambia a un embedder no-normalizado, habría que evaluar `l2`
o `inner_product`.

Notas operativas:
- `maintenance_work_mem = '1GB'` antes del CREATE INDEX acelera el build
  (recomendado por la doc oficial de pgvector). El SET es transaccional —
  no persiste fuera de esta migración.
- `IF NOT EXISTS` para que la migración sea idempotente si se reaplica.
- En PG de prod con muchos datos, este CREATE INDEX puede tardar varios
  minutos. Está bien — corre offline durante el deploy.

Revision ID: b3a7d1c2e0f4
Revises: 908138e3c1b2
Create Date: 2026-05-25 10:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3a7d1c2e0f4"
down_revision: str | Sequence[str] | None = "908138e3c1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea el índice HNSW sobre `document_chunks.embedding`."""
    op.execute("SET maintenance_work_mem = '1GB'")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    """Borra el índice HNSW. Las queries vuelven a fallback secuencial."""
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
