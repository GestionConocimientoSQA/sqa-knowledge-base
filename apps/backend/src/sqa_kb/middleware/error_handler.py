"""Handlers globales que mapean `DomainError` → respuestas HTTP.

La capa de transporte (FastAPI) traduce las excepciones del dominio a
códigos HTTP. Los handlers de domain/services lanzan errores tipados
sin saber qué framework los va a recibir — eso mantiene el domain
agnóstico (y testeable sin levantar FastAPI).

Convención de payload de error:

    {
        "error": {
            "code": "NotFoundError",   // nombre de la clase Python
            "message": "...",
            "request_id": "..."         // del X-Request-ID
        }
    }

Esta forma es estable entre versiones; el frontend la consume tal cual.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sqa_kb.domain.errors import (
    ConflictError,
    DomainError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
    ValidationError as DomainValidationError,
)
from sqa_kb.observability.logging import get_logger

logger = get_logger(__name__)


_STATUS_BY_ERROR_TYPE: tuple[tuple[type[DomainError], int], ...] = (
    (NotFoundError, 404),
    (UnauthorizedError, 401),
    (ForbiddenError, 403),
    (DomainValidationError, 422),
    (ConflictError, 409),
    (RateLimitedError, 429),
    (ExternalServiceError, 503),
)
"""Orden: específicos antes que genéricos. La búsqueda devuelve el primer match."""


def _http_status_for(err: DomainError) -> int:
    for err_type, status in _STATUS_BY_ERROR_TYPE:
        if isinstance(err, err_type):
            return status
    return 500  # DomainError sin subtype específico


def _build_payload(err: DomainError, request_id: str | None) -> dict[str, object]:
    payload: dict[str, object] = {
        "code": err.code,
        "message": err.message,
    }
    if request_id is not None:
        payload["request_id"] = request_id
    if isinstance(err, RateLimitedError) and err.retry_after_seconds is not None:
        payload["retry_after_seconds"] = err.retry_after_seconds
    if isinstance(err, ExternalServiceError):
        payload["service"] = err.service
    return {"error": payload}


def register_error_handlers(app: FastAPI) -> None:
    """Registra los handlers globales. Llamar UNA vez desde la factory."""

    @app.exception_handler(DomainError)
    async def _domain_error_handler(
        request: Request, exc: DomainError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        status_code = _http_status_for(exc)

        log_method = logger.warning if status_code < 500 else logger.error
        log_method(
            "domain_error",
            code=exc.code,
            status=status_code,
            path=request.url.path,
            method=request.method,
            exc_info=status_code >= 500,
        )

        headers: dict[str, str] = {}
        if isinstance(exc, RateLimitedError) and exc.retry_after_seconds is not None:
            headers["Retry-After"] = str(exc.retry_after_seconds)

        return JSONResponse(
            status_code=status_code,
            content=_build_payload(exc, request_id),
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.error(
            "unhandled_exception",
            exc_type=type(exc).__name__,
            path=request.url.path,
            method=request.method,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "InternalServerError",
                    "message": "Internal server error",
                    "request_id": request_id,
                }
            },
        )
