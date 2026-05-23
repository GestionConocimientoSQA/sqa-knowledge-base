"""FastAPI application factory.

Compone los componentes core en el orden esperado:
1. Logging — configurado antes que cualquier otra cosa logue.
2. App + middlewares — CORS y request-id en cada request.
3. Error handlers — DomainError → HTTP.
4. Wiring de adapters concretos (DB + auth) según `app_env`.
5. Routers — health (Fase 0/1A) + endpoints de dominio (Fase 1B).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqa_kb.adapters.auth.dev import DevTokenValidator
from sqa_kb.adapters.repositories.postgres import (
    create_engine,
    create_session_factory,
)
from sqa_kb.adapters.repositories.postgres.activity import (
    PostgresActivityRepository,
)
from sqa_kb.adapters.repositories.postgres.audit_log import (
    PostgresAuditLogRepository,
)
from sqa_kb.adapters.repositories.postgres.documents import (
    PostgresDocumentRepository,
)
from sqa_kb.adapters.repositories.postgres.ingestion import (
    PostgresIngestionRepository,
)
from sqa_kb.adapters.repositories.postgres.queries import (
    PostgresQueryRepository,
)
from sqa_kb.adapters.repositories.postgres.session import PostgresHealthCheck
from sqa_kb.adapters.repositories.postgres.sessions import (
    PostgresSessionRepository,
)
from sqa_kb.adapters.repositories.postgres.skills import PostgresSkillRepository
from sqa_kb.adapters.repositories.postgres.taxonomy import (
    PostgresTaxonomyRepository,
)
from sqa_kb.adapters.repositories.postgres.users import PostgresUserRepository
from sqa_kb.api.auth import router as auth_router
from sqa_kb.api.health import register_health_check, router as health_router
from sqa_kb.config import Settings, get_settings
from sqa_kb.middleware.error_handler import register_error_handlers
from sqa_kb.middleware.request_id import RequestIdMiddleware
from sqa_kb.observability.logging import configure_logging, get_logger


def _wire_persistence(app: FastAPI, settings: Settings) -> None:
    """Inicializa engine + repos + auth y los guarda en `app.state`.

    Se ejecuta solo si `database_url` está seteada. En tests unitarios que
    no necesitan DB la URL queda en None y este wiring se saltea — los
    routers que requieren DB tendrán 500 si se llaman, lo cual es correcto.
    """
    if settings.database_url is None:
        return

    engine = create_engine(settings)
    factory = create_session_factory(engine)

    user_repo = PostgresUserRepository(factory)

    app.state.engine = engine
    app.state.session_factory = factory
    app.state.user_repo = user_repo
    app.state.session_repo = PostgresSessionRepository(factory)
    app.state.document_repo = PostgresDocumentRepository(factory)
    app.state.ingestion_repo = PostgresIngestionRepository(factory)
    app.state.query_repo = PostgresQueryRepository(factory)
    app.state.taxonomy_repo = PostgresTaxonomyRepository(factory)
    app.state.skill_repo = PostgresSkillRepository(factory)
    app.state.audit_repo = PostgresAuditLogRepository(factory)
    app.state.activity_repo = PostgresActivityRepository(factory)
    app.state.token_validator = DevTokenValidator(
        user_repo, app_env=settings.app_env
    )

    # Health check de DB visible desde /health/ready.
    register_health_check(PostgresHealthCheck(engine))


def create_app() -> FastAPI:
    """Application factory — facilita testing y entornos."""
    settings = get_settings()

    # Configurar logging ANTES de instanciar FastAPI.
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
        # Exponer el request-id al frontend para correlación cross-stack.
        expose_headers=["X-Request-ID"],
    )

    register_error_handlers(app)

    # Wiring de adapters (solo si hay DATABASE_URL).
    _wire_persistence(app, settings)

    app.include_router(health_router)
    app.include_router(auth_router)

    @app.get("/", tags=["root"])
    async def root() -> dict[str, str]:
        return {
            "service": "sqa-knowledge-base",
            "version": "0.1.0",
            "docs": "/docs",
        }

    logger.info(
        "app_started",
        env=str(settings.app_env),
        name=settings.app_name,
        db_wired=settings.database_url is not None,
    )
    return app


app = create_app()
