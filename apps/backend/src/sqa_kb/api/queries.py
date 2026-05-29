"""Endpoint POST /queries — consulta directa al KB (Fase 3.5).

Ejecuta hybrid search (vector + FTS) sobre `document_chunks` y devuelve
los top-K chunks más relevantes. Además persiste:

- Una fila en `queries` (modo B desde el frontend, alimenta hot topics
  + gap detection del dashboard).
- Una fila en `query_citations` por cada chunk retornado (grafo de citas
  + KPIs).

A diferencia de `/sessions/{id}/messages` (el endpoint streaming del
agente), `/queries` es síncrono — un solo request/response. Sirve al
caso de uso "consulta rápida" del frontend sin abrir una sesión.

IDOR / Multi-tenant (Fase 9.3)
==============================
El KB está scopeado por proyecto. El body acepta `projectId` obligatorio
y el endpoint valida que el caller sea miembro del proyecto (o GK Lead)
antes de consultar el retriever. Sin esa validación cualquier usuario
autenticado podría pedir chunks de proyectos ajenos.

Errors
======
- 401 si falta auth (manejado por `CurrentUser`).
- 422 si el body es inválido (query vacía, top_k fuera de rango).
- 500 si el `HybridSearcher` no fue cableado (cohere_api_key ausente al
  startup) — el mensaje del handler global cuenta cuál es el problema.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from sqa_kb.api.dependencies import (
    CurrentUser,
    KbSearcherDep,
    ProjectServiceDep,
    QueryRepoDep,
)
from sqa_kb.domain.entities import Query, QueryCitation
from sqa_kb.domain.errors import ForbiddenError
from sqa_kb.domain.value_objects import CategoryCode, DocTypeCode

router = APIRouter(tags=["queries"], prefix="/queries")


# ===========================================================================
# Schemas
# ===========================================================================


class _CamelBase(BaseModel):
    """Base con `alias_generator=to_camel` — espejo del resto de la API
    (camelCase en el wire, snake_case en Python)."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class CreateQueryBody(_CamelBase):
    """Body para POST /queries."""

    project_id: str = Field(min_length=1, max_length=64)
    """UUID del proyecto cuyo KB se consulta. **Obligatorio desde Fase 9.3**.
    El backend valida que el caller sea miembro o `gk_lead`."""
    query: str = Field(min_length=1, max_length=2000)
    """Texto de la consulta. 1-2000 chars."""
    top_k: int = Field(default=5, ge=1, le=50)
    """Cuántos chunks devolver. Default 5; máximo 50 para acotar costo
    del round-trip y del JSON serialization."""
    carpetas: list[CategoryCode] | None = None
    """Filtro opcional por carpeta. `None` o lista vacía = sin filtro."""
    tipos: list[DocTypeCode] | None = None
    """Filtro opcional por tipo de documento."""
    authoritative_only: bool = False
    """Si True, restringe a documentos autoritativos."""


class QueryChunkPayload(_CamelBase):
    """Chunk retornado al frontend — espejo de `HybridChunk`."""

    chunk_id: str
    document_id: str
    chunk_index: int
    document_title: str
    document_type: str
    document_category: str
    authoritative: bool
    section_title: str
    snippet: str
    score: float
    vector_score: float
    fulltext_score: float


class QueryResultResponse(_CamelBase):
    """Response del POST /queries."""

    query_id: str
    items: list[QueryChunkPayload]
    total_returned: int
    has_result: bool


# ===========================================================================
# Endpoint
# ===========================================================================


@router.post("", response_model=QueryResultResponse, status_code=200)
async def create_query(
    body: CreateQueryBody,
    searcher: KbSearcherDep,
    query_repo: QueryRepoDep,
    projects: ProjectServiceDep,
    user: CurrentUser,
) -> QueryResultResponse:
    """Ejecuta hybrid search, persiste la consulta + citaciones, devuelve top-K.

    Valida la membership del caller en `body.project_id` antes de consultar
    al retriever. Sin acceso → 404 (no diferenciamos 'no existe' vs 'no
    podés verlo', misma convención IDOR del repo).
    """
    # Validación de acceso al proyecto. `projects.get` lanza NotFoundError
    # si el usuario no tiene visibilidad (gk_lead siempre la tiene).
    await projects.get(user, body.project_id)

    query_id = str(uuid.uuid4())
    asked_at = datetime.now(UTC)

    # Convertimos los enums a strings para no atar el searcher al StrEnum
    # del dominio (mantenemos el adapter agnóstico).
    carpetas_filter: Sequence[str] | None = (
        [str(c) for c in body.carpetas] if body.carpetas else None
    )
    tipos_filter: Sequence[str] | None = (
        [str(t) for t in body.tipos] if body.tipos else None
    )

    chunks = await searcher.search(
        body.query,
        project_id=body.project_id,
        top_k=body.top_k,
        carpetas=carpetas_filter,
        tipos=tipos_filter,
        authoritative_only=body.authoritative_only,
    )
    has_result = len(chunks) > 0
    answered_at = datetime.now(UTC)

    # Persistencia: query + una cita por chunk top-K. Hot topics + gap
    # detection del dashboard (Fase 7) leen de `queries`.
    await query_repo.record(
        Query(
            id=query_id,
            project_id=body.project_id,
            user_oid=user.oid,
            session_id=None,
            text=body.query,
            asked_at=asked_at,
            answered_at=answered_at,
            has_result=has_result,
        )
    )
    for chunk in chunks:
        # `section` es NonEmptyStr en el dominio → fallback a un guion si
        # el chunker no detectó título de sección.
        section = chunk.section_title or "—"
        await query_repo.add_citation(
            QueryCitation(
                query_id=query_id,
                document_id=chunk.document_id,
                section=section,
                snippet=chunk.snippet or "—",
            )
        )

    items = [
        QueryChunkPayload(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            chunk_index=c.chunk_index,
            document_title=c.document_title,
            document_type=c.document_type,
            document_category=c.document_category,
            authoritative=c.authoritative,
            section_title=c.section_title,
            snippet=c.snippet,
            score=c.score,
            vector_score=c.vector_score,
            fulltext_score=c.fulltext_score,
        )
        for c in chunks
    ]
    return QueryResultResponse(
        query_id=query_id,
        items=items,
        total_returned=len(items),
        has_result=has_result,
    )


# ===========================================================================
# Annotated helper — exportable para tests
# ===========================================================================


__all__ = [
    "CreateQueryBody",
    "QueryChunkPayload",
    "QueryResultResponse",
    "router",
]


# Re-export Annotated para compat con el patrón de otros routers.
_ = Annotated
