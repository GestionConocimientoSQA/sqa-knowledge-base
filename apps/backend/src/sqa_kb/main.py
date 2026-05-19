"""FastAPI app entry point (Fase 5 — esqueleto)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqa_kb.api.health import router as health_router
from sqa_kb.config import get_settings


def create_app() -> FastAPI:
    """Application factory — facilita testing y entornos."""
    settings = get_settings()
    app = FastAPI(
        title="SQA Knowledge Base API",
        version="0.1.0",
        description="API del agente Aria — gestión del conocimiento SQA.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)

    @app.get("/", tags=["root"])
    async def root() -> dict[str, str]:
        return {
            "service": "sqa-knowledge-base",
            "version": "0.1.0",
            "docs": "/docs",
        }

    return app


app = create_app()
