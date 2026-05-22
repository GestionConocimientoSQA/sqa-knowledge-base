"""Middleware de propagación de `X-Request-ID`.

Reglas:
- Si el request entra con header `X-Request-ID`, lo respetamos (el frontend
  o un Front Door upstream pueden generarlo).
- Si no, generamos un UUID4.
- En ambos casos, el id queda disponible en:
    - `request.state.request_id` para handlers
    - el `ContextVar` del logging — todos los logs lo incluyen
    - el header `X-Request-ID` de la response

Esto permite correlacionar logs/traces de una misma request a lo largo
de todo el stack (frontend → backend → logs centralizados).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from sqa_kb.observability.logging import set_request_id

HEADER_NAME = "X-Request-ID"
_MAX_LENGTH = 128
"""Limit defensivo — un request_id válido es UUID (36 chars) o opaco corto."""


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Asigna o propaga `X-Request-ID` por request."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get(HEADER_NAME, "").strip()
        request_id = (
            incoming
            if incoming and len(incoming) <= _MAX_LENGTH
            else str(uuid.uuid4())
        )

        # Disponible para handlers via `request.state.request_id`
        request.state.request_id = request_id
        set_request_id(request_id)

        try:
            response = await call_next(request)
        finally:
            # Limpiar el context var al salir — evita leak entre requests
            # cuando workers reusan tasks.
            set_request_id(None)

        response.headers[HEADER_NAME] = request_id
        return response
