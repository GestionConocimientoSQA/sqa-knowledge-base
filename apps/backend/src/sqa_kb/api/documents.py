"""Endpoints del catálogo de documentos.

Espejo del contrato del frontend (`lib/api/documents.ts`, Fase 7.1):
- GET /documents              search con filtros + paginación
- GET /documents/{id}         detalle (incluye incoming citations + resumen)
- PATCH /documents/{id}/authoritative   solo admin (gated en service)
- GET /my-captures            scoped al `caller_oid` autenticado
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from sqa_kb.api.dependencies import (
    CurrentUser,
    DocumentRepoDep,
)
from sqa_kb.domain.entities import (
    Document,
    DocumentDetail,
    MyCapturesStats,
    _Base,
)
from sqa_kb.domain.errors import ForbiddenError, NotFoundError
from sqa_kb.domain.value_objects import CategoryCode, DocStatus, DocTypeCode

router = APIRouter(tags=["documents"])


class PaginatedDocuments(_Base):
    """Respuesta paginada — mismo shape que `PaginatedResult<DocumentItem>`
    del frontend (`types/domain.ts`). Hereda de `_Base` para serializar
    `has_more` ↔ `hasMore` automáticamente."""

    items: list[Document]
    total: int
    page: int
    limit: int
    has_more: bool


class MyCapturesResult(_Base):
    """Mismo shape que `MyCapturesResult` del frontend."""

    items: list[Document]
    stats: MyCapturesStats


@router.get("/documents", response_model=PaginatedDocuments)
async def search_documents(  # noqa: PLR0913 — espejo del contrato frontend
    repo: DocumentRepoDep,
    _user: CurrentUser,
    q: Annotated[str | None, Query(description="Búsqueda textual")] = None,
    carpetas: Annotated[list[CategoryCode] | None, Query()] = None,
    tipos: Annotated[list[DocTypeCode] | None, Query()] = None,
    estados: Annotated[list[DocStatus] | None, Query()] = None,
    autoritativo: Annotated[bool | None, Query()] = None,
    anonimizado: Annotated[bool | None, Query()] = None,
    min_score: Annotated[float | None, Query(ge=1.0, le=5.0)] = None,
    date_from: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    date_to: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    author_oid: Annotated[str | None, Query()] = None,
    sort_by: Annotated[
        str | None,
        Query(pattern=r"^(relevance|date_desc|score_desc|citations_desc)$"),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedDocuments:
    """Búsqueda paginada del catálogo. Mismos filtros que el mock-stub del
    frontend de Fase 7.1 — el contrato es el mismo."""
    offset = (page - 1) * limit
    items, total = await repo.search(
        query=q,
        carpetas=carpetas,
        tipos=tipos,
        estados=estados,
        autoritativo=autoritativo,
        anonimizado=anonimizado,
        min_score=min_score,
        date_from=date_from,
        date_to=date_to,
        author_oid=author_oid,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    return PaginatedDocuments(
        items=list(items),
        total=total,
        page=page,
        limit=limit,
        has_more=offset + limit < total,
    )


@router.get("/documents/{document_id}", response_model=DocumentDetail)
async def get_document_detail(
    document_id: str,
    repo: DocumentRepoDep,
    _user: CurrentUser,
) -> DocumentDetail:
    """Detalle del documento con `incoming_citations` + resumen."""
    detail = await repo.get_detail(document_id)
    if detail is None:
        raise NotFoundError(f"Documento {document_id} no encontrado")
    return detail


class ToggleAuthoritativeBody(BaseModel):
    value: bool = Field(description="Nuevo estado del flag autoritativo")


@router.patch("/documents/{document_id}/authoritative", response_model=Document)
async def set_authoritative(
    document_id: str,
    body: ToggleAuthoritativeBody,
    repo: DocumentRepoDep,
    user: CurrentUser,
) -> Document:
    """Marca/desmarca un documento como autoritativo. Solo admin —
    Owner sobre sus `carpetas_owned`, GK Lead sobre cualquiera.

    El enforcement vive acá (no en el repo) porque es decisión de servicio,
    no de persistencia. El audit log debe registrarlo cuando llegue 1B+.
    """
    if not user.is_admin:
        raise ForbiddenError("Solo Owner o GK Lead pueden marcar autoritativo")

    # Owner solo sobre sus carpetas. GK Lead sobre todo.
    if user.role_id == "owner":
        # Necesitamos leer la carpeta del doc.
        doc = await repo.get(document_id)
        if doc is None:
            raise NotFoundError(f"Documento {document_id} no encontrado")
        if doc.carpeta not in user.carpetas_owned:
            raise ForbiddenError(
                f"Owner no es responsable de la carpeta {doc.carpeta}"
            )

    return await repo.set_authoritative(
        document_id, value=body.value, caller_oid=user.oid
    )


@router.get("/my-captures", response_model=MyCapturesResult)
async def my_captures(
    repo: DocumentRepoDep,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> MyCapturesResult:
    """Captures del usuario autenticado + stats agregadas. Scoping por
    `caller_oid` automático — no expone los docs de otros."""
    items, stats = await repo.list_by_author(user.oid, limit=limit)
    return MyCapturesResult(items=list(items), stats=stats)
