"""Configuración de structlog.

Diseño:
- En producción y staging: salida JSON apta para App Insights y cualquier
  agregador. Cada log incluye automáticamente `request_id`, `app_env`,
  `service`, `timestamp` ISO 8601 UTC.
- En dev local: salida coloreada y legible si `SQA_KB_LOG_JSON=false`,
  para iteración rápida en consola.

El `request_id` viene de un `contextvars.ContextVar` que el middleware
RequestIdMiddleware setea al inicio de cada request. Esto evita pasarlo
explícitamente por cada llamada — todo log dentro del lifecycle de una
request lo arrastra.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog

from sqa_kb.config import Settings

# Context var del request — vacío fuera del lifecycle de una request HTTP.
_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Lee el `request_id` del contexto actual. None si no estamos dentro
    de una request HTTP."""
    return _request_id_ctx.get()


def set_request_id(value: str | None) -> None:
    """Setea el `request_id` del contexto. El middleware lo llama en cada
    request. Los tests pueden setearlo manualmente."""
    _request_id_ctx.set(value)


def _request_id_processor(
    _logger: object, _method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Inyecta `request_id` del context var en cada log line."""
    rid = _request_id_ctx.get()
    if rid is not None:
        event_dict["request_id"] = rid
    return event_dict


def configure_logging(settings: Settings) -> None:
    """Configura structlog. Llamar UNA vez al startup desde `main.py`.

    Si se llama múltiples veces (ej: tests), reconfigura — structlog es
    idempotente en ese sentido.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Procesadores comunes a JSON y consola.
    common_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _request_id_processor,
        # Campos fijos que aparecen en todos los logs — útiles para filtrar
        # por servicio + entorno en el agregador.
        _add_service_metadata(settings),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_json:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*common_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Silenciar loggers ruidosos de libs externas.
    for noisy in ("uvicorn.access", "azure.core.pipeline.policies.http_logging_policy"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _add_service_metadata(
    settings: Settings,
) -> structlog.types.Processor:
    """Closure que agrega campos fijos del servicio. Inyecta `app_env` y `service`."""

    def processor(
        _logger: object, _method: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        event_dict.setdefault("service", settings.app_name)
        event_dict.setdefault("app_env", str(settings.app_env))
        return event_dict

    return processor


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Punto único para obtener un logger. Equivalente a `structlog.get_logger`
    pero centraliza por si más adelante queremos agregar context fijo."""
    return structlog.get_logger(name)
