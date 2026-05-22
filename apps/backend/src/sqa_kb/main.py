"""FastAPI application factory.

Compone los componentes core en el orden esperado:
1. Logging — configurado antes que cualquier otra cosa logue.
2. App + middlewares — CORS y request-id en cada request.
3. Error handlers — DomainError → HTTP.
4. Routers — health (Fase 0/1A) + endpoints de dominio (Fase 1B).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqa_kb.api.health import router as health_router
from sqa_kb.config import get_settings
from sqa_kb.middleware.error_handler import register_error_handlers
from sqa_kb.middleware.request_id import RequestIdMiddleware
from sqa_kb.observability.logging import configure_logging, get_logger


def create_app() -> FastAPI:
    """Application factory — facilita testing y entornos."""
    settings = get_settings()

    # Configurar logging ANTES de instanciar FastAPI para que el startup
    # también quede capturado en el formato definido (JSON o consola).
    configure_logging(settings)
    logger = get_logger(__name__)

    app = FastAPI(
        title="SQA Knowledge Base API",
        version="0.1.0",
        description="API del agente Aria — gestión del conocimiento SQA.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Middlewares — el orden importa: RequestId va PRIMERO para que CORS y
    # downstream tengan acceso al request_id en sus logs.
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # Exponer el request-id al frontend para que aparezca en sus logs
        # de error y permita correlación cross-stack.
        expose_headers=["X-Request-ID"],
    )

    register_error_handlers(app)

    app.include_router(health_router)

    @app.get("/", tags=["root"])
    async def root() -> dict[str, str]:
        return {
            "service": "sqa-knowledge-base",
            "version": "0.1.0",
            "docs": "/docs",
        }

    logger.info("app_started", env=str(settings.app_env), name=settings.app_name)
    return app


app = create_app()
