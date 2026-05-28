"""Endpoints de ingesta de documentación aprobada — modo C (Fase 4.5).

Flujo:
    POST /ingestion              upload de archivo (multipart)
    POST /ingestion/{id}/classify  extrae + anonimiza + clasifica
    POST /ingestion/{id}/approve   crea Document + indexa con trazabilidad
    GET  /ingestion              lista filtrable por status

El router es un thin wrapper: valida el request HTTP y delega en
`IngestionService` (services/ingestion_service.py), que orquesta los
puertos. Auth requerida (CurrentUser).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Query, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from sqa_kb.api.dependencies import CurrentUser, IngestionServiceDep
from sqa_kb.domain.entities import IngestionItem
from sqa_kb.domain.value_objects import CategoryCode, DocTypeCode, IngestionStatus
from sqa_kb.services.ingestion_service import (
    TraceabilityInput,
    process_ingestion_background,
)

router = APIRouter(tags=["ingestion"], prefix="/ingestion")


# ===========================================================================
# Schemas
# ===========================================================================


class _CamelBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ApproveBody(_CamelBase):
    """Body del POST /ingestion/{id}/approve — trazabilidad obligatoria."""

    approved_by: str = Field(min_length=1, max_length=255)
    approval_date: str = Field(min_length=1, description="ISO date YYYY-MM-DD")
    source_origin: str = Field(default="", max_length=1024)
    version: str = Field(default="1.0", max_length=16)
    category: CategoryCode
    document_type: DocTypeCode


class RejectBody(_CamelBase):
    """Body del POST /ingestion/{id}/reject — motivo del rechazo."""

    reason: str = Field(min_length=1, max_length=1024)


# ===========================================================================
# Endpoints
# ===========================================================================


@router.post("", response_model=IngestionItem, status_code=201)
async def upload_document(
    service: IngestionServiceDep,
    user: CurrentUser,
    background: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    source_origin: Annotated[str, Query(alias="sourceOrigin")] = "",
) -> IngestionItem:
    """Sube un archivo a la cola de ingesta. Valida tamaño + formato.

    Tras crear el item, agenda la auto-clasificación en background
    (worker `ingestion_processor`) para que cuando el usuario abra el
    item en la UI ya tenga carpeta/tipo sugeridos.
    """
    data = await file.read()
    item = await service.upload(
        filename=file.filename or "documento",
        data=data,
        uploaded_by_oid=user.oid,
        source_origin=source_origin,
    )
    background.add_task(process_ingestion_background, service, item.id)
    return item


@router.post("/{item_id}/classify", response_model=IngestionItem)
async def classify_document(
    item_id: str,
    service: IngestionServiceDep,
    user: CurrentUser,  # noqa: ARG001 — auth gate
) -> IngestionItem:
    """Extrae el texto, lo anonimiza y clasifica (carpeta + tipo)."""
    return await service.classify(item_id)


@router.post("/{item_id}/approve", response_model=IngestionItem)
async def approve_document(
    item_id: str,
    body: ApproveBody,
    service: IngestionServiceDep,
    user: CurrentUser,
) -> IngestionItem:
    """Aprueba el item: crea el Document final + dispara indexación."""
    traceability = TraceabilityInput(
        approved_by=body.approved_by,
        approval_date=body.approval_date,
        source_origin=body.source_origin,
        version=body.version,
        category=body.category,
        document_type=body.document_type,
    )
    return await service.approve(
        item_id,
        traceability=traceability,
        approver_oid=user.oid,
        approver_name=user.name,
    )


@router.post("/{item_id}/reject", response_model=IngestionItem)
async def reject_document(
    item_id: str,
    body: RejectBody,
    service: IngestionServiceDep,
    user: CurrentUser,  # noqa: ARG001 — auth gate
) -> IngestionItem:
    """Rechaza el item con un motivo (decisión del revisor)."""
    return await service.reject(item_id, reason=body.reason)


@router.get("", response_model=list[IngestionItem])
async def list_ingestion(
    service: IngestionServiceDep,
    user: CurrentUser,  # noqa: ARG001 — auth gate
    status: Annotated[list[IngestionStatus] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[IngestionItem]:
    """Lista items de ingesta, filtrable por uno o más `status`."""
    return await service.list_items(statuses=status, limit=limit, offset=offset)
