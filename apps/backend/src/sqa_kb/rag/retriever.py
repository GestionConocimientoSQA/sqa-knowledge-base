"""Retriever vectorial (Fase 3.3).

Compone una búsqueda semántica sobre `document_chunks` aprovechando:

- `pgvector` con operador `<=>` (cosine distance).
- Índice HNSW (`vector_cosine_ops`, m=16, ef_construction=64) creado por la
  migración Alembic `hnsw_index_document_chunks`.
- Boost de documentos autoritativos: el score crudo `1 - cosine_distance`
  se multiplica por `1.15` si `documents.autoritativo = TRUE`.

Decisión de diseño — separación ORDER BY vs SELECT
==================================================
El `ORDER BY` usa la distancia cruda (`embedding <=> :qvec`) para que el
planner aproveche el índice HNSW (que ordena por esa expresión). El boost
se aplica como columna `score` en el SELECT y el re-rank final ocurre en
Python sobre el top-K traído de la DB. K es chico (default 5) — el costo
del re-rank es despreciable comparado con habernos ahorrado el index scan
si el boost estuviese en el ORDER BY.

NO usa `ChunkRepository`
========================
El puerto `ChunkRepository` solo expone bulk_insert/delete/count para el
indexer. La query del retriever es lo suficientemente específica (SQL +
pgvector + boost) como para que abstraerla en otro puerto sea overhead
sin valor — un solo consumidor, un solo backend (pgvector). Si en el
futuro hace falta cambiar a Azure AI Search, este archivo entero se
reemplaza por otro adapter con la misma API pública del `VectorRetriever`.

Regla del usuario
=================
Sin requests reales al embedder en tests. El `EmbedderPort` se inyecta —
en unit tests se usa un fake; en integration test (con PG real) también
para no pegarle a Cohere.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.ports.gateways import EmbedderPort

DEFAULT_TOP_K: int = 5
DEFAULT_AUTHORITATIVE_BOOST: float = 1.15
"""Multiplicador del score para documentos `autoritativo=TRUE`. Valor
fijado por ROADMAP §17.4. Configurable por construcción para experimentos."""

DEFAULT_SNIPPET_MAX_CHARS: int = 240
"""Largo del snippet devuelto por el retriever. Suficiente para que el
agente/UI muestre contexto sin transmitir el chunk completo (que puede
llegar a ~700 tokens)."""


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """Resultado individual del retriever.

    Datos suficientes para que el agente cite el documento sin un round
    trip extra a `documents`. No es una `entity` del dominio — es un DTO
    de transporte del retriever. Si más adelante se necesita en `domain`,
    se promueve sin romper este código (composición, no herencia).
    """

    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    """Texto crudo del chunk (sin header contextual)."""
    snippet: str
    """Versión truncada del `content` para preview rápido."""
    section_title: str
    """Título de la sección (cuando el chunker la pudo derivar)."""
    score: float
    """Score combinado: `(1 - cosine_distance) * boost`. Rango ~[0, boost]."""
    document_title: str
    document_type: str
    document_category: str
    authoritative: bool


def _format_pgvector_literal(vector: Sequence[float]) -> str:
    """Serializa un vector Python a la representación textual de pgvector.

    pgvector acepta `'[0.1,0.2,...]'::vector`. Evitamos depender del
    type adapter `pgvector-asyncpg` para queries con `text()` — la
    representación string + cast explícito funciona en todos los drivers.
    """
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"


def _build_snippet(content: str, *, max_chars: int) -> str:
    """Trunca `content` a `max_chars` agregando `…` si se acortó.

    Defensa contra strings con saltos de línea — los reemplaza por
    espacio para que el snippet sea presentable en una sola línea (UI).
    """
    flat = " ".join(content.split())
    if len(flat) <= max_chars:
        return flat
    return flat[: max_chars - 1].rstrip() + "…"


class VectorRetriever:
    """Búsqueda semántica top-K con boost autoritativos.

    Inyectables:
    - `embedder`: convierte la query del usuario en vector
      (`embed_query` con `input_type=search_query` en Cohere).
    - `session_factory`: para abrir AsyncSession contra PostgreSQL.
    - `default_authoritative_boost`: multiplicador del score para
      autoritativos (configurable por construcción; el `retrieve()`
      también acepta override por llamada).
    - `snippet_max_chars`: corte del `snippet` devuelto.
    """

    def __init__(
        self,
        *,
        embedder: EmbedderPort,
        session_factory: async_sessionmaker,  # type: ignore[type-arg]
        default_authoritative_boost: float = DEFAULT_AUTHORITATIVE_BOOST,
        snippet_max_chars: int = DEFAULT_SNIPPET_MAX_CHARS,
    ) -> None:
        self._embedder = embedder
        self._session_factory = session_factory
        self._default_boost = default_authoritative_boost
        self._snippet_max_chars = snippet_max_chars

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        carpetas: Iterable[str] | None = None,
        tipos: Iterable[str] | None = None,
        authoritative_only: bool = False,
        authoritative_boost: float | None = None,
    ) -> Sequence[RetrievedChunk]:
        """Devuelve los top-K chunks más relevantes ordenados por score desc.

        Args:
            query: texto del usuario (se embedea con `input_type=search_query`).
            top_k: máximo de chunks a devolver. `top_k <= 0` devuelve [].
            carpetas: si se pasa, filtra por `documents.carpeta IN (...)`.
                Acepta strings o `CategoryCode` (StrEnum) indistintamente.
            tipos: idem `carpetas` pero para `documents.tipo`.
            authoritative_only: si True, descarta no-autoritativos del SQL.
            authoritative_boost: override del multiplicador. None = usa el
                de construcción.
        """
        if top_k <= 0:
            return []

        embedding_batch = await self._embedder.embed_query(query)
        if not embedding_batch.vectors:
            # El adapter Cohere garantiza 1 vector — defensa contra fakes
            # o adapters futuros que devuelvan vacío.
            return []
        qvec_literal = _format_pgvector_literal(embedding_batch.vectors[0])

        boost = (
            authoritative_boost
            if authoritative_boost is not None
            else self._default_boost
        )

        clauses: list[str] = ["c.embedding IS NOT NULL"]
        params: dict[str, object] = {
            "qvec": qvec_literal,
            "boost": float(boost),
            "top_k": int(top_k),
        }
        expanding_binds: list = []

        carpetas_list = [str(c) for c in carpetas] if carpetas else []
        if carpetas_list:
            clauses.append("d.carpeta IN :carpetas")
            params["carpetas"] = carpetas_list
            expanding_binds.append(bindparam("carpetas", expanding=True))

        tipos_list = [str(t) for t in tipos] if tipos else []
        if tipos_list:
            clauses.append("d.tipo IN :tipos")
            params["tipos"] = tipos_list
            expanding_binds.append(bindparam("tipos", expanding=True))

        if authoritative_only:
            clauses.append("d.autoritativo = TRUE")

        where_clause = " AND ".join(clauses)
        # Importante: las cláusulas WHERE son strings hardcodeados —
        # los valores SIEMPRE entran por bind params. No hay
        # concatenación de input del usuario en el SQL.
        sql = text(
            f"""
            SELECT
                c.id AS chunk_id,
                c.document_id AS document_id,
                c.chunk_index AS chunk_index,
                c.content AS content,
                c.metadata AS chunk_metadata,
                d.titulo AS doc_titulo,
                d.tipo AS doc_tipo,
                d.carpeta AS doc_carpeta,
                d.autoritativo AS doc_autoritativo,
                (1 - (c.embedding <=> CAST(:qvec AS vector)))
                  * CASE WHEN d.autoritativo THEN :boost ELSE 1.0 END
                  AS score
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE {where_clause}
            ORDER BY c.embedding <=> CAST(:qvec AS vector)
            LIMIT :top_k
            """
        )
        if expanding_binds:
            sql = sql.bindparams(*expanding_binds)

        async with self._session_factory() as db:
            result = await db.execute(sql, params)
            rows = result.mappings().all()

        chunks: list[RetrievedChunk] = []
        for row in rows:
            metadata = row["chunk_metadata"] or {}
            section_title = ""
            if isinstance(metadata, dict):
                section_title = str(metadata.get("section_title", ""))
            content_str = row["content"] or ""
            chunks.append(
                RetrievedChunk(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    chunk_index=int(row["chunk_index"]),
                    content=content_str,
                    snippet=_build_snippet(
                        content_str, max_chars=self._snippet_max_chars
                    ),
                    section_title=section_title,
                    score=float(row["score"]),
                    document_title=row["doc_titulo"],
                    document_type=row["doc_tipo"],
                    document_category=row["doc_carpeta"],
                    authoritative=bool(row["doc_autoritativo"]),
                )
            )

        # Re-rank en Python por score combinado (boost ya aplicado en el
        # SELECT). El ORDER BY de la DB usó la distancia cruda para no
        # perder el index scan HNSW; acá afinamos el orden final.
        chunks.sort(key=lambda c: c.score, reverse=True)
        return chunks
