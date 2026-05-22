"""Errores del dominio.

Jerarquía simple — `DomainError` es la raíz, las subclases son lanzables y
testeables por tipo. La capa `api/` los mapea a respuestas HTTP via el
error handler global (Fase 1A.4).

Regla: los servicios y entidades NUNCA lanzan `HTTPException` ni
errores específicos de FastAPI. Lanzan `DomainError` (o subclases) y
la capa de transporte hace el mapping. Esto mantiene el domain limpio
y permite cambiar de framework sin tocar la lógica.
"""

from __future__ import annotations


class DomainError(Exception):
    """Raíz de los errores del dominio. Stack de stack-traces preservado."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__


class NotFoundError(DomainError):
    """La entidad solicitada no existe (o el caller no tiene visibilidad).

    Por seguridad (IDOR — ver [[project-security-idor-check]]) los
    repositorios devuelven `NotFoundError` también cuando el recurso
    existe pero pertenece a otro usuario. No queremos diferenciar
    "no existe" vs "no podés verlo" en respuestas HTTP.
    """


class UnauthorizedError(DomainError):
    """Sin sesión válida o token expirado."""


class ForbiddenError(DomainError):
    """Hay sesión válida pero el caller no tiene permisos para esta acción.

    Ejemplo: un Capturador intenta `PATCH /documents/{id}/authoritative` —
    la operación está reservada a `isAdmin` (Owner sobre sus carpetas o
    GK Lead sobre cualquiera) según [[project-roles-capacidades]].
    """


class ValidationError(DomainError):
    """Datos del cliente no cumplen reglas del dominio.

    Distinto de la validación de Pydantic (que ya devuelve 422). Esto se
    lanza cuando una regla de negocio falla, ej: "no se puede pausar una
    sesión completada", "el documento ya está marcado como autoritativo".
    """


class ConflictError(DomainError):
    """Operación entra en conflicto con el estado actual del recurso.

    Mapea a 409. Ejemplos: doble click en aprobar ingesta, intento de
    crear un slug que ya existe, edición concurrente.
    """


class RateLimitedError(DomainError):
    """El caller superó la cuota."""

    def __init__(self, message: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class ExternalServiceError(DomainError):
    """Una dependencia externa falló (DB, blob, LLM gateway, etc.).

    Mapea a 503. Carry-along del nombre del servicio para logging.
    """

    def __init__(self, message: str, *, service: str) -> None:
        super().__init__(message)
        self.service = service
