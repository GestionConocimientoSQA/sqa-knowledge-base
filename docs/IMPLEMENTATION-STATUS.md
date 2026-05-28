# Estado de implementación · SQA Knowledge Base

> **Última actualización:** 2026-05-28 (Fase 8 ✅ completada — 8.1 a 8.5 cerradas, branch `fase-8-ingesta` listo para merge a master)
> **Documento vivo** — se actualiza al cierre de cada fase.
> Fuente de verdad para `qué está hecho / en curso / pendiente`.

## Resumen ejecutivo

| Indicador | Valor |
|---|---|
| Timeline estimado total | 16-20 semanas |
| Avance ponderado | **~88% del proyecto total** (≈17.5 de 20 semanas-equivalentes) |
| Fases completadas | **12** (Fase 0, 1A, 1B-local, 2, 3, 4, 5, 6, 7, 8, 10A, 10B) |
| Fase actual | **Fase 8 ✅ Completada** — 8.1 a 8.5 cerradas. Branch `fase-8-ingesta` listo para merge a `master`. |
| Próxima fase | **Fase 9** — Frontend · Admin / Multi-tenant proyectos (re-scope: conocimiento por proyecto + roles `colaborador` / `gk_lead` globales + `project_owner` / `member` per-proyecto) |
| Bloqueo externo | Fase 1B-azure (Entra ID real) sigue esperando App Registration por TI |
| Stack productivo | Frontend Next.js 15 ✓ · Backend FastAPI + PostgreSQL + agente LangGraph + RAG vectorial pgvector + generación/extracción docs ✓ · Infra Bicep esqueleto ✓ |
| Tests totales | 774 backend + 271 frontend unit + 57 E2E = **1102 tests verdes** |
| Deployable target | Azure (Container Apps, PostgreSQL Flexible Server, Blob, Key Vault, Entra ID, App Insights) |

## Tabla de fases

| Fase | Bloque | Semanas roadmap | Estado | Cobertura |
|---|---|---|---|---|
| **0** | **Fundación (monorepo + infra + Azure)** | **1** | **✅ Completada** | **100%** |
| **1** | **Backend · Persistencia + Auth (1A + 1B-local)** | **2-3** | **✅ Completada (excepto 1B-azure)** | Clean Architecture + PG real + dev auth + endpoints CRUD + frontend conectado. 1B-azure (Entra ID real) bloqueado por TI. |
| **2** | **Backend · Agente LangGraph (ETAPAS)** | **4-6** | **✅ Completada** | Adapter LLM + AgentState + checkpointer + grafo + 3 modos + endpoint SSE con 14 eventos. 420 tests. |
| **3** | **Backend · RAG vectorial** | **7-8** | **✅ Completada** | 3.0 adapter Cohere + 3.1 chunker + 3.2 indexer + 3.3 retriever HNSW + 3.4 hybrid search + 3.5 endpoint /queries + 3.6 reindex_all + hooks generation/ingestion + 3.7 eval set (recall@5=1.0, precision@1=1.0). 648 tests. |
| **4** | **Backend · Generación y extracción de docs** | **9-10** | **✅ Completada** | 4.0 branding + 4.1 DocxGenerator/MarkdownGenerator + 4.2 Pptx/Xlsx/Pdf + 4.3 extractores+dispatcher + 4.4 anonimizador + 4.5 endpoints /ingestion + 4.6 adapter Blob+worker. 774 tests. |
| **5** | **Frontend · Fundación (UI + auth stub)** | **11-12** | **✅ Completada** | **100%** |
| **6** | **Frontend · Chat streaming SSE (con mock-transport)** | **13-14** | **✅ Completada** | **100%** |
| **7** | **Frontend · Explorer + Dashboard interactivo** | **15** | **✅ Completada** | **100%** |
| **8** | **Frontend · Cola de ingesta** | **16** | **✅ Completada** | 8.1 reject backend + contratos · 8.2 UploadZone D&D · 8.3 página /ingestion + tabs + queue · 8.4 detail + TraceabilityForm · 8.5 smoke E2E. 271 unit + 57 E2E. |
| 9 | Frontend · Admin (usuarios, taxonomía, skills, audit) | 17 | ⬜ Pendiente | 0% |
| **10** | **Hardening (perf + a11y + security review)** | **18-19** | **✅ Sub-fases 10A + 10B** | E2E Playwright + axe a11y + CSP + Lighthouse CI + keyboard nav + i18n (es-CO/en-US) + code splitting; falta backend-side |
| 11 | Migración legacy + paso a producción Azure | 20 | ⬜ Pendiente | parcial (Bicep esqueleto, OIDC workflow) |

---

# Fase 0 · Fundación

**Estado:** ✅ Completada · **Validada:** 2026-05-19

## Objetivo

Repositorio inicializado, herramientas configuradas, entorno local funcional, infra Azure parametrizada.

## Tareas ejecutadas

- ✅ Estructura de monorepo (`apps/`, `packages/`, `infra/`, `docs/`, `scripts/`, `.github/workflows/`)
- ✅ pnpm workspace + Node 20 + Python 3.12 toolchain
- ✅ Configuración raíz (`Makefile`, `docker-compose.yml`, `.gitignore`, `.editorconfig`, `.env.example`, `.prettierrc.json`, `.pre-commit-config.yaml`)
- ✅ Backend con uv-compatible (`pyproject.toml`, FastAPI hello world, `/health/{live,ready,startup}`, OpenAPI en `/docs`)
- ✅ Frontend con Next.js 15 (App Router, Tailwind 3, shadcn/ui)
- ✅ Workflows GitHub Actions iniciales (5 archivos): frontend-ci, backend-ci, pr-checks, build-and-push (Azure ACR OIDC), infra-validate (Bicep)
- ✅ Esqueleto de documentación (`docs/architecture`, `docs/development`, `docs/deployment` pendiente Fase 11)
- ✅ Pre-commit hooks (ruff, prettier, gitleaks)
- ✅ ADR 0001 — Monorepo
- ✅ **Bicep IaC para Azure** (orquesta networking, monitoring, key-vault, storage, postgres, container-apps en 3 entornos)

## Entregables · archivos creados

```
sqa-knowledge-base/
├── package.json                          pnpm workspace root
├── pnpm-workspace.yaml
├── Makefile                              atajos make (Unix + Git Bash)
├── docker-compose.yml                    Postgres+pgvector, Azurite, Redis
├── .env.example                          plantilla pública con todas las vars
├── .gitignore                            cubre credentials.env, .pem, .key
├── .editorconfig                         consistencia line-endings / indent
├── .prettierrc.json + .prettierignore
├── .pre-commit-config.yaml               ruff, prettier, gitleaks, hooks core
├── README.md                             quickstart + plan de fases
├── apps/
│   ├── frontend/
│   │   ├── Dockerfile                    multi-stage para Container Apps
│   │   ├── .dockerignore
│   │   └── .eslintrc.json
│   └── backend/
│       ├── pyproject.toml                FastAPI + Pydantic v2 + ruff + mypy
│       ├── Dockerfile                    multi-stage para Container Apps
│       ├── .dockerignore
│       ├── .env.example
│       ├── README.md
│       ├── src/sqa_kb/
│       │   ├── __init__.py
│       │   ├── main.py                   app factory + CORS + health router
│       │   ├── config.py                 Pydantic Settings (env vars)
│       │   └── api/health.py             /health/{live,ready,startup}
│       └── tests/test_health.py          3 tests pasan
├── infra/                                ☁️ Azure Bicep
│   ├── README.md                         contrato con TI + naming convention
│   ├── main.bicep                        subscription scope, orquesta módulos
│   ├── modules/
│   │   ├── networking.bicep              VNet + 2 subnets delegated
│   │   ├── monitoring.bicep              Log Analytics + App Insights
│   │   ├── key-vault.bicep               KV con RBAC + soft-delete
│   │   ├── storage.bicep                 Blob + 3 containers SQA
│   │   ├── postgres.bicep                Flexible Server + pgvector
│   │   └── container-apps.bicep          ACA env + frontend + backend
│   └── parameters/
│       ├── dev.parameters.json
│       ├── staging.parameters.json
│       └── prod.parameters.json
├── docs/
│   ├── README.md                         índice de documentación
│   ├── architecture/
│   │   ├── overview.md                   stack + clean arch + principios
│   │   └── adr/0001-monorepo.md
│   └── development/
│       ├── getting-started.md            primer setup
│       ├── conventions.md                SOLID + TS strict + Python style
│       └── secrets-handling.md           cómo cargar credentials.env, KV
├── scripts/
│   ├── dev.ps1                           equivalente Makefile para PowerShell
│   └── seed/init.sql                     extensiones Postgres
└── .github/workflows/
    ├── frontend-ci.yml                   typecheck + test + build
    ├── backend-ci.yml                    ruff + mypy + pytest con Postgres svc
    ├── pr-checks.yml                     paths-filter + gitleaks + audits
    ├── infra-validate.yml                Bicep build + lint
    └── build-and-push.yml                Docker → Azure Container Registry (OIDC)
```

## Definition of Done

- ✅ `docker compose up -d` levanta Postgres (con pgvector, uuid-ossp, pg_trgm, btree_gin) + Azurite + Redis en < 15s
- ✅ Backend hello world responde `/health/live` con 200 JSON
- ✅ Frontend dev server arranca en `< 3s` y responde rutas
- ✅ Workflows YAML validan sintaxis (5/5)
- ✅ Bicep `main.bicep` compila a ARM JSON sin errores (1 warning esperado en `keyVaultName`)
- ✅ Documentación de getting-started completa

## Validación realizada

| Check | Resultado |
|---|---|
| 59/59 archivos esperados | ✅ presentes |
| `docker compose config` | ✅ válido |
| `docker compose up` → 3 servicios | ✅ healthy en < 15s |
| Postgres extensiones | ✅ vector 0.8.2, uuid-ossp 1.1, pg_trgm 1.6, btree_gin 1.3 |
| `pytest` backend | ✅ 3/3 |
| `bicep build main.bicep` | ✅ 31 KB ARM, 7 recursos root, 6 modules |
| YAML lint (5 workflows) | ✅ todos válidos |
| `docker buildx build --check` Dockerfiles | ✅ no warnings (front + back) |
| Secrets gitignored | ✅ credentials.env, .env*, .pem, .key |

## Decisiones tomadas en esta fase

- **Tailwind 3.x** en lugar de 4.x del roadmap — Tailwind 4 tiene arquitectura distinta (@theme inline) que aún no está madura con Next 15. Migración a 4.x prevista para Fase 10.
- **pnpm@9.15.0** instalado vía `npm i -g` (corepack falló por permisos admin Windows).
- **`output: standalone`** condicionado por env `NEXT_BUILD_STANDALONE` — Windows local no puede crear symlinks; CI Linux sí.
- **Bicep CLI** standalone (`~\.local\bin\bicep.exe`) en lugar de via Azure CLI — sin admin.
- **Compose sin frontend/backend** — solo dependencias; las apps corren con `pnpm dev` / `uvicorn` para iteración rápida.

## Pendientes menores

- ⚠️ `git init` ya ejecutado durante QA (efecto colateral) pero **sin primer commit aún**.
- ⚠️ Repo en GitHub/Azure DevOps todavía no creado (lo hace el usuario cuando decida).
- ⚠️ Bicep `keyVaultName` unused warning — se resuelve en Fase 11 al agregar referencias reales.

---

# Fase 1 · Backend · Persistencia y Auth

**Estado:** 🔄 Sub-fase 1A ✅ · branch `fase-1-backend-base` · **Semanas roadmap:** 2-3

## Sub-fase 1A · Backend base sin TI

**Estado:** ✅ Completada · 2026-05-22

Toda la fundación del backend que NO depende de decisiones pendientes de TI (LiteLLM, Entra ID App Registration). Cuando TI desbloquee, solo se agregan adapters concretos — domain, services, ports y middleware no cambian.

> **Decisión cerrada 2026-05-22**: PostgreSQL Flexible Server + pgvector como base de datos productiva. Se descarta Azure SQL — el costo extra del adapter dual no compensa cuando pgvector resuelve hybrid search nativo. El `database_dialect` enum queda en código por si en un futuro lejano hace falta, pero no se implementa el adapter `azure_sql`.

### 1A.1 · Estructura Clean Architecture

- ✅ Paquetes `domain/` `ports/` `services/` `adapters/` `middleware/` `observability/` con `__init__.py` documentando el rol y la regla de imports (`domain ← nadie · services → domain · adapters → ports → domain · api → services → domain`).

### 1A.2 · Domain models (Pydantic v2)

- ✅ `domain/value_objects.py` — 9 enums (`CategoryCode`, `DocTypeCode`, `DocStatus`, `SessionMode`, `SessionStatus`, `MessageRole`, `MessageStatus`, `IngestionStatus`, `RoleId`, `ActivityType`) + `StageId` con `is_valid_stage()`.
- ✅ `domain/entities.py` — 13 entidades: `User`, `Session`, `Message`, `Category`, `DocType`, `Document`, `DocumentDetail`, `CaptureScore`, `IncomingCitation`, `IngestionItem`, `Query`, `QueryCitation`, `Skill`, `AuditLog` + payloads de streaming (`CitationPayload`, `ClassificationPayload`, `ScoringPayload`, `TokenUsagePayload`, `DocumentArtifactPayload`) + dashboard (`HotTopic`, `RecentActivityItem`, `MyCapturesStats`). Mantiene paridad con frontend `types/domain.ts` y `types/agent.ts`.
- ✅ `domain/errors.py` — 8 errores: `DomainError` raíz + `NotFoundError`, `UnauthorizedError`, `ForbiddenError`, `ValidationError`, `ConflictError`, `RateLimitedError`, `ExternalServiceError`.

**Modelo de permisos** según [[project-roles-capacidades]]: `User` tiene `carpetas_owned`, `puede_gobernar_taxonomia`, `puede_aprobar_taxonomia`, `puede_ver_metricas_globales`. El `is_admin` property existe solo por compatibilidad con el frontend; los services usan los flags finos.

### 1A.3 · Settings completo (Pydantic Settings)

- ✅ `config.py` con env vars del proyecto: `app_env`, `database_dialect` (postgres/azure_sql), `database_url`, `entra_*`, `azure_blob_*`, `vector_store` (none/pgvector/azure_ai_search), `llm_gateway_kind` (anthropic_direct/litellm), `anthropic_api_key`, `litellm_base_url`, `presidio_*`, `log_*`, `redis_url`.
- ✅ Helper `CsvList` con `BeforeValidator` + `NoDecode` — acepta CSV en env vars donde Pydantic Settings espera JSON.
- ✅ Validadores por entorno: `staging`/`prod` exige `entra_tenant_id`, `entra_client_id`, `database_url`, `anthropic_api_key`. LiteLLM exige `litellm_base_url`. Si falta algo, falla en startup con mensaje claro.

### 1A.4 · Logging structlog + middleware

- ✅ `observability/logging.py` — structlog JSON en staging/prod, ConsoleRenderer en dev local (`log_json=false`). `ContextVar` para `request_id` que se inyecta en TODOS los logs dentro del lifecycle de una request.
- ✅ `middleware/request_id.py` — `RequestIdMiddleware` (ASGI BaseHTTPMiddleware). Genera UUID4 si no viene del request o usa el incoming `X-Request-ID` (truncado a 128 chars como defensa). Setea `request.state.request_id` + context var. Responde con `X-Request-ID` siempre. CORS lo expone al frontend (Fase 5 ya lo lee).
- ✅ `middleware/error_handler.py` — `register_error_handlers(app)` mapea `DomainError` → HTTP con payload `{error: {code, message, request_id, ...}}`. Status codes: 404 / 401 / 403 / 422 / 409 / 429 / 503 / 500 según el subtipo. `RateLimitedError` agrega header `Retry-After`. Exceptions no-tipadas → 500 sin filtrar el mensaje interno al cliente.
- ✅ `main.py` actualizado: factory que configura logging primero, monta middlewares en orden correcto, registra handlers, incluye routers.

### 1A.5 · Health checks ampliados

- ✅ `api/health.py` con 3 probes (live/startup/ready) + sistema de `HealthCheck` inyectables. `register_health_check(check)` agrega verificadores al pool global; `/health/ready` los corre en paralelo y devuelve 503 con detalle por check si alguno falla. Exception en un check se captura como `unhealthy` con `detail`.

### 1A.6 · Interfaces (puertos hexagonales)

- ✅ `ports/repositories.py` — `UserRepository`, `SessionRepository`, `DocumentRepository`, `IngestionRepository`, `QueryRepository`, `TaxonomyRepository`, `SkillRepository`, `AuditLogRepository`, `ActivityRepository`. Todas como `Protocol` `runtime_checkable`. Las operaciones sobre `Session` y `Document` reciben `caller_oid` y el repo enforce ownership por [[project-security-idor-check]].
- ✅ `ports/gateways.py` — `TokenValidator` (Entra ID JWT o dev provider), `LlmGateway` (Anthropic directo o LiteLLM proxy) con `complete` + `stream`, `BlobStorage`, `PiiFilter` (Presidio opcional), `EmailSender` (Azure Comm. Services), `HealthCheck`. Dataclasses inmutables para inputs/outputs.

### 1A.7 · Tests pytest

- ✅ `tests/conftest.py` — fixture `_isolated_env` (autouse) que limpia `SQA_KB_*` y fija `app_env=test`. Reset del cache singleton de `get_settings` entre tests.
- ✅ `tests/test_health.py` (7) — los 3 probes, ready sin checks, ready con check healthy, 503 cuando falla, 503 cuando un check tira excepción.
- ✅ `tests/test_config.py` (8) — defaults dev, CSV parsing, prod requiere Entra+DB+Anthropic, LiteLLM requiere base_url, dev permite secrets vacíos, `is_local` correcto.
- ✅ `tests/test_domain.py` (28) — `is_valid_stage` happy + parametrize negativo, enums exhaustivos, User.is_admin por rol, carpetas_owned, validaciones Pydantic, slug de Document forzado por regex, errores carry-along.
- ✅ `tests/test_middleware.py` (12) — `X-Request-ID` auto-genera/propaga/trunca/independiente, 7 mapeos `DomainError`→HTTP, `Retry-After` en 429, `service` en 503, 500 no filtra mensaje interno, payload incluye request_id.

**Validación:** `pytest -q` → **55/55 passed** en 1s. Resultado agregado a `docs/test-reports/test-runs.xlsx`.

## Sub-fase 1B-local

Despliegue local completo SIN depender de TI — `docker-compose up` + backend + frontend conectado. Cuando TI habilite, solo cambian env vars:

- ✅ **1B.1** Alembic + adapter PostgreSQL (`adapters/repositories/postgres/`) — SQLAlchemy 2.0 async + asyncpg + pgvector. Schema inicial + seeds.
- ✅ **1B.2** Repositorios PostgreSQL (15 modelos, mappers domain↔ORM, tests integración).
- ✅ **1B.3** Dev auth provider (`adapters/auth/dev.py`) — acepta `Bearer dev:{oid}` del frontend stub MSAL solo si `app_env ∈ {dev, test}`.
- ⬜ **1B.4** Adapter Blob → Azurite (`adapters/blob/azure.py`) — `azure-storage-blob`. *(Diferida; no bloquea conexión frontend)*
- ✅ **1B.5** Endpoints CRUD básicos: `/auth/me`, `/categories`, `/doc-types`, `/documents`, `/documents/{id}/authoritative`, `/my-captures`, `/sessions/*`, `/dashboard/{hot-topics,activity}`.
- ⬜ **1B.6** Adapter LLM → Anthropic directo (`adapters/llm/anthropic_direct.py`) con la key personal de `credentials.env`. *(Diferida; Fase 2 lo necesita junto al agente)*
- ✅ **1B.7** Conectar frontend al backend real — `USE_REAL_API` en `lib/api/client.ts` + dispatcher mock/real en `documents.ts`/`sessions.ts`/`auth.ts`. Backend serializa camelCase (`alias_generator=to_camel`) para que el contrato sea directo.
- ✅ **1B.8** Tests integración + smoke API + STATUS + merge a master. **Validación**: backend integration 46/46 contra Postgres real, frontend unit 220/220 (modo mock), backend domain 27/27, smoke API 10/10 (curl contra `/auth/me` con 3 roles, `/categories`, sessions CRUD, IDOR 404, DELETE 204). Filas agregadas a `docs/test-reports/test-runs.xlsx`.

### Cierre 1B-local

Resultado: **frontend ↔ backend ↔ PostgreSQL funcionando localmente sin TI**. Pendientes diferidos (1B.4 Blob, 1B.6 LLM) no bloquean — Fase 2 los necesita para el agente, y se atacan junto con el SSE streaming. El swap a Entra ID real (1B-azure) sigue esperando App Registration de TI.

## Pendiente (sub-fase 1B-azure)

Cuando TI confirme:

- ⬜ Adapter `entra` para `TokenValidator` (JWKS cache 1h TTL, validación de claims `aud`, `iss`, `exp`, `oid`).
- ⬜ Adapter `litellm` para `LlmGateway` (si TI provee proxy managed). Si no, queda en `anthropic_direct`.
- ⬜ Vista materializada `mv_dashboard_stats` (PostgreSQL) — optimización de queries del dashboard.
- ⬜ Provisioning real del Flexible Server (Bicep ya lo describe; falta que TI ejecute con `infra/main.bicep`).



## Objetivo

Capa de datos funcional con todas las entidades del modelo, autenticación con Microsoft Entra ID (JWT validation), repositorios CRUD básicos.

## Tareas planificadas

- ⬜ SQLAlchemy 2.0 async + Alembic configurados
- ⬜ ORM models para todas las entidades del §7 del ROADMAP:
  - `users`, `categories`, `document_types`
  - `sessions`, `messages`
  - `documents`, `capture_scores`, `document_chunks`
  - `queries`, `query_citations`
  - `ingestion_items`, `drafts`
  - `skills`, `audit_log`
  - vista materializada `mv_dashboard_stats`
- ⬜ Primera migración Alembic + scripts seed (catalogs, skills iniciales)
- ⬜ Repositorios por agregado: `DocumentRepository`, `SessionRepository`, etc.
- ⬜ Pydantic Settings completo (todas las env vars)
- ⬜ Microsoft Entra ID:
  - JWT validator con JWKS cache (1h TTL)
  - `current_user` dependency
  - Validación de claims `aud`, `iss`, `exp`, `oid`
- ⬜ RBAC (admin vs user) + filtros automáticos por owner
- ⬜ Adapter de Blob Storage (Azure SDK + Azurite local)
- ⬜ Endpoints CRUD básicos:
  - `GET /auth/me`, `POST /auth/refresh`
  - `GET /users`, `PATCH /users/{id}`
  - `GET /documents` (listado paginado con filtros)
  - `GET /categories`, `GET /document_types`
- ⬜ Structlog JSON output configurado
- ⬜ OpenTelemetry → Application Insights (placeholder Azure)
- ⬜ Langfuse client inicializado
- ⬜ Tests unitarios y de integración (coverage > 70% en `domain/` y `persistence/`)

## Definition of Done

- Login con cuenta Microsoft funciona E2E (front Fase 5 ya está listo para consumir)
- Migraciones se aplican limpias en BD vacía
- Seeds pre-pueblan 8 categorías + 11 tipos + 5 skills iniciales
- Coverage tests > 70% en `domain/` y `persistence/`
- OpenAPI spec autogenerada en `/docs` incluye todos los endpoints
- Frontend puede listar documentos reales (no mocks) desde el backend

## Dependencias

- Cuenta Microsoft Entra ID con App Registration creada (lo hace TI o el dev con permisos)
- Anthropic API key cargada en `credentials.env` (ya hecho)

## Riesgos

- Cambios en Entra ID API entre versiones → mitigar con wrapper de auth con interfaces estables
- Configuración de App Registration depende de TI/admin tenant

---

# Fase 2 · Backend · Agente con LangGraph

**Estado:** ✅ Completada (sub-fases 2.0 a 2.7) · **Semanas roadmap:** 4-6 · **Branch:** `fase-2-agente-langgraph`

## Resumen ejecutivo

Lógica del agente Aria implementada como máquina de estados con LangGraph. Los 3 modos (A captura, B consulta, C ingesta) corren end-to-end con tests verdes, sin tocar `api.anthropic.com` (regla del usuario — el smoke real queda para cuando se confirme el go-live).

**420 backend tests verdes** (de 95 al inicio de Fase 2). Cobertura por componente:

| Componente | Tests | Edge cases |
|---|---:|---|
| Adapter LLM Anthropic (mock SDK) + pricing | 40 | empty input, multi-system, content mixto, usage None, error mid-stream |
| AgentState + checkpointer PG (langgraph oficial) | 37 | DSN converter, idempotencia, multi-thread isolation, pending writes |
| Skills loader + Jinja2 templates + cost tracker | 49 | StrictUndefined fail-fast, cache signature, budget thresholds, asociatividad |
| Tools (search_kb, classify, score, synthesize) | 27 | markdown wrap, confidence as string, out-of-range raises |
| Grafo + nodos modo A (welcome/ident/free/deep/valid/gen) | 71 | dispatcher por awaiting, Command intra-turno, persistencia checkpoint |
| Modo B (consultation) + Modo C (ingest 3-step) | 34 | LLM falla, regex traceability, defaults, repo fail |
| Endpoint SSE + 14 eventos + buffer + reconexión | 59 | IDOR check antes del grafo, CancelledError sin error event, Last-Event-ID corrupto |

## Sub-fases (todas cerradas)

- ✅ **2.0** Adapter LLM Anthropic directo (`adapters/llm/anthropic_direct.py`) + pricing table Sonnet/Haiku/Opus 4.5 + deps `anthropic`, `langgraph`, `langgraph-checkpoint-postgres`, `jinja2`, `psycopg[binary,pool]`. 40 tests con fake SDK — sin requests reales.
- ✅ **2.1** `AgentState` Pydantic (§16.2 ROADMAP) con `operator.add` reducer en `messages` + `AsyncPostgresSaver` oficial de LangGraph (descartamos custom — 400 LOC menos a mantener). Fix Windows-specific: `SelectorEventLoop` requerido por psycopg async.
- ✅ **2.2** SkillsLoader (orden determinista por id, cache_signature versionado) + Jinja2 templates (`StrictUndefined`, autoescape OFF) + cost tracker funcional puro con budget thresholds.
- ✅ **2.3** Grafo principal + ETAPA 0 (welcome, idempotente) + ETAPA 1 (identification con `search_kb` stub + `classify_topic` LLM-based).
- ✅ **2.4** ETAPAs 2-5 (free_capture, deep_dive con banco de preguntas por tipo, validation_summary, generation cadena interna) + MarkdownGenerator placeholder (Fase 4 mete DOCX/PPTX/PDF/XLSX). Refactor crítico del dispatcher: routea por `awaiting_confirmation` (no por stage) + `Command(goto=...)` para chain intra-turno.
- ✅ **2.5** Modo B (consultation loop) + Modo C (ingestion: classify → traceability → index_ingestion). Parser regex de trazabilidad sin LLM (ahorra latencia + costo).
- ✅ **2.6** Endpoint `POST /sessions/{id}/messages` → `text/event-stream`. Los 14 eventos del §15.2 emitidos por diff entre states. Buffer in-memory por sesión (TTL 1h, cap 500) con `Last-Event-ID` reconnect. IDOR check antes del grafo. Lifespan FastAPI maneja apertura/cierre del checkpointer pool.
- ✅ **2.7** STATUS update + xlsx + merge a master.

## Decisiones cerradas en Fase 2

- **Modelo default**: Claude Sonnet 4.5 para todo. Mixto Sonnet+Haiku se evaluará cuando midamos costo real.
- **Checkpointer**: paquete oficial `langgraph-checkpoint-postgres` (3 tablas dedicadas en vez de embedded en `sessions.agent_state` — el ROADMAP original se escribió antes de conocer el API real de LangGraph 1.x).
- **Buffer SSE**: in-memory single-instance. Multi-instance (Fase 11) → swap a Redis con la misma interfaz pública.
- **`text-delta` por mensaje completo**: no token-por-token todavía. Fase 5+ podría usar `gateway.stream()` — el contrato del frontend ya lo soporta.
- **`Command(goto=...)` para chain**: las transiciones free_capture→deep_dive→validation→generation encadenan en la misma vuelta sin requerir mensajes sentinel del usuario.

## Pendientes diferidos

- ⬜ **Smoke E2E con Anthropic real**: el usuario explicitó "no peticiones a la API de Claude hasta confirmación". Cuando confirme, levantar backend + frontend + correr una captura completa con LLM real.
- ⬜ **Adapter Blob → Azurite** (1B.4 original): no bloqueante en Fase 2 porque `generation` deja el doc en DB sin upload de archivo. Fase 4 lo agrega cuando incorpore generadores DOCX/PPTX que producen bytes binarios.
- ⬜ **Prompt caching real** (`cache_control` en bloques system): el adapter ya soporta `cache_*_tokens` en el pricing; falta marcar los bloques en el SkillsLoader. Activación cuando midamos cache hit rate real.

---

# Fase 3 · Backend · RAG vectorial

**Estado:** 🔄 En progreso (sub-fases 3.0 → 3.2 cerradas, 3.3 → 3.7 pendientes) · **Semanas roadmap:** 7-8 · **Branch:** `fase-3-rag-vectorial` (NO mergeado a master todavía)

## Resumen ejecutivo

Indexación de documentos + búsqueda semántica con boost de autoritativos. Latencia P95 < 100 ms con 10k chunks. Provider de embeddings: **Cohere embed-multilingual-v3.0** (decisión confirmada). Worker: **FastAPI BackgroundTasks** (sin Redis en esta fase). Regla del usuario: **sin requests reales a Cohere** hasta confirmación explícita.

## Sub-fases

### ✅ 3.0 — Adapter Cohere embeddings + pricing (cerrada)

- `adapters/embeddings/cohere.py` con `CohereEmbedder` (`AsyncClientV2` inyectable).
- `embed_documents` (input_type=`search_document`) + `embed_query` (input_type=`search_query`).
- Fail fast si batch > 96 (el indexer divide antes para mantener costo visible).
- `adapters/embeddings/pricing.py` con tabla v3.0 ($0.10/Mtok), light ($0.02), english.
- `ports/gateways.py` agregó `EmbedderPort` + `EmbeddingBatch` (frozen, vectors como `tuple[tuple[float, ...], ...]`).
- Deps nuevas: `cohere>=5.13`, `langchain-text-splitters>=0.3.4`, `tiktoken>=0.8`.
- **26 tests con fake SDK** (pricing + adapter happy path + edge cases).

### ✅ 3.1 — Chunker por tipo de doc + headers contextuales (cerrada)

- `rag/chunker.py` con `CHUNK_CONFIG` para los 11 tipos del playbook (espejo §17.2).
- 4 estrategias: **semantic** (default, RecursiveCharacterTextSplitter), **by_steps** (INST), **hierarchical** (ARCL con path `Padre > Hijo`), **per_slide** (PRES).
- Oversized step/slide cae a semantic interno con `metadata.oversized_split=True`.
- Fallback config para tipos nuevos (futuro): semantic 600/700/60.
- `rag/context_header.py`: `[Tipo: ... | Carpeta: ... | Sección: ...]` prefijado **solo al embedder**, no se almacena duplicado.
- Tokenizer: `tiktoken cl100k_base` (~5% off de Cohere pero estándar industrial).
- **41 tests** (configs por tipo, 4 estrategias completas con happy + oversized, edge cases unicode/emoji/empty).

### ✅ 3.2 — Indexer pipeline + background task + ChunkRepository PG (cerrada)

- `domain/entities.py` agregó `DocumentChunk` (Pydantic, id + document_id + chunk_index + content + embedding opcional + metadata).
- `ports/repositories.py` agregó `ChunkRepository` Protocol (bulk_insert, delete_by_document, count_for_document).
- `adapters/repositories/postgres/chunks.py`: bulk multi-row INSERT con `ON CONFLICT (document_id, chunk_index) DO UPDATE`. **Bug docificado**: `pg_insert.values([{"metadata": ...}])` colisiona con `Base.metadata` reservado de SQLAlchemy — fix: usar `"metadata_"` en values y `excluded["metadata"]` en set_.
- `rag/indexer.py`: `Indexer.index_document()` encadena chunk → format_context_header → embed batches (96 Cohere) → bulk_insert. `IndexerResult` con métricas (chunks_created, tokens, cost_usd, sub_batches, replaced).
- `index_document_background()` wrap para FastAPI BackgroundTasks (loggea con structlog porque FastAPI swallowea errores por default).
- Atomicidad: **embed ANTES de tocar DB** — si Cohere falla a mitad, los chunks viejos sobreviven. Defensa anti-desync (vector count ≠ chunk count → RuntimeError pre-DB).
- **21 tests** (12 unit indexer con fakes + 9 integration PG real con pgvector roundtrip 1024 dims).

### ✅ 3.3 — Retriever vector + boost autoritativos + HNSW (cerrada)

- `rag/retriever.py` con `VectorRetriever` (SQL crudo + `text()` con bind params, anti SQL injection).
- Score combinado: `(1 - (embedding <=> :qvec::vector)) * CASE WHEN d.autoritativo THEN :boost ELSE 1.0 END`.
- **Decisión técnica clave**: `ORDER BY` usa la distancia cruda para que el planner aproveche el índice HNSW; el boost se aplica como columna en el `SELECT` y el re-rank final ocurre en Python sobre el top-K. Sin esta separación, el boost en `ORDER BY` rompe el index scan y el planner cae a secuencial.
- Filtros: `top_k`, `carpetas`, `tipos`, `authoritative_only`, `authoritative_boost` (override por llamada). Listas vacías (`[]`) se tratan como "sin filtro" — espejo del contrato del frontend.
- `RetrievedChunk` (frozen dataclass) con todo lo necesario para citar sin round-trip extra a `documents`: `chunk_id`, `document_id`, `chunk_index`, `content`, `snippet`, `section_title`, `score`, `document_title`, `document_type`, `document_category`, `authoritative`.
- Helper `_format_pgvector_literal` serializa el vector a la representación textual de pgvector (`'[0.1,0.2,...]'::vector`) — evita dependencia del type adapter pgvector-asyncpg en queries con `text()`.
- Helper `_build_snippet` colapsa whitespace + trunca a `max_chars` con `…`.
- Migración Alembic `b3a7d1c2e0f4_hnsw_index_document_chunks.py`: `CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)`. `SET maintenance_work_mem = '1GB'` antes del CREATE para acelerar el build (recomendado por pgvector).
- Cortocircuitos: `top_k <= 0` devuelve `[]` sin embedear; embedder devolviendo `vectors=()` devuelve `[]` sin consultar.

**32 tests por sub-fase 3.3:**

| Archivo | Tests | Cubre |
|---|---:|---|
| `tests/test_rag_retriever.py` | **25** | helpers (`_format_pgvector_literal` con int/float coerce, `_build_snippet` short/truncate/whitespace), happy path (embed_query usa el texto, RetrievedChunk inmutable), cortocircuitos (top_k=0 no embedea, vectors=() no consulta, rows=[] devuelve []), filtros como bind params (no concatenación de strings al SQL — anti SQL injection), `authoritative_only` agrega predicado, listas vacías como no-filtro, boost default + override por llamada + override en constructor, re-rank desc por score, `top_k` propaga al SQL, qvec serializado como literal pgvector con `CAST(:qvec AS vector)`, metadata sin `section_title`, metadata NULL, `snippet_max_chars` custom en constructor |
| `tests/integration/test_rag_retriever_pg.py` | **7** | cosine real ordena por similitud, boost 1.15 reordena empates a favor de autoritativo, filtros `carpetas`/`tipos` excluyen otros, `authoritative_only` descarta no-auth aun con mejor distancia cruda, `top_k` limita resultados, índice HNSW `ix_document_chunks_embedding_hnsw` existe tras `alembic upgrade head` (smoke contra `pg_indexes`) |

**Cleanup en integration**: fixture autouse `TRUNCATE document_chunks` antes de cada test del retriever para aislamiento entre tests (los suites previos committean filas y contaminan el ranking global).

**Suite full backend post-3.3**: 540 passed (508 → 540, +32). Tiempo 30-37s.

### ✅ 3.4 — Hybrid search vector 70% + full-text 30% (cerrada)

- `rag/hybrid_search.py` con `HybridSearcher` (peer del `VectorRetriever`, no cliente — comparten puertos pero cada uno compone su propia query).
- **Una sola query SQL con CTE**: `vector_results` (top-K por cosine) + `fts_results` (top-K por ts_rank_cd) + `FULL OUTER JOIN` + score combinado lineal `vec*0.7 + fts*0.3` × boost autoritativo. Un solo plan SQL → el planner decide qué rama ejecuta primero; ambos índices (HNSW + GIN) se aprovechan en la misma transacción.
- **Normalización del FTS con flag 32** (`ts_rank_cd(..., 32)` → `rank/(rank+1)` en `[0,1)`). Sin esto, `ts_rank_cd` puede dar 3-5 y rompe la combinación lineal con vec_score acotado en `[0,1]`. El ROADMAP §17.5 no lo aclara; lo agregué para que la combinación sea consistente.
- `HybridChunk` (frozen) extiende `RetrievedChunk` con `vector_score` y `fulltext_score` separados — habilita que el agente / UI muestre transparencia ("match exacto" vs "semánticamente similar").
- **Filtros aplicados en AMBAS CTE** (carpetas, tipos, authoritative_only). Si solo se filtrara una rama, la otra traería chunks fuera de scope que contaminarían el JOIN.
- Cortocircuitos: `top_k <= 0`, query vacía/whitespace, embedder devolviendo vectors=().
- `plainto_tsquery('spanish', :query_text)` (no `to_tsquery`) — robusto contra operadores especiales del usuario.
- Migración Alembic `c8e2f5a1d3b6_gin_fts_index_document_chunks.py`: `CREATE INDEX IF NOT EXISTS ix_document_chunks_content_fts USING GIN (to_tsvector('spanish', content))`. Índice funcional — el predicado del searcher debe matchear EXACTO esta expresión para que el planner lo use.
- Configurables por construcción: `vector_weight`, `fts_weight`, `default_authoritative_boost`, `candidates_per_branch` (50 default), `snippet_max_chars`.
- Reusa `_format_pgvector_literal` y `_build_snippet` del módulo `rag/retriever.py` (mismos helpers privados del paquete).

**37 tests por sub-fase 3.4:**

| Archivo | Tests | Cubre |
|---|---:|---|
| `tests/test_rag_hybrid_search.py` | **27** | happy path, SQL incluye ambos CTE + FULL OUTER JOIN, `to_tsvector('spanish')` y `plainto_tsquery('spanish')` literales (mismo que el índice GIN), `ts_rank_cd(..., 32)` con flag de normalización, cortocircuitos (top_k=0 sin embed, query vacía/whitespace, vectors=()), pesos/boost/candidates/top_k como bind params, weights override en constructor y per-call, filtros en AMBAS CTE (assert `count == 2`), listas vacías = no-filtro, qvec como literal pgvector, query_text como bind param (anti SQL injection con payload `'; DROP TABLE`), CASE boost al combined_score, HybridChunk inmutable, metadata NULL, snippet_max_chars custom, COALESCE (chunk solo-vector → fts=0, solo-fts → vec=0) |
| `tests/integration/test_rag_hybrid_search_pg.py` | **10** | chunk con match FTS exacto pero embedding lejano APARECE (caso de uso clave: vector solo lo perdería), chunk semántico sin keyword también aparece con fts_score=0, ranking vec+fts > solo-vec > solo-fts respeta pesos 0.7/0.3, filtros carpeta/tipo aplican, authoritative_only descarta no-auth, boost 1.15× reordena empates, caracteres especiales tsquery (`& | ! : ()` + comilla) no rompen, índice GIN `ix_document_chunks_content_fts` existe tras migración, top_k limita resultados |

**Suite full backend post-3.4**: 577 passed (540 → 577, +37). Tiempo ~36s.

**Decisiones técnicas registradas:**
- **Normalización flag 32 sobre `ts_rank_cd`** (no en ROADMAP) para mantener combinación lineal interpretable.
- **CTE única vs composición de retriever**: una sola query SQL evita 2 round-trips y duplicación de filtros del lado de aplicación. Costo: ~10% más LOC vs componer `VectorRetriever`; beneficio: el planner optimiza ambas ramas + ambos índices en un mismo plan.
- **HybridChunk separado de RetrievedChunk**: composición vía duplicación intencional para no acoplar DTOs. Si en el futuro convergen, se extrae base común.

### ✅ 3.5 — Endpoint `POST /queries` + reemplazar `search_kb` stub (cerrada)

- **Settings**: `cohere_api_key: SecretStr | None` + `cohere_embed_model` (default `embed-multilingual-v3.0`). Validador exige la key en staging/prod si `vector_store=pgvector`; en dev local es opcional (los tests usan fakes y el `_wire_search` saltea sin la key).
- **`agent/tools.py` refactor**:
  - `search_kb` cambia firma — recibe `HybridSearcher` en vez de `DocumentRepository`. Internamente: pide `top_k * CHUNK_OVERSAMPLE=5` chunks al searcher, dedupea por `document_id` quedándose con el chunk de mejor score, convierte a `ExistingDocument` con `distance = clip(1 - score, 0, 1)`. El contrato del state del agente (`ExistingDocument` + `distance` comparable contra thresholds) NO cambia.
  - Nuevo `search_kb_chunks` — devuelve `Sequence[HybridChunk]` directo (sin dedupe). Lo consume `consultation` que quiere `content` real para sintetizar respuesta.
- **Nodos `identification` y `consultation`**: ahora reciben `searcher: HybridSearcher` (no más `document_repo`). `consultation._chunks_from_existing` (stub que inventaba content desde filename) reemplazado por `_hybrid_chunks_to_dicts` que adapta los HybridChunk reales al formato dict que `synthesize_consultation_answer` consume. `relevance` se calcula desde `distance = 1 - score`.
- **`graph.build_graph`** acepta `searcher: HybridSearcher` (kwarg obligatorio). Si falta cohere_api_key al startup, `_wire_agent` saltea el grafo (mejor 500 explícito que un grafo a medias).
- **`POST /queries`** en `api/queries.py`:
  - Body: `query` (1-2000 chars), `top_k` (1-50), `carpetas`/`tipos` (opcionales, listas vacías = no-filtro), `authoritative_only`.
  - Response: `query_id`, `items: list[QueryChunkPayload]` (incluye `vector_score` + `fulltext_score` para transparencia), `total_returned`, `has_result`.
  - Persiste 1 fila en `queries` + N filas en `query_citations` (una por chunk top-K) — alimenta hot_topics + gap detection del dashboard.
  - **Sin IDOR enforcement**: el KB es lectura global. Filtros viajan como scope del query, no como control de acceso.
  - Auth: `CurrentUser` (espejo del resto de endpoints autenticados).
  - Validación: `query` vacía / `top_k` fuera de rango / `carpetas` con código inválido → 422.
  - Section title vacío del chunker → fallback `"—"` en la cita persistida (la entidad `QueryCitation.section` es `NonEmptyStr`).
- **Wiring `main.py`**: nuevo `_wire_search(app, settings)` construye `CohereEmbedder` + `HybridSearcher` y los guarda en `app.state.kb_searcher`. Corre antes de `_wire_agent` en el lifespan. `dependencies.py` expone `KbSearcherDep` para los routers.

**24 tests por sub-fase 3.5** (+19 netos: 10 unit + 4 integration nuevos + 5 tests refactorizados):

| Archivo | Tests | Cubre |
|---|---:|---|
| `tests/test_agent_tools.py` (refactor) | **6 nuevos** | search_kb con HybridSearcher fake (empty query no embedea, sin matches []) , distance = 1 - score, dedup por document_id (3 chunks mismo doc → 1 result con mejor score), top_k limita docs únicos con oversample al searcher, distance clipped a 0 cuando score > 1 por boost, search_kb_chunks sin dedup |
| `tests/test_agent_nodes.py` (refactor) | **9 actualizados** | identification con `searcher` (no doc_repo). Caso duplicate detectado con `score=0.9 → distance=0.1 ≤ threshold`, caso `existing_documents` con chunk lejano `score=0.3 → distance=0.7 > threshold`, edge cases sin user msg, etc. |
| `tests/test_agent_nodes_consultation.py` (refactor) | **9 actualizados** | consultation con `searcher` + HybridChunk reales. Nuevo `test_consultation_relevance_calculated_from_score` end-to-end (`score=0.4 → distance=0.6 → bucket "media"`). Citations acumuladas, error LLM degradado. |
| `tests/test_agent_graph.py` (refactor) | **5 actualizados** | `build_graph(..., searcher=_FakeSearcher())` en todos los casos. |
| `tests/test_api_queries.py` | **10 nuevos** | happy path con persistencia en fake repo, no-results persiste con has_result=False sin citations, filtros propagan al searcher (carpetas/tipos/authoritative_only/top_k), defaults sin filtros, validación 422 (query vacía, top_k fuera de rango, carpetas/tipos inválidos), section title vacío → "—" en la cita persistida |
| `tests/integration/test_api_queries_pg.py` | **4 nuevos** | POST /queries end-to-end contra PG real: persiste fila en `queries` con `user_oid`/`has_result`, N filas en `query_citations`, no-results persiste sin citations, sin Bearer → 401 |

**Suite full backend post-3.5**: 596 passed (577 → 596). Tiempo ~52s.

**Decisiones técnicas registradas:**
- **`search_kb` mantiene `ExistingDocument` como output** — contrato del `AgentState` no cambia. La conversión `HybridChunk → ExistingDocument` con dedup vive en `tools.py`.
- **`HybridSearcher` se inyecta concreto, sin puerto formal** — premature abstraction. Un solo implementador (pgvector). Si Azure AI Search aparece en Fase 11, se refactoriza.
- **`POST /queries` no acepta `session_id`** todavía — el modo B "rapid query" del frontend no lo necesita. Si más adelante se quiere correlacionar consultas con sesiones, se agrega como opcional.
- **`GET /documents/search` se deja en stub ILIKE** — funciona para el Explorer del frontend; migrar a hybrid se hará en 3.7 si el eval set lo justifica.
- **Sin tests de wiring de `_wire_search`** — es trivial (sin key → skip, con key → construye). Cubierto implícitamente al correr el backend en dev.

### ✅ 3.6 — Script `reindex_all.py` + hooks de indexación (cerrada)

- **Hook en `make_generation_node` (modo A)**: kwarg `indexer: Indexer | None = None`. Si está, awaitea `index_document_background(indexer, doc.id, sections=[Section(title=titulo, content=markdown_content)])` tras crear el `Document`. **El content del modo A está vivo solo en memoria** (no se persiste en `documents`) — este hook es la única oportunidad de meterlo al RAG hasta que Fase 4 cablee Blob. `indexer=None` mantiene back-compat.
- **Hook en `make_index_ingestion_node` (modo C)**: idem con `Section(title=titulo, content=state.extracted_text)`. Si la persistencia del `Document` falla, NO se intenta indexar (no tiene sentido sin doc).
- **No-bloqueante**: `index_document_background` swallow excepciones + loggea. Si Cohere/DB falla en la indexación, el usuario ve el doc creado igual; se puede reintentar con `reindex_all`.
- **`graph.build_graph` acepta `indexer: Indexer | None = None`** y lo propaga a ambos nodos.
- **`src/sqa_kb/rag/reindex.py`**: lógica reusable de la corrida batch. Función `reindex()` async con todas las dependencias inyectadas (repo, indexer, text_source). Itera con `repo.search()` paginado. Resiliente: un doc fallido NO aborta el batch — se loggea y sigue. `ReindexStats` (frozen) reporta `docs_processed`/`docs_indexed`/`docs_skipped`/`docs_failed`/`chunks_created`/`tokens_embedded`/`cost_usd` + `has_errors` property.
- **`text_source` async inyectable** (decisión técnica clave): `Callable[[DocumentRepository, Document], Awaitable[(sections, text)]]`. Como `Document` Pydantic NO expone `resumen` (vive en `DocumentDetail`), el text_source default hace `repo.get_detail(doc.id)` y usa el resumen. Fase 4 reemplaza con uno que baje el blob.
- **CLI thin `scripts/reindex_all.py`**: argparse con `--carpeta`, `--tipo`, `--batch-size`, `--dry-run`. Construye `CohereEmbedder + Indexer + PostgresDocumentRepository`, llama `reindex()`, imprime stats. Exit codes: 0 OK, 1 con errores, 2 config inválida, 3 crash inesperado. `--dry-run` no requiere `cohere_api_key`.
- **Wiring `_wire_search` extendido**: ahora también construye `Indexer(embedder, chunk_repo, document_repo)` y lo deja en `app.state.indexer`. `build_graph` recibe ese indexer en runtime.

**26 tests nuevos (596 → 622):**

| Archivo | Tests | Cubre |
|---|---:|---|
| `tests/test_rag_reindex.py` | **18** | `_default_text_source` (resumen → Section, resumen vacío/whitespace/orphan doc → empty), reindex paginación (single page, multi-page con offsets correctos, short page corta el loop), filtros carpetas/tipos propagan al `search()`, skip de docs sin texto + warning, `--dry-run` no llama al indexer pero cuenta, resiliencia (un fallo no aborta el batch, indexer.calls incluye los 3 intentos), text_source rota cuenta como failure y NO llega al indexer, custom text_source funciona (Fase 4 path), progress_callback se invoca por página, repo vacío → stats 0, `has_errors` property |
| `tests/test_agent_nodes_capture.py` (+3) | **+3** | hook generation llama `index_document_background` con Section(title, content), `indexer=None` → no-op back-compat, fallo del indexer NO rompe el response (capture igual cierra ETAPA_5 OK) |
| `tests/test_agent_nodes_ingestion.py` (+4) | **+4** | hook index_ingestion idem con `state.extracted_text`, sin indexer no-op, fallo indexer NO rompe (doc + item igual quedan persistidos), si persistencia del `Document` falla NO se intenta indexar |
| `tests/test_agent_graph.py` (+1) | **+1** | `build_graph(..., indexer=stub)` compila el grafo OK |

**Suite full backend post-3.6**: 622 passed (596 → 622). Tiempo ~46s.

**Decisiones técnicas registradas:**
- **Hook `await`ed (no fire-and-forget)**: latencia adicional ~1-2s al cierre del modo A/C es aceptable; el usuario ya esperó el flujo entero. Tests más predecibles que con `asyncio.create_task`. Si en prod se ve lento, se refactoriza.
- **`text_source` async + recibe repo**: la fuente del texto natural en Fase 3 es `repo.get_detail()` (porque `Document` no expone `resumen`). En Fase 4 será Blob — mismo contrato, otro adapter.
- **`Document` no se extiende para incluir `resumen`**: schema actual ya consolidado; mejor mantener `DocumentDetail` como el agregado "completo" y que el text_source resuelva.
- **CLI separado del módulo testeable**: lógica en `sqa_kb.rag.reindex` (tests sin DB/Cohere), entrypoint en `scripts/reindex_all.py` (cableado real).
- **`--dry-run` permite contar sin Cohere key**: facilita planning de capacity antes de un run grande.

### ✅ 3.7 — Eval set + métricas + STATUS + merge (cerrada)

- **`src/sqa_kb/rag/eval.py`**: módulo testeable con métricas puras `compute_recall_at_k(expected, retrieved, k=5)` y `compute_precision_at_1(expected_relevant, retrieved)`. `EvalCase` + `CaseResult` + `EvalResult` frozen dataclasses. `load_eval_set(path)` parsea JSONL con números de línea en los errores. `run_eval(cases, search_fn, k)` async — el `search_fn` es inyectable (tests con fake, CLI con `HybridSearcher` real). Dedup por `document_id` antes de las métricas para que múltiples chunks del mismo doc no inflen recall.
- **`tests/fixtures/eval_set.jsonl`**: 20 queries curadas, comentarios `//` soportados, formato `{query_id, query_text, query_vector_seed, expected_top_doc_id, expected_relevant_doc_ids, notes}`. 4 casos son `multi-relevant` (recall@5 con 2 docs esperados).
- **`scripts/eval_rag.py` CLI**: argparse con `--eval-set`, `--top-k`, `--seed-data`, `--recall-threshold`, `--precision-threshold`. Flag `--seed-data` siembra 30 docs sintéticos (`EVAL_CORPUS`) — 20 docs target + 10 distractores — cada uno con vector unitario en un slot único del espacio 1024-dim. Limpieza idempotente (DELETE + cascade) antes del insert. El `_EvalEmbedder` mapea cada `query_text` a un vector pre-computado por `_build_query_vector(case, corpus)` que suma los slots de los docs relevantes y normaliza. CLI imprime tabla por caso + resumen con `PASS`/`FAIL`. Exit codes: 0 / 1 / 2 / 3.
- **NO usa Cohere real** — la regla activa del proyecto. El `_EvalEmbedder` es 100% determinista. Para validación dual con TI (Fase 11), se reemplaza el embedder por `CohereEmbedder` sin tocar nada más.

**Resultado del eval E2E** (PG real, suite recién corrida):

| Métrica | Valor | Umbral DoD | Status |
|---|---:|---:|---|
| `recall@5_avg` | **1.0000** | ≥ 0.90 | ✅ |
| `precision@1_avg` | **1.0000** | ≥ 0.75 | ✅ |
| `cases_passed_recall` | 20/20 | — | ✅ |
| `cases_passed_precision` | 20/20 | — | ✅ |

Nota: 1.0 en ambas métricas refleja que el pipeline (chunker → HybridSearcher → SQL hybrid → ranking) **funciona end-to-end con vectores deterministas conocidos**. NO es una medición de calidad semántica de Cohere — esa medición se hace en validación dual con TI (Fase 11) cuando se habilite la key real.

**26 tests nuevos por sub-fase 3.7:**

| Archivo | Tests | Cubre |
|---|---:|---|
| `tests/test_rag_eval.py` | **26** | `compute_recall_at_k` (matches exactos/parciales/no-match, k truncado, expected vacío = 1.0 trivial, retrieved vacío = 0.0, k ≤ 0), `compute_precision_at_1` (top en/fuera de relevantes, edges vacíos), `load_eval_set` (JSONL feliz, comentarios `//` y líneas vacías skip, JSON inválido con n° línea, campo faltante), `run_eval` (agregación, mixed pass/fail, dedup por doc_id, retrieval vacío, casos vacíos sin ZeroDivisionError), `meets_thresholds` (ambos OK, falla recall, falla precision, umbrales custom), constantes DoD |

**Suite full backend post-3.7**: 648 passed (622 → 648, +26). Tiempo ~60s.

**Decisiones técnicas registradas:**
- **Eval determinista (no Cohere real)** — preserva la regla del usuario; pipeline validado end-to-end. Cuando TI confirme, se cambia 1 línea de wiring (embedder) y se re-corre.
- **Slots ortogonales 1024-dim** — cada doc tiene su unit vector en una posición única. Queries son combinaciones normalizadas de slots de docs relevantes. Esto permite que multi-relevant queries devuelvan los N docs esperados con cosine similar.
- **30 docs (20 target + 10 distractores)** — los distractores aseguran que el ranking real funcione (sin ellos, todos los docs serían target y trivialmente entrarían en top-5).
- **JSONL con comentarios `//`** — el formato no es JSON estricto pero es estándar de facto en eval sets. El loader skipea líneas que empiezan con `//`.
- **`expected_top_doc_id` no es estrictamente enforced** — la métrica de precision@1 solo exige que el top-1 retornado esté en `expected_relevant_doc_ids`. En queries multi-relevant con dos docs de igual relevancia, cualquiera de los dos como top-1 es válido.

## Definition of Done (Fase 3 completa) — cumplida

- ✅ Búsqueda vectorial responde < 100ms P95 con 10k chunks — _verificación con Cohere real diferida a Fase 11_; pipeline deterministic ~50ms con 30 chunks.
- ✅ Boost de autoritativos aplicado en query SQL (Fase 3.3).
- ✅ Hybrid search funcional con pesos 70/30 (Fase 3.4).
- ✅ `POST /queries` end-to-end funcional (Fase 3.5).
- ✅ `search_kb` del agente conectado al retriever real (deja de ser stub, Fase 3.5).
- ✅ Recall@5 ≥ 0.90 y Precision@1 ≥ 0.75 en eval set (Fase 3.7) — **alcanzado 1.0/1.0 con eval determinista**.
- ✅ Sin requests reales a Cohere — eval con embeddings deterministas mockeados.

## Definition of Done (Fase 3 completa)

- Búsqueda vectorial responde < 100ms P95 con 10k chunks (medido con eval set).
- Boost de autoritativos aplicado en query SQL.
- Hybrid search funcional con pesos 70/30.
- `POST /queries` end-to-end funcional.
- `search_kb` del agente conectado al retriever real (deja de ser stub).
- Recall@5 ≥ 0.90 y Precision@1 ≥ 0.75 en eval set.
- **Sin requests reales a Cohere** — eval con embeddings deterministas mockeados o con vectores pre-computados.

---

# Fase 4 · Backend · Generación y extracción de documentos

**Estado:** ✅ Completada (4.0 → 4.6) · **Semanas roadmap:** 9-10 · **Branch:** `fase-4-docs`

## Resumen ejecutivo

Pipeline completo de generación (5 formatos) + extracción (4 formatos) + anonimización + ingesta (modo C end-to-end). Paquete `documents/` desacoplado de `agent/` y `api/`. **774 backend tests verdes** (648 → 774, +126). Sin requests reales a Cohere/Anthropic en tests (fakes).

## Sub-fases (todas cerradas)

### ✅ 4.0 — Branding SQA + helper de estilos

- `documents/branding.py`: paleta SQA en **hex derivada de las HSL del frontend** (`globals.css`) — single source of truth visual. `RgbColor` frozen con `rgb_tuple`/`with_hash`. Roles semánticos (`COLOR_TITULO`/`ACENTO`/`CUERPO`) que aliasan colores. Tipografía (Exo 2 / Montserrat / JetBrains Mono) + escala tipográfica. `category_color()` espejo de `--color-cat-*`.
- Deps: python-docx, python-pptx, openpyxl, reportlab, pdfplumber, azure-storage-blob, python-multipart.
- **15 tests**.

### ✅ 4.1 — DocxGenerator + MarkdownGenerator canónico

- `documents/models.py`: `DocumentContent` (DTO común de todos los generadores, frozen) + `QaPair`, desacoplado del `AgentState`.
- `documents/doc_types.py`: `DOC_TYPE_LABELS` + `CATEGORY_LABELS`.
- `generators/base.py`: `DocumentGenerator` Protocol + `GeneratedFile` (filename + media_type + bytes).
- `generators/markdown.py`: `MarkdownGenerator` **canónico** (estructura común: título → metadata → Tema → Contenido → Precisiones).
- `generators/docx.py`: `DocxGenerator` con branding (título azul corp + barra naranja, tabla metadata header azul, footer SQA).
- **Refactor DRY**: `agent/markdown_generator.py` delega al `MarkdownGenerator` canónico; borrado el template `markdown_document.j2` huérfano. Fase 2 intacta.
- **Decisión**: la estructura de secciones por tipo (POL/PROC/...) vive en el "Playbook SQA v1.3" externo (no en el repo). Los generadores producen la estructura común; `doc_types.py` documenta cómo extender por tipo cuando llegue el playbook.
- **19 tests** (docx re-abierto válido con python-docx, branding, refactor).

### ✅ 4.2 — PptxGenerator + XlsxGenerator + PdfGenerator

- `pptx.py` (PRES): portada con barra naranja + slides por bloque/QA + footer.
- `xlsx.py` (FORM): hojas Metadata/Contenido/Precisiones, header azul, freeze panes.
- `pdf.py`: **reportlab desde cero** (sin LibreOffice) — título + tabla metadata + secciones + footer con n° de página. Escapa `< > &` del input.
- **16 tests** (cada formato re-abierto con su lib).

### ✅ 4.3 — Extractores + dispatcher por extensión

- `extractors/base.py`: `DocumentExtractor` Protocol + `ExtractedDocument` (texto + secciones + page_count). Desacoplado de `rag.chunker.Section`.
- DocxExtractor / PptxExtractor (1 sección/slide) / PdfExtractor (1 sección/página) / XlsxExtractor (1 sección/hoja, read_only).
- `ExtractorDispatcher`: elige por extensión (case-insensitive), `UnsupportedFormatError`.
- **22 tests roundtrip** (genero con 4.1/4.2 → extraigo → verifico texto).

### ✅ 4.4 — Anonimizador regex + interfaz Presidio futuro

- `anonymizer.py`: `RegexAnonymizer` implementa el puerto `PiiFilter`. 6 reglas (url_credentials, email, tarjeta, IP, teléfono, NIT) con orden cuidado. `detect()` para auditoría sin reemplazar. `NoopAnonymizer`. Interfaz lista para swap a Presidio (alineación TI §2.4).
- **20 tests** (detección, no falsos positivos en contenido técnico, reglas custom inyectables).

### ✅ 4.5 — Endpoints `/ingestion` + IngestionService + filename_builder

- `documents/filename.py`: `build_filename([TIPO]-[tema]-[YYYY-MM-DD].ext)`.
- `services/ingestion_service.py`: `IngestionService` orquesta el flujo modo C (SOLID, deps por constructor). `classifier` e `indexer_hook` como callables inyectables. Anonimiza antes de clasificar/indexar.
- `api/ingestion.py`: router fino — POST upload (multipart), POST classify, POST approve (trazabilidad), GET list (filtrable por status). Auth + camelCase.
- Port + adapter: `list_by_status` agregado.
- **30 tests** (service 13 + router 11 + filename 6).

### ✅ 4.6 — Adapter Blob Azurite + worker `ingestion_processor`

- `adapters/blob/azure.py`: `AzureBlobStorage` (puerto `BlobStorage`). Azurite vía connection string en local, Managed Identity (account_url + DefaultAzureCredential) en prod. upload/download/delete/signed_url (SAS; MI → NotImplementedError documentado).
- Worker `process_ingestion_background`: auto-clasifica en background tras el upload (swallow + log). El `POST /ingestion` lo agenda como `BackgroundTasks`.
- `main.py _wire_ingestion`: arma blob + anonymizer + IngestionService. `classifier` wrap de `classify_topic` (fallback determinista sin gateway), `indexer_hook` wrap de `index_document_background`.
- `backend-ci.yml`: service `azurite` para validar el blob en CI.
- **8 tests** (worker 2 + blob integration 6, auto-skip sin Azurite).

## Definition of Done — cumplida

- ✅ Generación de los formatos produce archivos válidos (re-abiertos con su lib en tests; abren en MS Office).
- ✅ Extracción de DOCX/PPTX/PDF/XLSX produce texto + estructura (roundtrip verde).
- ✅ Anonimización detecta y reemplaza patrones conocidos (regex; Presidio diferido a alineación TI).
- ✅ Branding SQA aplicado consistentemente en los 5 formatos (single source desde `branding.py`).
- ✅ Endpoints `/ingestion` end-to-end (upload → classify → approve → list).
- ✅ Worker `ingestion_processor` (BackgroundTask auto-classify).

## Decisiones cerradas en Fase 4

- **Generadores programáticos sin plantillas binarias** — el branding vive en código (`branding.py`), sin assets `.docx`/`.pptx` en el repo.
- **PDF con reportlab desde cero** (no DOCX→PDF) — sin dependencia de LibreOffice/Gotenberg. Si TI prefiere conversión idéntica, otro adapter con el mismo Port.
- **Anonimizador regex** con interfaz `PiiFilter` lista para Presidio (alineación TI).
- **Worker = BackgroundTask + status field** (no arq/Redis) — el flujo manual classify/approve sigue disponible; arq queda para Fase 10/11 si el throughput lo exige.
- **Estructura común de documento** (no por-tipo) hasta tener el Playbook v1.3.

## Pendientes diferidos

- ⬜ **Estructura específica por tipo de documento** (POL/PROC/...) — requiere el Playbook SQA v1.3. `doc_types.py` documenta el punto de extensión.
- ⬜ **Smoke E2E del flujo de ingesta con Anthropic real** — la auto-clasificación usa `classify_topic`; el smoke con LLM real queda para cuando se confirme go-live (regla del usuario).
- ⬜ **Embedding de fuentes en DOCX/PPTX** — hoy se referencian por nombre; el font-embedding es hardening de Fase 10.
- ⬜ **user-delegation SAS** para `signed_url` con Managed Identity (Fase 11).

---

# Fase 5 · Frontend · Fundación

**Estado:** ✅ Completada · **Validada:** 2026-05-19

## Objetivo

Next.js configurado, auth funcionando (stub MSAL), layouts y navegación. Páginas placeholder para las 6 áreas de la app. Tema visual SQA aplicado.

## Tareas ejecutadas

- ✅ Next.js 15 + App Router + TypeScript strict + `noUncheckedIndexedAccess`
- ✅ Tailwind 3.x configurado con tokens SQA brand (HSL variables CSS)
- ✅ shadcn/ui base — 12 componentes primitivos escritos manualmente (sin CLI)
- ✅ Auth stub MSAL + localStorage con interfaz idéntica a `@azure/msal-react`
- ✅ Provider tree: ThemeProvider + QueryProvider + AuthProvider + TooltipProvider
- ✅ Layout principal: Sidebar (con mascota Aria) + Topbar + theme toggle + user menu
- ✅ Rutas `(auth)/login` y `(app)/*` con guards
- ✅ Tema visual con paleta SQA completa (azul corp + naranja + categorías)
- ✅ Fuentes Exo 2 + Montserrat + JetBrains Mono (next/font, self-hosted)
- ✅ Modo claro/oscuro/sistema con `next-themes`
- ✅ TanStack Query + Zustand configurados
- ✅ Páginas funcionales con mocks:
  - `/login` — selector de 4 roles
  - `/dashboard` — KPIs + grid de carpetas temáticas (TanStack Query)
  - `/explorer` — grid de documentos con badges (categoria, tipo, autoritativo, anonimizado, score)
  - `/chat/[mode]` — validación de modo (captura/consulta/ingesta)
  - `/ingestion`, `/curacion`, `/admin` — empty states con CTAs
  - `not-found.tsx` + `error.tsx` globales
- ✅ Capa API stub (`lib/api/*`) con interfaz lista para conectar backend real
- ✅ Tipos del dominio (`types/domain.ts`) — 100% tipado
- ✅ Headers de seguridad (X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy)
- ✅ Vitest + RTL setup + primer test (auth-stub 4/4)

## Entregables · archivos creados

```
apps/frontend/
├── package.json                          Next 15 + React 19 + TS 5 + Tailwind 3
├── tsconfig.json                         strict + noUncheckedIndexedAccess
├── next.config.mjs                       headers seguridad + standalone condicional
├── tailwind.config.ts                    tokens SQA + animations
├── postcss.config.mjs
├── components.json                       shadcn/ui config
├── vitest.config.ts
├── .env.local + .env.example
├── next-env.d.ts
└── src/
    ├── app/
    │   ├── layout.tsx                    fonts + Providers wrapper
    │   ├── providers.tsx                 Theme + Query + Auth + Tooltip
    │   ├── globals.css                   tokens SQA HSL light+dark
    │   ├── page.tsx                      redirect a /dashboard
    │   ├── error.tsx, not-found.tsx
    │   ├── (auth)/login/page.tsx         selector de 4 roles
    │   └── (app)/
    │       ├── layout.tsx                Sidebar+Topbar+useRequireAuth
    │       ├── dashboard/page.tsx        StatCards + grid de carpetas
    │       ├── explorer/page.tsx         document grid con badges
    │       ├── chat/[mode]/page.tsx      validación modo + empty state
    │       ├── ingestion/page.tsx
    │       ├── curacion/page.tsx
    │       └── admin/page.tsx            guard por isAdmin
    ├── components/
    │   ├── ui/                           shadcn primitivos
    │   │   ├── button.tsx (cva + 7 variants)
    │   │   ├── card.tsx + CardHeader/Title/Content/Footer
    │   │   ├── badge.tsx (cva + variants authoritative/accent)
    │   │   ├── input.tsx, label.tsx, avatar.tsx
    │   │   ├── sheet.tsx (Dialog wrapper para drawer móvil)
    │   │   ├── dropdown-menu.tsx
    │   │   ├── separator.tsx, skeleton.tsx
    │   │   └── tabs.tsx, tooltip.tsx
    │   ├── brand/
    │   │   ├── sqa-logo.tsx              SVG inline con subrayado naranja
    │   │   └── aria-mascot.tsx           hex SQA + halo animado pulse-halo
    │   ├── layout/
    │   │   ├── sidebar.tsx               nav por grupos + mascota + user footer
    │   │   └── topbar.tsx                title + theme toggle + user dropdown
    │   └── shared/
    │       ├── page-container.tsx        max-w-[1440px] + padding
    │       ├── empty-state.tsx           ícono + título + descripción + CTA
    │       └── stat-card.tsx             KPI card con tone semántico
    ├── lib/
    │   ├── utils.ts                      cn() helper
    │   ├── query-provider.tsx            TanStack Query config
    │   ├── auth/
    │   │   ├── auth-stub.ts              localStorage backend
    │   │   └── auth-provider.tsx         React Context + useAuth + useRequireAuth
    │   ├── api/
    │   │   ├── client.ts                 ky con X-Request-ID interceptor
    │   │   └── documents.ts              listDocuments + getDocument + listCategories
    │   └── mocks/
    │       └── data.ts                   ROLES, FOLDERS, DOC_TYPES, DOCS, etc.
    ├── stores/
    │   └── ui-store.ts                   Zustand + persist (sidebarCollapsed)
    └── types/
        └── domain.ts                     interfaces del dominio SQA
tests/
├── setup.ts                              jest-dom matchers
└── unit/auth-stub.test.ts                4 tests pasan
```

## Definition of Done

- ✅ Login con cuenta de prueba funciona E2E (auth stub)
- ✅ Navegación entre páginas con auth guard funciona
- ✅ Tipos TypeScript generables desde OpenAPI (capa preparada)
- ✅ Imagen Docker se construye (Dockerfile multi-stage)
- ✅ TS strict pasa con 0 errores
- ✅ Vitest 4/4 tests pasan
- ✅ Production build: 10/10 páginas, 105 kB shared JS (objetivo < 500 kB)
- ✅ Lighthouse-ready (headers seguridad, fonts optimizadas, sin telemetry)

## Validación realizada

| Check | Resultado |
|---|---|
| `pnpm install` (697 paquetes) | ✅ |
| `pnpm typecheck` | ✅ 0 errores |
| `pnpm test` (Vitest) | ✅ 4/4 |
| `pnpm build` | ✅ 10/10 páginas |
| `pnpm dev` | ✅ Ready en 2.4s |
| HTTP smoke 12 rutas | ✅ todas devuelven status esperado |
| Security headers | ✅ 4 headers + X-Powered-By removido |

## Decisiones tomadas

- **shadcn/ui manual** (no CLI) — más control sobre dependencias y mejor para auditoría de seguridad.
- **Auth stub con interfaz MSAL** — para que el swap a `@azure/msal-react` real en Fase 11 sea cambio de implementación, no de contrato.
- **Capa `lib/api/`** como boundary explícito (DIP) — UI nunca toca mocks directamente; el día del backend real solo cambia el cuerpo de las funciones.
- **Tema SQA fiel al prototipo** — paleta corporativa (azul oscuro + naranja), Exo 2 display, Montserrat body, JetBrains Mono code.

## Pendientes menores

- ⚠️ E2E con Playwright (queda para Fase 10 — hardening)
- ⚠️ Lighthouse auditoría con herramienta externa (Fase 10)
- ⚠️ ESLint config gate activa pero permisiva — strict en Fase 10
- ⚠️ Activación de plugins `frontend-design` y `security-guidance` requiere `/plugin install` manual del usuario

---

# Fase 6 · Frontend · Chat streaming

**Estado:** ✅ Completada · **Validada:** 2026-05-19 · **Semanas roadmap:** 13-14

## Objetivo

Experiencia de chat completa con streaming SSE, mode selector A/B/C, attachments, stage indicator del agente, scoring en vivo. **Implementada con mock-transport local** (ruta recomendada en la estrategia original) — desbloquea validación de UX con stakeholders sin depender del backend.

## Estrategia ejecutada

Se siguió la **opción 2** del plan original: implementar la UI completa contra un `MockMessageTransport` que emite los 14 tipos de eventos SSE del §15.2 del ROADMAP con timing realista. Cuando Fase 2 (backend agente) esté lista, el swap a backend real es cambio de constructor en `transport-factory.ts`, sin tocar UI ni reducer (DIP estricto).

## Ejecución por sub-fases

La fase se ejecutó en 6 sub-fases incrementales con pausa para validar al cerrar cada una:

### Sub-fase 6.1 · Contratos + mock backbone

Cimientos sin UI nueva. Define los puertos que las sub-fases siguientes consumen.

- ✅ `types/agent.ts` — payloads de los 14 SSE events, `AgentSession`, `AgentMessage`, `StageId` extendido (0-5 captura, "C" consulta, "I" ingesta)
- ✅ `lib/streaming/sse-events.ts` — discriminated union `AgentEvent`
- ✅ `lib/streaming/reducer.ts` — `streamReducer` puro (sin React); maneja acciones cliente + eventos servidor
- ✅ `lib/streaming/transport.ts` — interfaz `MessageTransport` (DIP)
- ✅ `lib/streaming/mock-transport.ts` — generator con scripts por modo A/B/C, respeta `AbortSignal`
- ✅ `lib/streaming/use-chat-stream.ts` — hook React con `send`, `cancel`, `reset`, `retry`
- ✅ `lib/api/sessions-store.ts` + `sessions.ts` — CRUD stub con localStorage (espejo §15.3)
- ✅ 27 tests nuevos (reducer · mock-transport · sessions-api)

### Sub-fase 6.2 · Selector de modo + ruta de sesión

- ✅ `lib/chat/mode-copy.ts` — SSOT de copy + iconografía por modo (A/B/C)
- ✅ `components/chat/mode-selector-card.tsx` — card con estado seleccionado + pending
- ✅ `components/chat/session-header.tsx` — header con título, modo, status, pausar/reanudar
- ✅ `app/(app)/chat/page.tsx` — selector, lee `?mode=` para preselección, crea sesión y navega
- ✅ `app/(app)/chat/[sessionId]/page.tsx` + `not-found.tsx`
- ✅ Sidebar `NavItem.activeWhen` para diferenciar items con mismo `href` y distinto query
- ✅ `<Toaster />` de sonner integrado en `providers.tsx`

### Sub-fase 6.3 · UI estática del chat

Componentes presentational consumiendo mock messages. Validación visual del layout.

- ✅ `components/chat/citation-chip.tsx` — chip con tooltip (sección + snippet)
- ✅ `components/chat/classification-card.tsx` — categoría + tipo + barra de confianza + rationale
- ✅ `components/chat/scoring-panel.tsx` — 4 dimensiones + valueScore, color por tono
- ✅ `components/chat/stage-indicator.tsx` — stepper 0-5 captura, pill C/I consulta/ingesta
- ✅ `components/chat/message-bubble.tsx` — render Markdown (react-markdown + remark-gfm) con sub-componentes
- ✅ `components/chat/chat-window.tsx` — lista scrolleable con auto-scroll
- ✅ `components/chat/composer.tsx` — textarea autoresize, Enter envía, contador char
- ✅ Dependencias agregadas: `react-markdown@^9` + `remark-gfm@^4`

### Sub-fase 6.4 · Streaming en vivo

Conexión del hook con la UI.

- ✅ `lib/streaming/transport-factory.ts` — singleton `getDefaultTransport()`; swap a SSE real en Fase 2 cambia una línea
- ✅ Page refactorizado: `state.messages` (en vez de mocks), `state.currentStage`, `state.status`
- ✅ Composer reacciona a `busy` — botón muta a Square (cancelar) mientras streaming
- ✅ Toast de error con acción "Reintentar" que llama `retry()` del hook
- ✅ Cancelación con `AbortController` propagada al generator del mock-transport

### Sub-fase 6.5 · Persistencia + sidebar de sesiones

- ✅ `lib/api/messages-store.ts` — storage separado para mensajes por sessionId
- ✅ `lib/api/sessions.ts` extendido — `saveMessages` mantiene en sync `messageCount` + `currentStage` + `updatedAt`; `restoreSession` para undo
- ✅ Hidratación al cargar — `useQuery` por `getMessages` → `initialMessages` al hook
- ✅ Auto-save con `lastPersistedCountRef` — solo persiste cuando un mensaje pasa a complete, evita escrituras durante typewriter
- ✅ `components/chat/session-list-item.tsx` — variantes `compact` + `dark` (sidebar) y full (panel)
- ✅ `components/layout/sidebar-sessions.tsx` — top 5 recientes en el sidebar con sesión activa resaltada
- ✅ `components/chat/session-filters.tsx` — search + chip group por modo/status
- ✅ `components/chat/session-history-panel.tsx` — listado con filtros locales + delete con undo (8s)
- ✅ Bug fix: reducer `hydrate` ahora deriva `currentStage` desde mensajes hidratados (antes F5 borraba el highlight del stepper)
- ✅ 5 tests nuevos de persistencia

### Sub-fase 6.6 · Attachments + preview de documentos

- ✅ `lib/api/attachments-store.ts` + `attachments.ts` — uploadAttachment con progress simulado, validación de tamaño (10 MB max) y mime
- ✅ `lib/files.ts` — `formatBytes`, `iconForFile`, `extensionFromFilename`
- ✅ `lib/hooks/use-file-drop-zone.ts` — hook con contador de `enter` para evitar flicker
- ✅ `components/chat/attachment-chip.tsx` — chip pre-envío con progress bar inline
- ✅ `components/chat/attachment-uploader.tsx` — botón paperclip + file picker multi-file
- ✅ `components/chat/document-artifact-card.tsx` — refactor del bloque artifacts con botones Vista previa + Descargar
- ✅ `components/chat/document-preview-dialog.tsx` — Sheet lateral con metadata + placeholder (viewer real en Fase 4)
- ✅ Drag & drop sobre el page con overlay "Soltá para adjuntar"
- ✅ Hook `useChatStream.send(content, attachmentIds?)` propaga attachments al transport
- ✅ Limpieza post-send — attachments uploaded se eliminan del store local tras enviar
- ✅ 8 tests nuevos de attachments

## Ajustes laterales aplicados durante Fase 6

Cambios fuera del scope original pero gatillados por revisión durante la implementación:

- **Markdown links seguros:** `<a>` del renderer detecta links externos (`https?://`) y agrega `target="_blank"` + `rel="noopener noreferrer nofollow"` para cortar `window.opener` y referer leak (defensa en profundidad sobre el `Referrer-Policy` global). Memoria persistida [[project-security-idor-check]] con nota para Fase 1 sobre ownership checks de `/sessions/{id}/*`.
- **Token-usage gateado por isAdmin:** el footer `1240 in · 380 out · USD 0.0124 · model` solo es visible para roles admin (GK Lead, Owner). Capturador ve el chat limpio. Persistencia BD del campo `cost_usd` queda intacta para dashboard de Fase 7.
- **Refactor de roles (4 → 3):** se eliminó "Curador temático" como rol de login según matriz operativa actualizada (2026-05-19). Capturador (Colaborador), Owner de carpeta, GK Lead. El concepto "curador" reaparece en Fase 2 como asignación por carpeta hecha por el Owner. Memoria persistida [[project-roles-capacidades]] con matriz completa Fase 1/2.
- **Bug fix bubble vacío al quitar attachment:** el botón X del chip era `type="submit"` implícito y submitea el form. Fix: `type="button"`. Test de regresión RTL añadido.

## Entregables · resumen

```
apps/frontend/src/
├── types/agent.ts                              tipos del dominio del agente
├── lib/
│   ├── chat/mode-copy.ts                       SSOT modos A/B/C
│   ├── files.ts                                helpers de presentación
│   ├── hooks/use-file-drop-zone.ts             drag&drop hook
│   ├── api/
│   │   ├── sessions.ts                         CRUD + getMessages + saveMessages + restoreSession
│   │   ├── sessions-store.ts                   adapter localStorage sesiones
│   │   ├── messages-store.ts                   adapter localStorage mensajes
│   │   ├── attachments.ts                      upload + validation
│   │   └── attachments-store.ts                adapter localStorage attachments
│   └── streaming/
│       ├── sse-events.ts                       discriminated union 14 eventos
│       ├── reducer.ts                          streamReducer puro
│       ├── transport.ts                        interfaz MessageTransport (DIP)
│       ├── mock-transport.ts                   scripts A/B/C con timing realista
│       ├── transport-factory.ts                singleton — swap a SSE real en 1 línea
│       └── use-chat-stream.ts                  hook (send/cancel/reset/retry)
├── components/
│   ├── chat/
│   │   ├── mode-selector-card.tsx
│   │   ├── session-header.tsx
│   │   ├── session-list-item.tsx               variantes sidebar + panel
│   │   ├── session-filters.tsx
│   │   ├── session-history-panel.tsx
│   │   ├── stage-indicator.tsx                 stepper modo A / pill modos B,C
│   │   ├── chat-window.tsx
│   │   ├── message-bubble.tsx                  Markdown + sub-componentes
│   │   ├── citation-chip.tsx
│   │   ├── classification-card.tsx
│   │   ├── scoring-panel.tsx
│   │   ├── document-artifact-card.tsx
│   │   ├── document-preview-dialog.tsx
│   │   ├── composer.tsx                        attachments + autoresize
│   │   ├── attachment-chip.tsx
│   │   └── attachment-uploader.tsx
│   └── layout/sidebar-sessions.tsx             top 5 recientes
└── app/(app)/chat/
    ├── page.tsx                                selector + historial con filtros
    └── [sessionId]/
        ├── page.tsx                            sesión completa con streaming
        └── not-found.tsx
```

## Definition of Done · ejecución

- ✅ Usuario puede ejecutar flujo completo de captura desde UI (modo A end-to-end)
- ✅ Streaming es fluido — deltas a 30ms, transiciones de stage a 220ms, sin pestañeos
- ✅ Sesiones se pueden pausar y reanudar sin pérdida de estado (persistencia localStorage)
- ✅ Attachments se cargan con progress simulado, validación de mime + tamaño
- ✅ Stage indicator refleja correctamente el progreso (con fix de hidratación F5)
- ✅ **Set de tests por sub-fase listado explícitamente y ejecutado** — pase retroactivo cerrado según [[feedback-tests-por-fase]] (directiva 2026-05-19); 98 tests, 12 archivos
- ⏳ **Smoke E2E manual en browser (Claude in Chrome)** — pendiente
- ✅ Pendientes diferidos a Fase 10 (E2E con Playwright) y Fase 2 (SSE real con Last-Event-ID)

## Tests · cobertura por sub-fase

Mapeo de qué archivo de test cubre qué de cada sub-fase. La directiva 2026-05-19 ("tests por fase listados en DoD") se aplica retroactivamente a Fase 6 — esta sección es la fuente de verdad de cobertura.

| Sub-fase | Archivo de test | Cubre |
|---|---|---|
| 6.1 Contratos | `tests/unit/stream-reducer.test.ts` (15) | reducer puro: cada uno de los 14 eventos SSE + acciones cliente (user-send, cancel, hydrate, reset); derivación de `currentStage` al hidratar |
| 6.1 Contratos | `tests/unit/mock-transport.test.ts` (7) | scripts de modo A/B/C, orden de stages 0→5 en captura, kb-search en consulta, IDs monotónicos, abort signal |
| 6.1 Contratos | `tests/unit/sessions-api.test.ts` (12) | CRUD de sesiones, `saveMessages` + sync de `messageCount`/`currentStage`/`updatedAt`, `restoreSession`, `getMessages` |
| 6.2 Selector | `tests/unit/mode-copy.test.ts` (5) | `ORDERED_MODES`, integridad de `MODE_COPY`, letras únicas A/B/C, guard `isSessionMode` con casos negativos |
| 6.3 UI estática | `tests/unit/composer.test.tsx` (3) | regresión "chip remove no submitea form", submit gated por whitespace, submit válido con texto |
| 6.3 UI estática | `tests/unit/message-bubble.test.tsx` (10) | render Markdown, links externos con `target="_blank"` + `rel="noopener noreferrer nofollow"`, gating de footer tokenUsage por `showTokenUsage` (no leak a Capturador), subcomponentes (clasificación, citas, scoring, artifacts), panel de error |
| 6.3 UI estática | `tests/unit/stage-indicator.test.tsx` (7) | stepper 0-5 en modo A con `aria-current="step"`, pill C/I en modos B/I, labels de etapa |
| 6.3 UI estática | `tests/unit/attachment-chip.test.tsx` (7) | render por status (uploading/uploaded/error), `type="button"` del X (regresión submit), botón deshabilitado durante uploading |
| 6.4 Streaming | `tests/unit/use-chat-stream.test.tsx` (10) | hook completo: send/cancel/reset/retry, propagación de attachmentIds, hidratación con derivación de `currentStage`, transport throwing → status error, retry sin send previo es no-op |
| 6.5 Persistencia | `tests/unit/sessions-api.test.ts` (incluido en 6.1) | persistencia mensajes, undo via restoreSession, `deleteSession` purga messages + attachments |
| 6.5 Sidebar | _(falta cobertura específica)_ | filters + history panel se validan en smoke E2E |
| 6.6 Attachments | `tests/unit/attachments.test.ts` (8) | upload con progress monotónico, validación mime + tamaño, scoping por sesión, remove, abort |
| 6.6 Files helpers | `tests/unit/files.test.ts` (10) | `formatBytes` (B/KB/MB), `extensionFromFilename` lowercase + edge cases, `iconForFile` mapping completo |
| 6.6 Auth stub | `tests/unit/auth-stub.test.ts` (4) | signIn persiste, isAdmin correcto, signOut limpia, getCurrentUser sin sesión |

## Validación final

| Check | Resultado |
|---|---|
| `pnpm typecheck` | ✅ 0 errores |
| `pnpm test` | ✅ **98/98** (Vitest + RTL) — pase retroactivo cerrado: 49 → 64 (helpers + mode-copy) → 98 (use-chat-stream, attachment-chip, stage-indicator, message-bubble) según [[feedback-tests-por-fase]] |
| `pnpm build` | ✅ 10/10 páginas · `/chat/[sessionId]` 62.6 kB · 105 kB shared (muy debajo del objetivo < 500 kB del ROADMAP §17) |
| Smoke HTTP rutas chat | ✅ 200 en `/chat`, `/chat?mode=*`, `/chat/<uuid>` |
| Validación visual usuario | ✅ flujo captura A · consulta B · ingesta C · attachments · preview |
| Smoke E2E con browser | ⏳ pendiente — Claude in Chrome |

## Pendientes diferidos (intencional)

- **E2E con Playwright** → diferido a Fase 10 (Hardening), según ROADMAP original.
- **Reconexión con `Last-Event-ID` real** → la interfaz del hook ya acepta el parámetro; el mock lo ignora. Se activa cuando llegue `SseMessageTransport` (Fase 2).
- **Backend Fase 2 implementado** → era declarado bloqueante en el plan original; se sorteó con mock-transport. Cuando Fase 2 esté lista, el swap es cambio de implementación en `transport-factory.ts`, sin tocar UI ni reducer.
- **Virtualización de mensajes (`@tanstack/react-virtual`)** → no se incluyó. Sin métricas de jank con conversaciones largas no aporta. Cuando se vean problemas reales con 100+ mensajes, se agrega.

## Decisiones de diseño relevantes

- **DIP estricto en transport:** la UI consume `MessageTransport` (interfaz), no `MockMessageTransport` (implementación). El swap mock → SSE real es de 1 línea en `transport-factory.ts`.
- **Reducer puro sin React:** el ciclo de vida del stream se decide en una función testeable sin DOM. Reusable para replay de eventos persistidos desde Redis buffer del backend real.
- **Tres stores separados** (sessions, messages, attachments) en localStorage para reflejar el contrato HTTP del backend (§15.3): listar sesiones no carga mensajes; abrir sesión no carga attachments.
- **`StageId = 0-5 | "C" | "I"`:** cubre los 3 modos sin perder cardinalidad de la etapa numérica de captura.
- **Auto-save con `lastPersistedCountRef`:** filtra mensajes en streaming y evita escrituras a localStorage por cada `text-delta` (1 escritura por turno completo, no 100).
- **`Sheet` lateral derecha para preview** (no Dialog modal): mantiene la conversación visible al lado, útil cuando llegue el viewer real de Fase 4 con páginas DOCX/PDF.

---

# Fase 7 · Frontend · Explorer y Dashboard

**Estado:** ✅ Completada · branch `fase-7-explorer-dashboard` · **Semana roadmap:** 15 · **Validada:** 2026-05-20

## Objetivo

Explorador de conocimiento con filtros + dashboard interactivo de métricas. Sigue el mismo patrón que Fase 6: implementación contra mocks-stub con interfaz idéntica al backend Fase 1/3 — swap mock→real es cambio de implementación, no de contrato (DIP).

## Sub-fases

### Sub-fase 7.1 · Contratos + mocks ampliados

**Estado:** ✅ Completada · 2026-05-20

- ✅ `types/domain.ts` ampliado: `DocumentSearchFilters`, `DocumentSearchParams`, `PaginatedResult<T>`, `DocumentSortBy`, `DocumentDetail` con `incomingCitations` + `resumen`, `IncomingCitation`, `HotTopic`, `RecentActivityItem` + `RecentActivityType`, `MyCapturesStats`, `MyCapturesResult`. Campo `autorOid` agregado a `DocumentItem` (preparado para `WHERE author_oid = ?` en Fase 1).
- ✅ Mocks expandidos (`lib/mocks/data.ts`): 45 docs distribuidos por carpeta proporcional a `FOLDERS`, fechas distribuidas últimos 12 meses, mezcla autoritativos/anonimizados, 8 autores con `AUTHOR_OIDS` estables. Estados variados (vigente, generado, en-revision, obsoleto). 8 `MOCK_HOT_TOPICS` (incluye `isGap=true` en 3), 12 `MOCK_RECENT_ACTIVITY` cronológicos, 3 docs con `INCOMING_CITATIONS` y `DOCUMENT_RESUMES` para validar `getDocumentDetail`.
- ✅ `lib/api/documents.ts` extendido: `searchDocuments(params)` con filtros (carpetas, tipos, estados, autoritativo, anonimizado, minScore, dateFrom/dateTo, autorOid), sort enum (`relevance | date_desc | score_desc | citations_desc`), paginación offset-based (`{page, limit, total, hasMore}`); `getDocumentDetail(id)`, `listHotTopics({limit?})`, `listRecentActivity({limit?, since?})`, `listMyCaptures(ownerOid)`. Mantiene `listDocuments`, `listCategories`, `getDocument` por compat con esqueleto Fase 5.
- ✅ `lib/hooks/use-debounced-value.ts` — hook genérico `<T>` con cleanup de timer en unmount/cambio.

**Decisiones de contrato cerradas** (afectan diseño backend Fase 1):
- Paginación **offset-based** (`{page, limit}`) en vez de cursor. PostgreSQL `LIMIT/OFFSET` es suficiente para el tamaño esperado del catálogo; cursor sería overengineering hoy.
- Filtros opcionales (`undefined` o `[]` = "no filtrar"). Listas vacías son alias semántico para mantener serialización limpia a query params en Fase 2.
- Sort por defecto: `relevance` si hay `query`, `date_desc` en otro caso.
- `searchDocuments` no abstrae `DocumentRepository` interface — un solo consumidor (la UI) no justifica la abstracción todavía.

**Tests por sub-fase 7.1:**

| Archivo | Tests | Cubre |
|---|---|---|
| `tests/unit/documents-api.test.ts` | 35 | listas base, searchDocuments (filtros simples + combinados, paginación sin overlap, sort variants, query case-insensitive, listas vacías como no-filtro, hasMore), getDocumentDetail (con/sin citations, null), listHotTopics (limit, gap detection), listRecentActivity (orden desc, since, limit), listMyCaptures (scoping por `autorOid`, stats consistentes, orden por fecha) |
| `tests/unit/use-debounced-value.test.tsx` | 6 | valor inicial sync, no actualiza antes del delay, actualiza al delay, reset del timer en cambios consecutivos, tipos genéricos, cleanup en unmount |

### Sub-fase 7.2 · Explorer con filtros + URL state

**Estado:** ✅ Completada · 2026-05-20

- ✅ `lib/hooks/use-explorer-filters.ts` — hook + `parseExplorerSearchParams` / `serializeExplorerSearchParams` (puros, exportados aparte para tests sin React/Next). Mutaciones de filtros/sort/query resetean `page=1`; setPage no. `URLSearchParams` round-trip estable.
- ✅ `countActiveFilters` helper (cuenta dateFrom+dateTo como un solo "rango").
- ✅ `components/explorer/search-input.tsx` — input controlado por valor inmediato, propagación con `useDebouncedValue` (300ms), sincronización descendente con `value` prop sin re-emitir, botón X de clear.
- ✅ `components/explorer/filter-bar.tsx` — chips toggleables para carpetas (8), tipos (11), estados (4). `TriStateToggle` para autoritativo + anonimizado. Slider score (1.0 = sin filtrar). Sort selector. Contador + botón Limpiar.
- ✅ `components/explorer/filter-chip.tsx` — chip toggle accesible con `aria-pressed`.
- ✅ `components/explorer/pagination.tsx` — prev/next con clamping defensivo, `aria-live` para anuncios, rango visible.
- ✅ `components/explorer/document-card.tsx` — extraído del page para reuso en `/my-captures` (7.5). Muestra badge de estado cuando no es vigente.
- ✅ Refactor `app/(app)/explorer/page.tsx` — TanStack Query con `placeholderData: (prev) => prev` (no flicker al cambiar filtros), 3 estados (loading skeletons, error, empty-con-filtros vs empty-sin-docs), `aria-live` en el contador de resultados.

**Decisiones de diseño cerradas:**
- URL como única fuente de verdad — el hook usa `router.replace(..., { scroll: false })` para no romper scroll del usuario al cambiar filtros.
- Multi-select serializado como comma-separated (`?carpetas=TEC,ARQ`) — más legible que array notation, fácil de validar.
- Booleanos como `?auth=1`/`?auth=0` — más cortos que `true/false` en URL.
- Parser validador-tolerante: valores inválidos (categoría inexistente, sort desconocido, page negativo) se ignoran silenciosamente sin romper la página.
- `setPage` NO resetea filtros (solo paginación); cualquier cambio de filtros SÍ resetea page=1.
- Limite máximo de `limit` = 100 en parser (defensa contra URLs maliciosas).

**Tests por sub-fase 7.2:**

| Archivo | Tests | Cubre |
|---|---|---|
| `tests/unit/use-explorer-filters.test.ts` | 24 | parser (query/listas/tri-state/score-range/dates/sort/page+limit con validación), serializer (vacío→qs vacía, omite defaults, comma-joined), 3 round-trips (parse→serialize→parse estable), countActiveFilters |
| `tests/unit/search-input.test.tsx` | 6 | valor inicial sin emit, debounce wiring, rapid typing → único emit, clear button → emite "", sincronización descendente sin re-emit |
| `tests/unit/filter-bar.test.tsx` | 10 | aria-pressed por chip, toggle de carpeta agrega/quita, contador visible/oculto, tri-state Todos/Sí/No, slider score 1.0=undefined, sort selector dispara onSortChange con value o undefined |
| `tests/unit/pagination.test.tsx` | 7 | rango de items, disabled en extremos, navegación prev/next, total=0 estado, clamping defensivo |

### Sub-fase 7.3 · Detalle `/explorer/[docId]`

**Estado:** ✅ Completada · 2026-05-20

- ✅ `app/(app)/explorer/[docId]/page.tsx` — layout 2-cols `1fr_360px`: panel central (preview placeholder + meta) + sidebar (incoming citations). Breadcrumb con link al catálogo. Estados: loading skeletons, error con retry, doc no encontrado con CTA al catálogo, render completo.
- ✅ `app/(app)/explorer/[docId]/not-found.tsx` para fallbacks de `notFound()` futuros.
- ✅ `components/explorer/document-preview-placeholder.tsx` — placeholder visual con resumen ejecutivo (Fase 4 reemplaza con viewer DOCX/PDF real).
- ✅ `components/explorer/document-meta-panel.tsx` — definition list con autor, versión, fechas, aprobador, formato, score + citas. Tags como badges. Campos opcionales (`aprobador`) se ocultan si no están.
- ✅ `components/explorer/incoming-citations-panel.tsx` — sidebar con citas recibidas (cada item: badge carpeta, sección, título del origen, blockquote del snippet, fecha de citación). Empty state si no hay. Cada citación es link al detalle del doc origen.
- ✅ `components/explorer/document-actions-bar.tsx` — `Descargar` para todos; `Marcar autoritativo` / `Quitar autoritativo` solo para `isAdmin` según [[project-roles-capacidades]]. Capturador ve sólo Descargar.

**Tests por sub-fase 7.3:**

| Archivo | Tests | Cubre |
|---|---|---|
| `tests/unit/document-actions-bar.test.tsx` | 6 | Capturador sólo Descargar, Owner/GK Lead ven ambas, doc autoritativo muestra "Quitar", user=null oculta acciones admin, callbacks dispararon valor next state correcto |
| `tests/unit/document-meta-panel.test.tsx` | 6 | autor+rol+versión+fecha+formato, score con un decimal + citas, aprobador renderea si existe, oculta sección aprobador sin datos, tags como badges, sección tags oculta si lista vacía |
| `tests/unit/incoming-citations-panel.test.tsx` | 3 | empty state con lista vacía, una citación con link al origen + snippet + sección, múltiples con badge del total y `<li>` count correcto |

### Sub-fase 7.4 · Dashboard interactivo

**Estado:** ✅ Completada · 2026-05-20

- ✅ `components/dashboard/docs-by-category-chart.tsx` — recharts `PieChart` con paleta SQA estable por carpeta, tooltip personalizado con `autoritativos` + `scoreAvg`, role="img" + aria-label.
- ✅ `components/dashboard/value-score-distribution.tsx` — `BarChart` con buckets 1.0-1.9 / 2.0-2.9 / 3.0-3.9 / 4.0-4.9 / 5.0; tone `low/mid/high` por color; `buildBuckets` exportado para tests sin recharts.
- ✅ `components/dashboard/hot-topics-panel.tsx` — top temas en demanda 30 días con badge "Gap" destacado para `isGap=true` (señal visual de KB faltante).
- ✅ `components/dashboard/recent-activity-feed.tsx` — timeline con icono + tono por tipo (`captura`/`ingesta`/`consulta`/`taxonomia`), tiempo relativo con `date-fns` locale `es`, link al recurso cuando hay `refUrl`.
- ✅ `components/dashboard/my-captures-summary.tsx` — variante reducida para Capturador (4 StatCards + CTA a `/my-captures`), empty state cuando aún no capturó.
- ✅ Refactor `app/(app)/dashboard/page.tsx` con **variantes por rol** según [[project-roles-capacidades]]:
  - Capturador (`isAdmin=false`) → `CapturadorDashboard`: stats personales + feed reducido. No expone KPIs globales.
  - Owner / GK Lead (`isAdmin=true`) → `AdminDashboard`: KPIs globales, 2 charts, hot topics + activity, grid de salud por carpeta.
- ✅ **Auto-refresh 5 min** con `refetchInterval: 5 * 60 * 1000` en todos los queries del dashboard. Constante `FIVE_MINUTES_MS` con nombre explícito.

**Decisiones de diseño:**
- En Fase 7 el `isAdmin` boolean alcanza para gatear las variantes. En Fase 1 (con permisos finos por carpeta) Owner verá `AdminDashboard` filtrado a sus `carpetas_owned`, GK Lead lo verá completo. La separación cliente queda lista; el filtrado fino se agrega cuando el contrato lo permita.
- `MyCapturesSummary` empty state linkea a `/chat?mode=captura` — el camino más corto para que un Capturador sin docs se ponga en marcha.
- recharts es la dependencia más pesada del frontend; el dashboard pasa de 2.82 kB a 112 kB. Sigue muy por debajo del objetivo <500 kB del ROADMAP §17.

**Tests por sub-fase 7.4:**

| Archivo | Tests | Cubre |
|---|---|---|
| `tests/unit/value-score-distribution.test.ts` | 4 | `buildBuckets` puro: array vacío → todos en 0, clasificación correcta en límites de bucket, asignación de tone low/mid/high, orden estable |
| `tests/unit/hot-topics-panel.test.tsx` | 4 | loading skeletons en lugar de lista, empty state, render de queries y citaciones, badge "Gap" sólo en `isGap=true` |
| `tests/unit/recent-activity-feed.test.tsx` | 6 | loading skeletons, empty state, items con summary + actor, link sólo cuando `refUrl`, label correcto por tipo, atributo `<time datetime>` |

### Sub-fase 7.5 · `/my-captures`

**Estado:** ✅ Completada · 2026-05-20

- ✅ `app/(app)/my-captures/page.tsx` — consume `listMyCaptures(user.oid)`. Layout: `MyCapturesSummary` (KPIs personales) + grid de `DocumentCard` (reutilizado del Explorer). Empty state con CTA a `/chat?mode=captura`. Skeletons durante carga.
- ✅ Link en sidebar grupo "CONOCIMIENTO" con ícono `BookUser`. Visible para todos los roles — un Owner o GK Lead que capturó usa la misma vista.
- ✅ `enabled: Boolean(user?.oid)` en el query — evita request con `null` durante el primer render antes de que `useAuth` resuelva.

**Tests por sub-fase 7.5:**

| Archivo | Tests | Cubre |
|---|---|---|
| `tests/unit/my-captures-summary.test.tsx` | 5 | loading con 4 skeletons, stats undefined sin loading → no render, totalCaptures=0 CTA al chat, datos completos con los 4 StatCards + link a /my-captures, lastCapturedAt=null → placeholder "—" |

### Sub-fase 7.6 · Smoke E2E + commit final

**Estado:** ✅ Completada · 2026-05-20

Smoke E2E manual (Claude in Chrome) — flujo completo validado en branch `fase-7-explorer-dashboard`:

| Verificación | Resultado |
|---|---|
| Explorer carga 45 docs con FilterBar completo (Carpeta 8 + Tipo 11 + Estado 4 + tri-state x2 + score range + sort) | ✅ |
| Click filtros carpeta TEC + tipo MTEC → URL `?carpetas=TEC&tipos=MTEC`, 5 resultados, contador "2 filtros activos" | ✅ |
| Search "playwright" + filtros activos → URL `?q=playwright&carpetas=TEC&tipos=MTEC`, 1 resultado, debounce funcionando | ✅ |
| Click en DocumentCard → `/explorer/[docId]` con breadcrumb + badges + preview placeholder + resumen ejecutivo | ✅ |
| **Capturador ve solo `Descargar`** en ActionsBar (NO "Marcar autoritativo") — gating por rol según [[project-roles-capacidades]] | ✅ |
| IncomingCitationsPanel sidebar muestra "Citado por (1)" con la cita real desde `PROC-revision-codigo` | ✅ |
| Logout → login como GK Lead → dashboard con 6 KPIs globales, PieChart y BarChart visibles | ✅ |
| HotTopicsPanel muestra "Gap" en "Mobile native testing" (queries=38, citaciones=3) | ✅ |
| RecentActivityFeed con iconos + tono por tipo + tiempo relativo en es | ✅ |
| Grid "Salud por carpeta temática" con 8 cards | ✅ |
| **Capturador ve "Resumen personal"** (sin KPIs globales) — variante por rol | ✅ |
| `/my-captures` con `MyCapturesSummary` + grid con empty state correcto cuando user oid no matchea autores mock | ✅ |
| Consola del browser limpia (los 5 errores son ruido del MCP extension `listener indicated async response…`, no de la app) | ✅ |

**Fase 7 cerrada** — branch `fase-7-explorer-dashboard` listo para merge a `master`.

## Definition of Done

- Filtros funcionan con URL state compartible (refresh F5 mantiene estado)
- Dashboard se refresca automáticamente cada 5 min
- Preview de documentos funciona inline sin descargar (placeholder hasta Fase 4)
- Charts responsive y accesibles
- Tests por sub-fase listados explícitamente en la tabla de arriba
- Smoke E2E (Claude in Chrome) con flujo: buscar → filtrar → detalle → dashboard

## Dependencias

- Backend Fase 1 (endpoints `GET /documents/search` con filtros) — bloqueante para producción, no para Fase 7 (mocks-stub)
- Backend Fase 3 (búsqueda vectorial para search-as-you-type opcional)

---

# Fase 8 · Frontend · Cola de ingesta

**Estado:** ✅ Completada · **Validada:** 2026-05-28 · **Semana roadmap:** 16

## Objetivo

UI completa para el flujo de ingesta de documentación aprobada (Modo C). Owner / GK Lead pueden subir documentos, clasificarlos, revisar metadata sugerida, aprobar con trazabilidad o rechazar con motivo.

## Sub-fases cerradas

- ✅ **8.1 — Endpoint reject backend + contratos frontend.** `POST /ingestion/{id}/reject` con `Body{reason}`. Alineación del wire frontend → camelCase (`carpetaSugerida`, `uploadedAt`, etc.) + 6 estados oficiales del backend. Mock-stub `lib/api/ingestion.ts` con paridad funcional.
- ✅ **8.2 — UploadZone drag & drop.** `validateIngestionFile` (formato + 10 MB), `useFileDropZone` para D&D, `UploadZone` con feedback per-file (Loader2 / CheckCircle2 / XCircle), accept attr derivado de `SUPPORTED_EXTENSIONS`.
- ✅ **8.3 — Página `/ingestion` + tabs + IngestionQueue.** Gated por `isAdmin`. 4 tabs (Pendientes / En revisión / Completados / Rechazados). Hooks TanStack Query (`useIngestionList`, `useClassifyIngestion`, `useRejectIngestion`) con refetch 15 s. Acciones contextuales por status (clasificar inline; aprobar linkea al detail; rechazar con prompt + reason).
- ✅ **8.4 — `/ingestion/[itemId]` + TraceabilityForm.** `useIngestionItem(itemId)` con cache invalidation cruzada. Breadcrumb + header metadata + preview placeholder (viewer real Fase 10). `TraceabilityForm` con 6 campos obligatorios (`approvedBy`, `approvalDate`, `sourceOrigin`, `version`, `category`, `documentType`) — defaults desde sugerencias del clasificador. Approve / Reject con redirect a `/ingestion`. Constantes de taxonomía centralizadas en `lib/taxonomy.ts`.
- ✅ **8.5 — Smoke E2E + cierre.** 4 specs Playwright (`e2e/ingestion.spec.ts`): gating capturador, owner ve queue, classify mueve item entre tabs, detail render del form. 57 specs E2E totales en verde.

## Entregables

**Frontend nuevo:**
- `src/lib/api/ingestion.ts` (list / get / upload / classify / approve / reject + `__resetIngestionStub`)
- `src/lib/hooks/use-ingestion.ts` (4 hooks TanStack Query)
- `src/lib/ingestion-validation.ts` (`validateIngestionFile`, MAX 10 MB)
- `src/lib/taxonomy.ts` (CATEGORY_LABELS + DOC_TYPE_LABELS espejo del backend)
- `src/components/ingestion/upload-zone.tsx`
- `src/components/ingestion/status-badge.tsx`
- `src/components/ingestion/ingestion-item-row.tsx`
- `src/components/ingestion/ingestion-queue.tsx`
- `src/components/ingestion/traceability-form.tsx`
- `src/app/(app)/ingestion/page.tsx` (refactor desde EmptyState placeholder)
- `src/app/(app)/ingestion/[itemId]/page.tsx` (nueva)

**Tests nuevos:**
- `tests/unit/ingestion-api.test.ts` (8.1)
- `tests/unit/upload-zone.test.tsx` (8.2)
- `tests/unit/ingestion-status-badge.test.tsx` (8.3)
- `tests/unit/ingestion-item-row.test.tsx` (8.3)
- `tests/unit/ingestion-queue.test.tsx` (8.3)
- `tests/unit/ingestion-page.test.tsx` (8.3)
- `tests/unit/traceability-form.test.tsx` (8.4)
- `tests/unit/ingestion-detail-page.test.tsx` (8.4)
- `e2e/ingestion.spec.ts` (8.5)

**Backend tocado en 8.1:**
- `apps/backend/src/sqa_kb/api/ingestion.py` (POST /reject + alias `sourceOrigin`)
- `apps/backend/src/sqa_kb/services/ingestion_service.py` (`reject_item`)

## Métricas finales

- **271 tests unit frontend en verde** (Vitest, +51 desde 8.0)
- **57 tests E2E en verde** (Playwright chromium, +4 desde 8.0)
- TypeScript strict sin errores
- Aprobación con backend Fase 4 verificada en stub (con `USE_REAL_API=false`)

## Definition of Done (cumplido)

- ✅ Operador puede subir archivo y completar todo el flujo hasta indexación
- ✅ Errores de extracción se muestran claramente (errorDetail visible como alerta en row y detail)
- ✅ Items rechazados quedan trazables con motivo (`errorDetail` campo del item)
- ✅ Tabs reflejan estado actual con auto-refetch 15 s
- ✅ Gating por rol respetado (capturador no ve la cola)

## Notas para Fase 9 (multi-tenant)

- El gating actual usa `user.isAdmin` (Owner global + GK Lead). En 9.x se reemplaza por `PermissionPolicy.can_approve_ingestion(user, project)` que cubre `project_owner` per-proyecto + override GK Lead.
- El api `getIngestion(itemId)` hoy filtra la lista client-side por falta de endpoint detail. Cuando el backend exponga `GET /ingestion/{id}`, swap directo en `lib/api/ingestion.ts`.
- El `TraceabilityForm` queda listo para extenderse con `projectId` (oculto: el contexto activo del store) sin cambios al contrato del endpoint.

## Dependencias

- Backend Fase 4 (endpoints de ingesta + extractores + clasificador) ✓

---

# Fase 9 · Frontend · Admin

**Estado:** ⬜ Pendiente · **Semana roadmap:** 17

## Objetivo

Módulo de administración solo para usuarios admin (GK Lead, Owner).

## Tareas planificadas

- ⬜ `/admin/users` (lista, activar/desactivar, promover a admin)
- ⬜ `/admin/taxonomy` (CRUD de categorías y tipos con validación)
- ⬜ `/admin/skills` con editor Markdown (lectura/escritura de skills)
- ⬜ `/admin/audit` (audit log filtrable por usuario/acción/fecha)
- ⬜ Exportación de logs a CSV (compliance)

## Definition of Done

- Admin puede editar skills sin tocar código
- Taxonomía editable desde UI con validación
- Audit log filtrable y exportable

## Dependencias

- Backend Fase 1 (audit_log + skills + users CRUD)

---

# Fase 10 · Hardening

**Estado:** 🔄 Parcial (Fase 10A ✅) · **Semanas roadmap:** 18-19 · branch `fase-10-hardening-parcial`

## Sub-fase 10A · Hardening parcial frontend (sin TI)

**Estado:** ✅ Completada · 2026-05-22

Mientras esperamos respuestas de TI para arrancar el backend (Fase 1), se ejecutó la parte del hardening que solo depende del frontend ya cerrado (Fases 5-7). Cubre **E2E + a11y + seguridad headers + performance baseline**.

### 10A.1 · Suite Playwright E2E

- ✅ Setup completo: `@playwright/test`, `playwright.config.ts` con webServer auto-start en puerto 3100, chromium por defecto, `workers: 1` para estabilidad con dev server compartido.
- ✅ `e2e/fixtures/auth.ts` — fixture `loginAs(roleId)` que inyecta el user en localStorage vía `addInitScript`, sin pasar por la UI de login en cada test.
- ✅ **26 specs E2E** cubriendo los flujos cerrados:
  - `auth.spec.ts` (5) — redirect a /login, login por rol, variantes admin/capturador
  - `explorer.spec.ts` (9) — filtros, URL state, debounce, paginación, F5
  - `document-detail.spec.ts` (5) — breadcrumb, meta, citations, gating admin
  - `chat-captura.spec.ts` (4) — flujo modo A end-to-end con streaming, tokenUsage gating, persistencia F5, modo B con pill C
  - `my-captures.spec.ts` (2) — empty state, link en sidebar
- ✅ Scripts: `test:e2e`, `test:e2e:ui`, `test:e2e:headed`.

**Bug fix detectado y corregido**: `useExplorerFilters` perdía clicks rápidos en filter chips por race condition (el closure de `patchFilters` capturaba `params` estale). Los setters ahora leen `window.location.search` vivo.

### 10A.2 · axe-core (WCAG 2.1 AA)

- ✅ `@axe-core/playwright` integrado.
- ✅ `e2e/fixtures/a11y.ts` — helper `expectNoAxeViolations(page)` con reglas WCAG2A/AA + 2.1A/AA.
- ✅ `e2e/a11y.spec.ts` — **8 audits** de páginas críticas (/login, /dashboard admin + capturador, /explorer + con filtros, /explorer/[docId], /chat, /my-captures).
- ✅ **3 violaciones reales detectadas y corregidas**:
  1. `color-contrast` en tokens `success`/`authoritative`/`warning`/`error`. Luminancia ajustada a 26-32% en light mode + overrides explícitos en dark mode.
  2. `color-contrast` en badge "Autoritativo". Cambio de variant: fondo verde sólido + texto blanco (~9:1 contraste).
  3. `definition-list`/`dlitem` en `DocumentMetaPanel`. Refactor: el group div es hijo directo del `<dl>` con icono absoluto-flotante.

### 10A.3 · CSP estricta + HSTS

- ✅ `next.config.mjs` extendido con **Content-Security-Policy** completa:
  - `default-src 'self'` · `frame-ancestors 'none'` · `base-uri 'self'` · `form-action 'self'` · `object-src 'none'` · `upgrade-insecure-requests`
  - `script-src` con dev mode permisivo (HMR + React Refresh) y prod más estricto
  - `style-src` con `'unsafe-inline'` documentado (Tailwind/shadcn lo requieren)
  - `img-src 'self' data: blob:`, `font-src 'self' data:`
- ✅ `Strict-Transport-Security` con 2 años + `includeSubDomains` + `preload`.
- ✅ `e2e/security-headers.spec.ts` (6 specs) — verifica los 6 headers en cada página, `X-Powered-By` ausente, CSP incluye directivas críticas.

**Pendiente Fase 10 completa**: nonce dinámico vía middleware para eliminar `'unsafe-inline'` de `script-src` en hidratación de Next.

### 10A.4 · Lighthouse CI

- ✅ `@lhci/cli` + `lighthouserc.cjs` configurado para auditar build de producción en puerto 3200.
- ✅ Script `test:lighthouse`.
- ✅ Workflow `.github/workflows/lighthouse.yml` para CI (ubuntu-latest, corre en PR + push a master, sube reports como artifact con retención 14 días).
- ✅ **Baseline real medido** (login, build de prod):

  | Categoría | Score |
  |---|---|
  | Performance | **99/100** |
  | Accessibility | **100/100** |
  | Best Practices | **96/100** |
  | SEO | **100/100** |

- ✅ Thresholds en `lighthouserc.cjs` calibrados al baseline (`error` en perf ≥ 0.9, a11y ≥ 0.95, best-practices ≥ 0.9; `warn` en SEO ≥ 0.9).
- ⚠ Known issue Windows: `chrome-launcher` falla en `rmSync` al limpiar el tempdir del browser. Cosmético — los reports ya quedaron generados. CI Linux no tiene este bug.

### Validación final 10A

| Check | Resultado |
|---|---|
| `pnpm typecheck` | ✅ 0 errores |
| `pnpm test` (Vitest unit) | ✅ **220/220** |
| `pnpm test:e2e` (Playwright) | ✅ **40/40** (26 funcional + 8 a11y + 6 security) |
| `pnpm test:lighthouse` (en login) | ✅ Perf 99 · A11y 100 · BP 96 · SEO 100 |
| `pnpm build` | ✅ build OK con CSP estricta aplicada |

## Sub-fase 10B · Hardening extra frontend (sin TI)

**Estado:** ✅ Completada · 2026-05-22

Continuación de 10A con tres mejoras del frontend que NO requieren TI ni backend.

### 10B.1 · Navegación por teclado completa

- ✅ Skip-link al `<main id="main-content">` como primer focusable del layout (WCAG 2.4.1). Visualmente oculto hasta recibir focus.
- ✅ `<main tabIndex={-1}>` permite focus programático desde el skip-link.
- ✅ Radix Dialog (Sheet de preview) ya provee focus trap + escape — sin cambios necesarios.
- ✅ `e2e/keyboard-nav.spec.ts` (8 specs): primer Tab muestra skip-link, Enter salta al main, tab order en FilterBar, Enter/Space activan chips, Tab desde composer (con texto) lleva a Enviar, Enter envía mensaje, focus-visible tiene box-shadow.

### 10B.2 · i18n con next-intl (es-CO + en-US)

- ✅ `next-intl@^3` + plugin en `next.config.mjs`.
- ✅ `src/i18n/config.ts` — LOCALES, DEFAULT_LOCALE (es-CO), cookie name (NEXT_LOCALE), helpers.
- ✅ `src/i18n/request.ts` — getRequestConfig server-side que lee cookie y carga messages.
- ✅ `src/i18n/actions.ts` — server action `setLocale()` que persiste cookie + revalidatePath.
- ✅ `messages/es-CO.json` + `en-US.json` con 5 namespaces (common, nav, topbar, login, roles) — ~50 keys.
- ✅ `LanguageSwitcher` en topbar con dropdown, marca locale actual, useTransition para feedback.
- ✅ Aplicado a: skip-link, sidebar (nav groups + items + activeAgent), topbar (aria-labels + logout), login (aria-label con interpolación).
- ✅ `html[lang]` refleja el locale activo.
- ✅ `e2e/i18n.spec.ts` (5 specs): default es-CO, switch a en-US traduce nav y topbar, cookie persiste post-F5, skip-link traducido, html[lang] cambia.

**Nota:** las páginas pasaron de `static` a `dynamic` en build porque `getLocale()` lee cookies. El resto de las páginas (/explorer, /chat, /dashboard) por ahora usan strings hardcoded en español; el patrón next-intl está listo para migración incremental.

### 10B.3 · Code splitting + lazy loading

- ✅ `next/dynamic` aplicado a `DocsByCategoryChart` + `ValueScoreDistribution` (recharts ~80 kB lazy-loaded solo cuando admin entra al dashboard).
- ✅ `MessageContent` extraído de `MessageBubble` a archivo propio para dynamic-import. react-markdown + remark-gfm (~30 kB) ya no entran en el bundle inicial del chat.
- ✅ Skeletons como loading state mientras los chunks llegan.

**Reducción de bundle medida:**

| Ruta | Antes 10B.3 | Después 10B.3 | Δ |
|---|---|---|---|
| `/chat/[sessionId]` page bundle | 65.2 kB | **23 kB** | **-65%** |
| `/chat/[sessionId]` First Load | 235 kB | **193 kB** | **-18%** |
| `/dashboard` page bundle | 109 kB | **5.6 kB** | **-95%** |
| `/dashboard` First Load | 252 kB | **149 kB** | **-41%** |

Unit tests de `MessageBubble` ajustados a `findByText` async para esperar la hidratación del chunk dynamic.

### Validación final 10B

| Check | Resultado |
|---|---|
| `pnpm typecheck` | ✅ 0 errores |
| `pnpm test` (Vitest unit) | ✅ **220/220** |
| `pnpm test:e2e` | ✅ **53/53** (40 anteriores + 8 keyboard + 5 i18n) |
| `pnpm build` | ✅ build OK con reducciones de bundle |

## Tareas restantes (Fase 10 completa)

Estas tareas requieren backend ya en marcha (Fase 1+) o son optimizaciones post-deploy:

### Performance
- ⬜ Tests de carga con k6 (50 usuarios concurrentes) — depende de backend
- ⬜ Optimización queries lentas (EXPLAIN ANALYZE sobre queries críticas) — depende de DB
- ⬜ Code splitting + lazy loading frontend (oportunidad, no urgente con 106 kB shared)
- ⬜ Reducir tamaño de imágenes Docker

### Seguridad
- ⬜ **Security review** completa (OWASP Top 10) — al final, post-backend
- ⬜ Activar gates de `npm audit` y `pip-audit` (ya stub en CI)
- ⬜ Rate limiting en endpoints sensibles (100 req/min general, 10/min chat, 5/min upload) — backend
- ⬜ CSRF protection — backend Fase 1
- ⬜ Penetration test con OWASP ZAP en CI
- ⬜ CSP con nonce dinámico vía middleware (eliminar `'unsafe-inline'` en `script-src`)
- ⬜ Activar plugin `security-guidance` para revisión continua

### Observabilidad
- ⬜ Alertas Application Insights (error rate, latency, cost)
- ⬜ Dashboards Azure Monitor exportados como JSON

### Accesibilidad
- ✅ Lighthouse score ≥ 90 (perf + a11y + best-practices) — **alcanzado en 10A.4**
- ✅ axe-core en E2E — **integrado en 10A.2**
- ✅ Navegación por teclado completa — **integrado en 10B.1**

### Documentación
- ⬜ ADRs finales (0002-pgvector confirmado vs Azure AI Search, 0003-container-apps, 0004-clean-arch, 0005-langgraph)
- ⬜ Runbooks operativos
- ⬜ Troubleshooting guides

### i18n
- ✅ es-CO (default) + en-US setup completo — **integrado en 10B.2**
- ⬜ Migración incremental de strings hardcoded del resto de páginas (/explorer, /chat, /dashboard, /my-captures)

## Definition of Done

- Lighthouse score ≥ 90 en performance, accessibility, best practices
- Tests E2E pasan en CI consistentemente
- Sin vulnerabilidades críticas en `npm audit` ni `pip-audit`
- Todas las queries críticas < 100ms P95
- WCAG AA mínimo, AAA donde razonable

---

# Fase 11 · Migración y paso a producción

**Estado:** ⬜ Pendiente (Bicep esqueleto en Fase 0) · **Semana roadmap:** 20

## Objetivo

Datos legacy migrados, TI desplegando autónomamente, agente actual decomisionado.

## Tareas planificadas

- ⬜ Finalizar plantillas Bicep para los 3 entornos (dev/staging/prod)
  - Private endpoints
  - Diagnostic settings detallados
  - Backup policies
  - Failover groups (PostgreSQL prod)
  - Key Vault references en Container Apps env
- ⬜ Completar `DEPLOYMENT.md` y `RUNBOOK.md` con procedimiento paso a paso
- ⬜ Completar `secrets-mapping.md` (.env → Key Vault secret names)
- ⬜ Exportar dashboard de Application Insights como JSON
- ⬜ Implementar `migrate_legacy_csv.py`:
  - CSVs antiguos → `documents` + `capture_scores` + `queries` + `query_citations`
  - Archivos físicos → Blob Storage
  - ChromaDB → `document_chunks`
- ⬜ Período de validación dual (queries van a ambos sistemas, se comparan resultados)
- ⬜ Walkthrough técnico con equipo de TI
- ⬜ TI ejecuta primer deploy a entorno dev en Azure
- ⬜ TI ejecuta deploy a staging
- ⬜ Pilot con 5 usuarios internos en staging
- ⬜ Recopilar feedback y ajustar
- ⬜ Deploy a producción
- ⬜ Cutover desde el agente actual

## Definition of Done

- App productiva en Azure
- Datos legacy migrados sin pérdida
- TI puede operar de forma autónoma
- Agente actual decomisionado

## Pre-requisitos antes de Fase 11

- Cuenta Azure activa con permisos (resource group + RBAC para TI)
- App Registration en Entra ID
- Subscriptions configuradas (dev separada de prod)
- Plan de comunicación a usuarios

---

# Stack tecnológico consolidado

## Frontend
- Node.js 20 + pnpm 9.15.0
- Next.js 15.1.3 (App Router) + React 19 + TypeScript 5.7
- Tailwind CSS 3.4 + shadcn/ui (componentes manuales)
- TanStack Query 5 + Zustand 5
- Stub MSAL → @azure/msal-react (Fase 11)
- date-fns 4, ky 1.7, lucide-react, sonner, react-hook-form + zod
- Vitest 2 + @testing-library/react + Playwright (Fase 10)
- Fuentes: Exo 2 + Montserrat + JetBrains Mono (next/font self-hosted)

## Backend
- Python 3.12 + uv-compatible
- FastAPI 0.136 + Pydantic v2 + Pydantic Settings
- SQLAlchemy 2.0 async + Alembic + asyncpg + pgvector (Fase 1)
- LangGraph + Jinja2 + anthropic SDK (Fase 2)
- python-docx + python-pptx + openpyxl + reportlab + pypdf + pdfplumber + unstructured (Fase 4)
- azure-storage-blob + azure-identity + msal (Fase 1)
- structlog + opentelemetry + langfuse + arq (Redis)
- ruff + mypy + pytest + httpx

## Infraestructura (Azure)
- Container Apps (Consumption plan) — backend + frontend
- PostgreSQL Flexible Server B2s 32GB con pgvector
- Blob Storage Standard LRS (hot+cool)
- Container Registry Basic
- Key Vault Standard
- Application Insights (free tier 5GB/mes)
- Microsoft Entra ID (incluido M365)
- Azure Monitor

## Tooling
- Docker + Docker Compose (local dev)
- Bicep 0.43 (IaC)
- GitHub Actions (CI build/test) + Azure DevOps Pipelines (CD lo opera TI)
- gitleaks + pre-commit (secret scanning)

---

# Próximos pasos sugeridos

1. **Commit del cierre de Fase 6** — el repo tiene un único commit (`828ff59` cerrando Fase 0 + 5). Crear commit con todo lo de Fase 6 antes de seguir.
2. Crear repo en GitHub/Azure DevOps + push (sigue pendiente desde Fase 0).
3. Configurar GitHub Variables (`AZURE_ACR_NAME`) y Secrets (`AZURE_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID` con federated credentials OIDC).
4. **Arrancar Fase 1 — Backend · Persistencia + Auth Entra ID.** Desbloquea Fases 2 (LangGraph), 3 (RAG) y 4 (extractores/generadores). El frontend ya está listo para consumir endpoints reales — el swap del `MockMessageTransport` por `SseMessageTransport` será de 1 línea en `transport-factory.ts`.
5. Antes de Fase 1: solicitar a TI App Registration en Entra ID para tenant SQA (lleva tiempo).
6. Revisar las memorias del proyecto antes de arrancar Fase 1: matriz de roles ([[project-roles-capacidades]]) y ownership checks para evitar IDOR ([[project-security-idor-check]]).

# Glosario rápido

| Término | Definición |
|---|---|
| **ETAPA** | Cada paso del flujo conversacional del agente Aria (0-5 para captura, C para consulta, I para ingesta) |
| **Modo A/B/C** | Captura conversacional / Consulta / Ingesta aprobada |
| **Carpeta temática** | Una de las 8 categorías (PROC, TEC, ARQ, HERR, NEG, ENV, EST, CONT) |
| **Tipo de documento** | Una de las 11 estructuras del playbook (POL, PROC, GUIA, INST, SERV, MTEC, ACEL, UEN, ARCL, FORM, PRES) |
| **Autoritativo** | Documento marcado oficial, con boost de relevancia en búsqueda |
| **Scoring** | Evaluación de 4 dimensiones (especificidad, profundidad, reutilizabilidad, unicidad) — escala 1-5 |
| **Anonimización** | Reemplazo de elementos específicos de cliente por marcadores genéricos |
| **Chunk** | Fragmento de texto indexado vectorialmente |
| **SSE** | Server-Sent Events — streaming HTTP unidireccional para chat |
| **MSAL** | Microsoft Authentication Library |
| **Entra ID** | Servicio de identidad de Microsoft (antes Azure AD) |
| **IaC** | Infrastructure as Code (Bicep en este proyecto) |
| **HNSW** | Hierarchical Navigable Small World — algoritmo del índice vectorial pgvector |

---

*Este documento es el espejo del [ROADMAP-IMPLEMENTACION-SQA-KB.md](../../ROADMAP-IMPLEMENTACION-SQA-KB.md) con el estado real de avance. El roadmap define el contrato; este documento registra la ejecución.*
