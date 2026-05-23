"""Dependencias FastAPI compartidas.

Cada función de este módulo es importable desde los routers con `Depends()`.
Las dependencias leen los adapters desde `app.state` que se llenó al startup
(ver `main.py`). Esto centraliza el wiring y mantiene los routers libres
de detalles de construcción.

Excepción: hay overrides simples para los tests via `app.dependency_overrides`
del propio FastAPI.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqa_kb.domain.entities import User
from sqa_kb.domain.errors import UnauthorizedError
from sqa_kb.ports.gateways import TokenValidator
from sqa_kb.ports.repositories import (
    ActivityRepository,
    AuditLogRepository,
    DocumentRepository,
    IngestionRepository,
    QueryRepository,
    SessionRepository,
    SkillRepository,
    TaxonomyRepository,
    UserRepository,
)

security = HTTPBearer(auto_error=False)


# ===========================================================================
# Acceso a adapters desde app.state
# ===========================================================================


def _from_state(name: str):  # type: ignore[no-untyped-def]
    """Factory que devuelve una dependency leyendo `request.app.state.{name}`."""

    def _dep(request: Request):  # type: ignore[no-untyped-def]
        value = getattr(request.app.state, name, None)
        if value is None:
            raise RuntimeError(
                f"app.state.{name} no fue inicializado al startup. "
                "Revisar create_app() en main.py."
            )
        return value

    _dep.__name__ = f"get_{name}"
    return _dep


get_user_repo = _from_state("user_repo")
get_session_repo = _from_state("session_repo")
get_document_repo = _from_state("document_repo")
get_ingestion_repo = _from_state("ingestion_repo")
get_query_repo = _from_state("query_repo")
get_taxonomy_repo = _from_state("taxonomy_repo")
get_skill_repo = _from_state("skill_repo")
get_audit_repo = _from_state("audit_repo")
get_activity_repo = _from_state("activity_repo")
get_token_validator = _from_state("token_validator")


# ===========================================================================
# Auth — current_user
# ===========================================================================


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security)
    ],
    validator: Annotated[TokenValidator, Depends(get_token_validator)],
) -> User:
    """Extrae el bearer, lo valida y devuelve el `User` resuelto.

    Lanza `UnauthorizedError` (mapeada a 401 por el handler global) si
    falta el header o el token no es válido.
    """
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Falta header `Authorization: Bearer <token>`")
    claims = await validator.validate(credentials.credentials)
    return await validator.resolve_user(claims)


CurrentUser = Annotated[User, Depends(get_current_user)]
"""Type alias usable en signatures de endpoints:

    @router.get("/me")
    async def me(user: CurrentUser) -> User:
        return user
"""


# Type aliases convenientes para signatures más cortas en routers.
UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
SessionRepoDep = Annotated[SessionRepository, Depends(get_session_repo)]
DocumentRepoDep = Annotated[DocumentRepository, Depends(get_document_repo)]
IngestionRepoDep = Annotated[IngestionRepository, Depends(get_ingestion_repo)]
QueryRepoDep = Annotated[QueryRepository, Depends(get_query_repo)]
TaxonomyRepoDep = Annotated[TaxonomyRepository, Depends(get_taxonomy_repo)]
SkillRepoDep = Annotated[SkillRepository, Depends(get_skill_repo)]
AuditRepoDep = Annotated[AuditLogRepository, Depends(get_audit_repo)]
ActivityRepoDep = Annotated[ActivityRepository, Depends(get_activity_repo)]
