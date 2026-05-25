"""FastAPI application factory.

Compone los componentes core en el orden esperado:
1. Logging — configurado antes que cualquier otra cosa logue.
2. App + middlewares — CORS y request-id en cada request.
3. Error handlers — DomainError → HTTP.
4. Wiring de adapters concretos (DB + auth) según `app_env`.
5. Routers — health (Fase 0/1A) + endpoints de dominio (Fase 1B).
"""

from __future__ import annotations

import asyncio
import sys

# Windows: psycopg async (Fase 2.1) requiere SelectorEventLoop, no el
# ProactorEventLoop default de asyncio en Python 3.8+. Tiene que setearse
# antes de que uvicorn cree el loop, por eso va al tope del módulo.
# En Linux/Azure (target prod) es no-op.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqa_kb.adapters.auth.dev import DevTokenValidator
from sqa_kb.adapters.checkpointer import CheckpointerBundle, build_checkpointer
from sqa_kb.adapters.embeddings.cohere import CohereEmbedder
from sqa_kb.adapters.llm import AnthropicDirectGateway
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
from sqa_kb.agent.graph import build_graph
from sqa_kb.api.auth import router as auth_router
from sqa_kb.api.dashboard import router as dashboard_router
from sqa_kb.api.documents import router as documents_router
from sqa_kb.api.health import register_health_check
from sqa_kb.api.health import router as health_router
from sqa_kb.api.messages import router as messages_router
from sqa_kb.api.queries import router as queries_router
from sqa_kb.api.sessions import router as sessions_router
from sqa_kb.api.sse import SseEventBuffer
from sqa_kb.api.taxonomy import router as taxonomy_router
from sqa_kb.adapters.repositories.postgres.chunks import PostgresChunkRepository
from sqa_kb.config import LlmGatewayKind, Settings, get_settings
from sqa_kb.middleware.error_handler import register_error_handlers
from sqa_kb.middleware.request_id import RequestIdMiddleware
from sqa_kb.observability.logging import configure_logging, get_logger
from sqa_kb.rag.hybrid_search import HybridSearcher
from sqa_kb.rag.indexer import Indexer


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


def _wire_search(app: FastAPI, settings: Settings) -> None:
    """Inicializa embedder + HybridSearcher + Indexer (Fase 3.5/3.6).

    Requiere `session_factory` (de `_wire_persistence`) + `cohere_api_key`.
    Si falta la key, saltea el wiring; el endpoint `/queries` y los nodos
    del agente que dependan del searcher devolverán 500 con mensaje claro
    vía `_from_state`. Los tests unitarios inyectan fakes y no necesitan
    este wiring.

    El `Indexer` (Fase 3.6) comparte el embedder con el searcher para
    no duplicar conexión a Cohere. `build_graph` lo recibe y se lo pasa
    a los nodos `generation` (modo A) y `index_ingestion` (modo C) que
    indexan al cierre de cada flujo.
    """
    if getattr(app.state, "session_factory", None) is None:
        return
    if settings.cohere_api_key is None:
        return

    embedder = CohereEmbedder(
        api_key=settings.cohere_api_key.get_secret_value(),
        model=settings.cohere_embed_model,
    )
    searcher = HybridSearcher(
        embedder=embedder,
        session_factory=app.state.session_factory,
    )
    chunk_repo = PostgresChunkRepository(app.state.session_factory)
    indexer = Indexer(
        embedder=embedder,
        chunk_repo=chunk_repo,
        document_repo=app.state.document_repo,
    )
    app.state.embedder = embedder
    app.state.kb_searcher = searcher
    app.state.chunk_repo = chunk_repo
    app.state.indexer = indexer


async def _wire_agent(app: FastAPI, settings: Settings) -> CheckpointerBundle | None:
    """Inicializa el grafo del agente (Fase 2) + buffer SSE.

    Requiere DB + LLM gateway config + searcher (Fase 3.5). Si falta
    cualquier prerrequisito, el wiring se saltea y los endpoints
    `/sessions/{id}/messages` van a devolver 500 con mensaje claro
    (vía `_from_state`).
    """
    if settings.database_url is None:
        return None

    # SSE buffer siempre lo creamos (sirve para tests aunque no haya grafo).
    app.state.sse_buffer = SseEventBuffer()

    if settings.llm_gateway_kind != LlmGatewayKind.ANTHROPIC_DIRECT:
        # Fase 1B-azure cableará LiteLLM; por ahora solo soportamos directo.
        return None
    if settings.anthropic_api_key is None:
        return None
    if getattr(app.state, "kb_searcher", None) is None:
        # Sin searcher (cohere_api_key ausente), los nodos identification
        # + consultation no pueden funcionar. No cableamos el grafo —
        # mejor 500 explícito que un grafo a medias.
        return None

    # Checkpointer Postgres del paquete oficial (Fase 2.1).
    bundle = await build_checkpointer(
        dsn=settings.database_url.get_secret_value()
    )

    gateway = AnthropicDirectGateway(
        api_key=settings.anthropic_api_key.get_secret_value(),
        default_model=settings.llm_default_model,
    )

    graph = build_graph(
        gateway=gateway,
        document_repo=app.state.document_repo,
        searcher=app.state.kb_searcher,
        ingestion_repo=app.state.ingestion_repo,
        indexer=app.state.indexer,
        checkpointer=bundle.saver,
    )

    app.state.llm_gateway = gateway
    app.state.agent_graph = graph
    app.state.checkpointer_bundle = bundle
    return bundle


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan que cablea search + agente y libera recursos al apagar."""
    settings = get_settings()
    # Search debe armarse ANTES del agente — el grafo lo necesita.
    _wire_search(app, settings)
    bundle = await _wire_agent(app, settings)
    try:
        yield
    finally:
        if bundle is not None:
            await bundle.aclose()


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
        lifespan=_lifespan,
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
    app.include_router(taxonomy_router)
    app.include_router(documents_router)
    app.include_router(sessions_router)
    app.include_router(messages_router)
    app.include_router(dashboard_router)
    app.include_router(queries_router)

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
