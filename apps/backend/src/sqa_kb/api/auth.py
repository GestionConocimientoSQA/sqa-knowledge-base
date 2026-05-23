"""Endpoints relacionados con autenticación.

Por ahora solo expone `GET /auth/me` — el frontend lo consume al cargar
para hidratar el `useAuth` con datos del backend (permisos finos según
la matriz `[[project-roles-capacidades]]`, no solo el `is_admin` que el
stub MSAL maneja hoy).
"""

from __future__ import annotations

from fastapi import APIRouter

from sqa_kb.api.dependencies import CurrentUser
from sqa_kb.domain.entities import User

router = APIRouter(tags=["auth"], prefix="/auth")


@router.get(
    "/me",
    response_model=User,
    summary="Perfil del usuario autenticado",
    responses={401: {"description": "Bearer ausente o inválido"}},
)
async def me(user: CurrentUser) -> User:
    """Devuelve el `User` completo con permisos finos.

    El frontend usa esta respuesta para configurar UI según el rol
    (gating de "Marcar autoritativo", visibilidad de KPIs globales, etc.).
    """
    return user
