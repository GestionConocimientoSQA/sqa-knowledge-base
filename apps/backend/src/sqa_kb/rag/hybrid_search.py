"""Búsqueda híbrida vector + full-text (Fase 3.4).

Combina dos rankings independientes con pesos lineales (70%/30% por
default, ROADMAP §17.5):

- **Vector** (`embedding <=> :qvec`): cubre similitud semántica —
  paráfrasis, sinónimos, traducciones internas.
- **Full-text** (`to_tsvector('spanish', content) @@ plainto_tsquery`):
  cubre matches léxicos exactos — nombres de herramientas, comandos,
  acrónimos, números de versión, identificadores. Para estos casos el
  embedding suele diluir la señal y el vector solo los pierde.

Score combinado
================
```
combined = (vec_score * vector_weight + fts_score * fts_weight)
           * (boost si autoritativo, 1.0 si no)
```

Normalización del FTS
=====================
`ts_rank_cd` retorna valores NO acotados (típicamente 0-3 pero puede
superar 10). Combinarlo a peso fijo con el vec_score que está en `[0, 1]`
hace que el FTS domine en chunks con muchos matches. Para acotarlo, se
usa el flag de normalización `32` de `ts_rank_cd`: divide por
`rank + 1`, llevando el resultado a `[0, 1)`. Esto mantiene la
comparabilidad con vec_score.

Una sola query SQL con CTE
==========================
A diferencia de hacer dos round-trips (uno al `VectorRetriever`, otro a
una capa FTS), esta implementación usa una sola query con CTEs y
`FULL OUTER JOIN`. Ventajas:
1. Un solo plan SQL → el planner decide en qué orden ejecuta las ramas.
2. Aprovecha ambos índices (HNSW + GIN) en la misma transacción.
3. El JOIN garantiza que un chunk que matchea en ambos lados aparece
   una sola vez con ambos scores; chunks que solo matchean en uno
   reciben 0 en el otro vía `COALESCE`.

NO reusa `VectorRetriever`
==========================
La tentación de composición (`HybridSearcher(retriever=...)`) implicaría
dos round-trips + duplicar el SQL de filtros en cada capa. Acá ambas
clases son peers del mismo módulo `rag/`, comparten puertos (`EmbedderPort`
+ `session_factory`) pero cada una compone su propia query. Si en el
futuro 3.5 necesita otra estrategia, se agrega otro peer.

Regla del usuario
=================
Sin requests reales al embedder en tests. El `EmbedderPort` se inyecta —
en unit tests se usa un fake; en integration test (con PG real) también.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.ports.gateways import EmbedderPort
from sqa_kb.rag.retriever import _build_snippet, _format_pgvector_literal

DEFAULT_TOP_K: int = 5
DEFAULT_VECTOR_WEIGHT: float = 0.7
DEFAULT_FTS_WEIGHT: float = 0.3
DEFAULT_AUTHORITATIVE_BOOST: float = 1.15
DEFAULT_CANDIDATES_PER_BRANCH: int = 50
"""Cuántos chunks pre-trae cada CTE antes de combinar. Generoso para
top_k=5 — cubre casos donde el match FTS perfecto está fuera del top-50
vector y viceversa. Configurable por construcción."""

DEFAULT_SNIPPET_MAX_CHARS: int = 240
DEFAULT_FTS_LANGUAGE: str = "spanish"
"""Idioma del diccionario de full-text. Hardcoded a 'spanish' porque la
migración GIN se creó sobre `to_tsvector('spanish', content)` — cambiar
acá sin re-crear el índice deja la query sin index scan."""


@dataclass(frozen=True, slots=True)
class HybridChunk:
    """Resultado individual de la búsqueda híbrida.

    Versión extendida de `RetrievedChunk` (no hereda — composición vía
    duplicación intencional para no acoplar dos DTOs). Agrega los scores
    crudos `vector_score` y `fulltext_score` que permiten al agente o a
    la UI decidir cómo presentar el resultado (ej. badge "match exacto"
    si fts_score > umbral).
    """

    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    snippet: str
    section_title: str
    score: float
    """Score combinado tras pesos y boost. Rango ~`[0, boost]`."""
    vector_score: float
    """`1 - cosine_distance`. `0.0` si el chunk solo matcheó por FTS."""
    fulltext_score: float
    """`ts_rank_cd(..., 32)` normalizado a [0,1). `0.0` si solo matcheó por vector."""
    document_title: str
    document_type: str
    document_category: str
    authoritative: bool


class HybridSearcher:
    """Búsqueda híbrida vector + full-text con boost autoritativos.

    Inyectables:
    - `embedder`: convierte la query del usuario en vector
      (`embed_query` con `input_type=search_query` en Cohere).
    - `session_factory`: para abrir AsyncSession contra PostgreSQL.
    - `vector_weight` / `fts_weight`: coeficientes lineales. La suma
      idealmente es 1.0, pero no es enforced — un caller que quiera
      otros pesos (ej. 0.5/0.5 para experimentos) puede pasarlos.
    - `default_authoritative_boost`: multiplicador del score para
      documentos autoritativos.
    - `candidates_per_branch`: top-K de cada CTE antes del JOIN.
    - `snippet_max_chars`: corte del `snippet` devuelto.
    """

    def __init__(
        self,
        *,
        embedder: EmbedderPort,
        session_factory: async_sessionmaker,  # type: ignore[type-arg]
        vector_weight: float = DEFAULT_VECTOR_WEIGHT,
        fts_weight: float = DEFAULT_FTS_WEIGHT,
        default_authoritative_boost: float = DEFAULT_AUTHORITATIVE_BOOST,
        candidates_per_branch: int = DEFAULT_CANDIDATES_PER_BRANCH,
        snippet_max_chars: int = DEFAULT_SNIPPET_MAX_CHARS,
    ) -> None:
        self._embedder = embedder
        self._session_factory = session_factory
        self._vector_weight = float(vector_weight)
        self._fts_weight = float(fts_weight)
        self._default_boost = default_authoritative_boost
        self._candidates = candidates_per_branch
        self._snippet_max_chars = snippet_max_chars

    async def search(
        self,
        query: str,
        *,
        project_id: str,
        top_k: int = DEFAULT_TOP_K,
        carpetas: Iterable[str] | None = None,
        tipos: Iterable[str] | None = None,
        authoritative_only: bool = False,
        authoritative_boost: float | None = None,
    ) -> Sequence[HybridChunk]:
        """Devuelve los top-K chunks por score combinado, desc.

        Args:
            query: texto del usuario. Se embedea + se usa como input de
                `plainto_tsquery('spanish', ...)`.
            project_id: UUID del proyecto al que pertenece la consulta.
                **Obligatorio desde Fase 9.3** — el filtro se aplica en
                ambas CTE (vector + FTS) para que ninguna rama traiga
                chunks fuera del tenant. El caller valida la membership
                del usuario antes de invocar.
            top_k: máximo de chunks a devolver. `top_k <= 0` devuelve [].
            carpetas: filtra por `documents.carpeta IN (...)`.
            tipos: filtra por `documents.tipo IN (...)`.
            authoritative_only: descarta no-autoritativos.
            authoritative_boost: override del multiplicador (None = default).
        """
        if top_k <= 0:
            return []
        # Defensa: query vacía o whitespace → plainto_tsquery devolvería
        # un tsquery vacío, que matchea cero filas. Cortocircuito.
        if not query or not query.strip():
            return []

        embedding_batch = await self._embedder.embed_query(query)
        if not embedding_batch.vectors:
            return []
        qvec_literal = _format_pgvector_literal(embedding_batch.vectors[0])

        boost = (
            authoritative_boost
            if authoritative_boost is not None
            else self._default_boost
        )

        # Construcción de filtros (mismo patrón que VectorRetriever — se
        # aplican en AMBAS CTE para no traer chunks fuera de scope desde
        # ninguna rama).
        # `d.project_id = :project_id` es OBLIGATORIO desde Fase 9.3.
        filter_clauses: list[str] = ["d.project_id = :project_id"]
        params: dict[str, object] = {
            "qvec": qvec_literal,
            "query_text": query,
            "fts_language": DEFAULT_FTS_LANGUAGE,
            "vec_weight": self._vector_weight,
            "fts_weight": self._fts_weight,
            "boost": float(boost),
            "candidates": int(self._candidates),
            "top_k": int(top_k),
            "project_id": project_id,
        }
        expanding_binds: list = []

        carpetas_list = [str(c) for c in carpetas] if carpetas else []
        if carpetas_list:
            filter_clauses.append("d.carpeta IN :carpetas")
            params["carpetas"] = carpetas_list
            expanding_binds.append(bindparam("carpetas", expanding=True))

        tipos_list = [str(t) for t in tipos] if tipos else []
        if tipos_list:
            filter_clauses.append("d.tipo IN :tipos")
            params["tipos"] = tipos_list
            expanding_binds.append(bindparam("tipos", expanding=True))

        if authoritative_only:
            filter_clauses.append("d.autoritativo = TRUE")

        # Predicados específicos de cada CTE.
        vec_where = ["c.embedding IS NOT NULL"] + filter_clauses
        # Nota: el `to_tsvector('spanish', c.content) @@ plainto_tsquery(...)`
        # debe matchear EXACTAMENTE la expresión del índice GIN para que
        # el planner lo use. No cambiar 'spanish' sin re-crear el índice.
        fts_where = [
            "to_tsvector('spanish', c.content) "
            "@@ plainto_tsquery('spanish', :query_text)"
        ] + filter_clauses
        vec_where_clause = " AND ".join(vec_where)
        fts_where_clause = " AND ".join(fts_where)

        sql = text(
            f"""
            WITH vector_results AS (
                SELECT
                    c.id AS chunk_id,
                    (1 - (c.embedding <=> CAST(:qvec AS vector))) AS vec_score
                FROM document_chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE {vec_where_clause}
                ORDER BY c.embedding <=> CAST(:qvec AS vector)
                LIMIT :candidates
            ),
            fts_results AS (
                SELECT
                    c.id AS chunk_id,
                    ts_rank_cd(
                        to_tsvector('spanish', c.content),
                        plainto_tsquery('spanish', :query_text),
                        32
                    ) AS fts_score
                FROM document_chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE {fts_where_clause}
                ORDER BY fts_score DESC
                LIMIT :candidates
            ),
            combined AS (
                SELECT
                    COALESCE(v.chunk_id, f.chunk_id) AS chunk_id,
                    COALESCE(v.vec_score, 0) AS vec_score,
                    COALESCE(f.fts_score, 0) AS fts_score
                FROM vector_results v
                FULL OUTER JOIN fts_results f ON v.chunk_id = f.chunk_id
            )
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
                comb.vec_score AS vec_score,
                comb.fts_score AS fts_score,
                (comb.vec_score * :vec_weight + comb.fts_score * :fts_weight)
                  * CASE WHEN d.autoritativo THEN :boost ELSE 1.0 END
                  AS combined_score
            FROM combined comb
            JOIN document_chunks c ON c.id = comb.chunk_id
            JOIN documents d ON d.id = c.document_id
            ORDER BY combined_score DESC
            LIMIT :top_k
            """
        )
        if expanding_binds:
            sql = sql.bindparams(*expanding_binds)

        async with self._session_factory() as db:
            result = await db.execute(sql, params)
            rows = result.mappings().all()

        chunks: list[HybridChunk] = []
        for row in rows:
            metadata = row["chunk_metadata"] or {}
            section_title = ""
            if isinstance(metadata, dict):
                section_title = str(metadata.get("section_title", ""))
            content_str = row["content"] or ""
            chunks.append(
                HybridChunk(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    chunk_index=int(row["chunk_index"]),
                    content=content_str,
                    snippet=_build_snippet(
                        content_str, max_chars=self._snippet_max_chars
                    ),
                    section_title=section_title,
                    score=float(row["combined_score"]),
                    vector_score=float(row["vec_score"]),
                    fulltext_score=float(row["fts_score"]),
                    document_title=row["doc_titulo"],
                    document_type=row["doc_tipo"],
                    document_category=row["doc_carpeta"],
                    authoritative=bool(row["doc_autoritativo"]),
                )
            )
        return chunks
