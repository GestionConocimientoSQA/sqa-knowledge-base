"""Endpoints de sesiones de documentación con el agente (Fase 9.5).

    POST   /projects/{id}/documentation-sessions          Inicia sesión
    GET    /projects/{id}/documentation-sessions          Lista del proyecto
    GET    /documentation-sessions/{sid}                  Detalle/estado
    POST   /documentation-sessions/{sid}/steps/{step}     Envía respuesta de step
    POST   /documentation-sessions/{sid}/finalize         Genera docs + ingesta
    POST   /documentation-sessions/{sid}/abandon          Cancela

Thin wrapper sobre `DocumentationSessionService`. La autorización vive en
el servicio (PermissionPolicy).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from sqa_kb.api.dependencies import (
    CurrentUser,
    DocumentationSessionServiceDep,
)
from sqa_kb.domain.entities import DocumentationSession
from sqa_kb.domain.value_objects import DocumentationStep


# Dos routers — uno con prefijo `/projects/{project_id}` (start + list) y
# otro con `/documentation-sessions/{session_id}` (operaciones sobre una
# sesión existente). Ambos quedan colgados de `app.include_router` en main.
project_router = APIRouter(tags=["documentation-sessions"])
session_router = APIRouter(
    tags=["documentation-sessions"],
    prefix="/documentation-sessions",
)


# ===========================================================================
# Schemas
# ===========================================================================


class _CamelBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class StepPayloadBody(_CamelBase):
    """Payload genérico por step — el servicio valida la forma por step."""

    payload: dict[str, Any] = Field(default_factory=dict)


# ===========================================================================
# Endpoints — bajo /projects/{project_id}
# ===========================================================================


@project_router.post(
    "/projects/{project_id}/documentation-sessions",
    response_model=DocumentationSession,
    status_code=201,
)
async def start_session(
    project_id: str,
    service: DocumentationSessionServiceDep,
    user: CurrentUser,
) -> DocumentationSession:
    """Abre una sesión de documentación nueva (step actual = `context`)."""
    return await service.start(user, project_id)


@project_router.get(
    "/projects/{project_id}/documentation-sessions",
    response_model=list[DocumentationSession],
)
async def list_sessions(
    project_id: str,
    service: DocumentationSessionServiceDep,
    user: CurrentUser,
) -> Sequence[DocumentationSession]:
    return await service.list_for_project(user, project_id)


# ===========================================================================
# Endpoints — bajo /documentation-sessions/{session_id}
# ===========================================================================


@session_router.get("/{session_id}", response_model=DocumentationSession)
async def get_session(
    session_id: str,
    service: DocumentationSessionServiceDep,
    user: CurrentUser,
) -> DocumentationSession:
    return await service.get(user, session_id)


@session_router.post(
    "/{session_id}/steps/{step}", response_model=DocumentationSession
)
async def submit_step(
    session_id: str,
    step: DocumentationStep,
    body: StepPayloadBody,
    service: DocumentationSessionServiceDep,
    user: CurrentUser,
) -> DocumentationSession:
    """Envía el payload del step actual. Avanza al siguiente."""
    return await service.submit_step(user, session_id, step, body.payload)


@session_router.post(
    "/{session_id}/finalize", response_model=DocumentationSession
)
async def finalize_session(
    session_id: str,
    service: DocumentationSessionServiceDep,
    user: CurrentUser,
) -> DocumentationSession:
    """Genera N docs `.md` (uno por step) y los envía a la cola de ingesta
    del proyecto. Marca la sesión `finalized`."""
    return await service.finalize(user, session_id)


@session_router.post(
    "/{session_id}/abandon", response_model=DocumentationSession
)
async def abandon_session(
    session_id: str,
    service: DocumentationSessionServiceDep,
    user: CurrentUser,
) -> DocumentationSession:
    return await service.abandon(user, session_id)
