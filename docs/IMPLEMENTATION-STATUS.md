# Estado de implementación · SQA Knowledge Base

> **Última actualización:** 2026-05-19
> **Documento vivo** — se actualiza al cierre de cada fase.
> Fuente de verdad para `qué está hecho / en curso / pendiente`.

## Resumen ejecutivo

| Indicador | Valor |
|---|---|
| Timeline estimado total | 16-20 semanas |
| Fases totales | 12 (Fase 0 a Fase 11) |
| Fases completadas | **2** (Fase 0 + Fase 5) |
| Fase actual | — (en pausa entre fases) |
| Próxima fase | Fase 1 — Backend: Persistencia y Auth |
| Stack productivo | Frontend Next.js 15 ✓ · Backend FastAPI esqueleto ✓ · Infra Bicep esqueleto ✓ |
| Deployable target | Azure (Container Apps, PostgreSQL Flexible Server, Blob, Key Vault, Entra ID, App Insights) |

## Tabla de fases

| Fase | Bloque | Semanas roadmap | Estado | Cobertura |
|---|---|---|---|---|
| 0 | Fundación (monorepo + infra + Azure) | 1 | ✅ Completada | 100% |
| 1 | Backend · Persistencia + Auth Entra ID | 2-3 | ⬜ Pendiente | 0% |
| 2 | Backend · Agente LangGraph (ETAPAS) | 4-6 | ⬜ Pendiente | 0% |
| 3 | Backend · RAG vectorial | 7-8 | ⬜ Pendiente | 0% |
| 4 | Backend · Generación y extracción de docs | 9-10 | ⬜ Pendiente | 0% |
| **5** | **Frontend · Fundación (UI + auth stub)** | **11-12** | **✅ Completada** | **100%** |
| 6 | Frontend · Chat streaming SSE | 13-14 | ⬜ Pendiente | 0% |
| 7 | Frontend · Explorer + Dashboard interactivo | 15 | ⬜ Pendiente | 0% (esqueleto en Fase 5) |
| 8 | Frontend · Cola de ingesta | 16 | ⬜ Pendiente | 0% |
| 9 | Frontend · Admin (usuarios, taxonomía, skills, audit) | 17 | ⬜ Pendiente | 0% |
| 10 | Hardening (perf + a11y + security review) | 18-19 | ⬜ Pendiente | parcial (security headers, gitleaks, audits stubs) |
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

**Estado:** ⬜ Pendiente · **Semanas roadmap:** 2-3

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

**Estado:** ⬜ Pendiente · **Semanas roadmap:** 4-6

## Objetivo

Lógica del agente Aria implementada como máquina de estados con LangGraph. Las 3 ETAPAS principales (A captura, B consulta, C ingesta) corren end-to-end.

## Tareas planificadas

- ⬜ Schema de estado del agente (`AgentState` Pydantic)
- ⬜ LangGraph principal con nodos + edges + conditional routing
- ⬜ Checkpointer custom que persiste en PostgreSQL (`sessions.agent_state` JSONB)
- ⬜ Implementar cada ETAPA como módulo separado:
  - ETAPA 0 — `welcome.py` (presentación + selección de modo)
  - ETAPA 1 — `identification.py` (identificación + búsqueda KB)
  - ETAPA 2 — `free_capture.py` (acumulación libre)
  - ETAPA 3 — `deep_dive.py` (preguntas dirigidas por tipo de doc)
  - ETAPA 4 — `validation.py` (resumen estructurado + confirmación)
  - ETAPA 5 — `generation.py` (generación + scoring + indexación)
  - ETAPA C — `consultation.py` (modo B, sin captura)
  - ETAPA I — `ingestion.py` (modo C, workflow de aprobación)
- ⬜ Sistema de plantillas Jinja2 para prompts
- ⬜ Skills loader (lee skills desde DB, inyecta en system prompts)
- ⬜ Tools del agente: `search_kb`, `classify_topic`, `score_capture`, `anonymize`
- ⬜ Anthropic client con streaming async (Sonnet 4.6 default, Haiku para clasificación, Opus para razonamiento profundo)
- ⬜ Prompt caching para skills + system prompts (cache hit > 80%)
- ⬜ Cost tracker (tokens entrada/salida + USD por mensaje, almacenado en `messages.cost_usd`)
- ⬜ Endpoints:
  - `POST /sessions` (crea sesión nueva, devuelve ID)
  - `POST /sessions/{id}/messages` con **streaming SSE** (event types definidos en §15.2)
  - `GET /sessions` (lista del usuario, paginado)
  - `POST /sessions/{id}/pause` y `/resume`
- ⬜ Tests de integración para los 3 flujos completos

## Definition of Done

- Las 3 ETAPAS principales corren E2E vía API
- Sesiones pausa/reanuda sin pérdida de estado
- Streaming SSE funciona desde curl/httpx
- Cost tracker registra correctamente tokens y costo por mensaje
- Tests de integración cubren happy paths de los 3 modos
- Frontend Fase 6 puede consumir el streaming sin cambios al contrato

---

# Fase 3 · Backend · RAG vectorial

**Estado:** ⬜ Pendiente · **Semanas roadmap:** 7-8

## Objetivo

Indexación de documentos + búsqueda semántica con boost de autoritativos. Latencia P95 < 100 ms con 10k chunks.

## Tareas planificadas

- ⬜ Chunker con estrategias por tipo de documento (semantic chunking)
- ⬜ Integrar modelo de embeddings (decisión: Cohere multilingual-v3 vía API)
- ⬜ Embedder con batching para reducir latencia (batch=100)
- ⬜ Retriever con query parametrizada (categoría, autoritativo, top-k)
- ⬜ Boost de autoritativos en la query SQL (`is_authoritative = true` con multiplicador)
- ⬜ Hybrid search (vector + full-text con `tsvector`)
- ⬜ Opcional: re-ranking con cross-encoder
- ⬜ Worker `document_indexer` (arq + Redis)
- ⬜ Script `reindex_all.py` para batch
- ⬜ Endpoints:
  - `POST /queries` (consulta directa sin sesión, devuelve top-k con citaciones)
  - `GET /documents/search` con filtros
- ⬜ Métricas: latencia P50/P95, recall en test set sintético

## Definition of Done

- Búsqueda vectorial responde < 100ms P95 con 10k chunks
- Boost de autoritativos aplicado correctamente
- Test set sintético: precisión@5 ≥ 0.85
- Workers procesan asíncronamente sin bloquear API

---

# Fase 4 · Backend · Generación y extracción de documentos

**Estado:** ⬜ Pendiente · **Semanas roadmap:** 9-10

## Objetivo

Capacidad completa de generar y extraer todos los formatos soportados (11 tipos de documento × 6 formatos).

## Tareas planificadas

- ⬜ Generadores con branding SQA aplicado:
  - `DocxGenerator` (python-docx) — POL, PROC, INST, MTEC, etc.
  - `PptxGenerator` (python-pptx) — PRES
  - `XlsxGenerator` (openpyxl) — FORM
  - `PdfGenerator` (reportlab + conversión desde docx)
  - `MarkdownGenerator`
- ⬜ Plantillas base `.docx`/`.pptx` con placeholders y branding SQA (logos, colores, fuentes Exo 2 / Montserrat)
- ⬜ Extractores:
  - `DocxExtractor` (python-docx)
  - `PptxExtractor` (python-pptx)
  - `PdfExtractor` (pdfplumber)
  - `XlsxExtractor` (openpyxl)
- ⬜ Dispatcher que elige extractor por extensión
- ⬜ Anonimizador con reglas configurables (regex + LLM-fallback)
- ⬜ Filename builder (`[TIPO]-[tema]-[YYYY-MM-DD].ext`)
- ⬜ Endpoints de ingesta:
  - `POST /ingestion` (upload de archivo a Blob)
  - `POST /ingestion/{id}/classify` (extrae + clasifica)
  - `POST /ingestion/{id}/approve` (con metadata de trazabilidad)
  - `GET /ingestion` (lista filtrable por status)
- ⬜ Worker `ingestion_processor`
- ⬜ Tests con archivos de prueba reales para cada formato

## Definition of Done

- Generación de los 11 tipos produce archivos válidos abriendo en MS Office
- Extracción de los 6 formatos soportados produce texto + estructura
- Anonimización detecta y reemplaza patrones conocidos
- Branding SQA aplicado consistentemente en PPTX y DOCX

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

**Estado:** ⬜ Pendiente · **Semanas roadmap:** 13-14 · **Es la siguiente a abordar**

## Objetivo

Experiencia de chat completa con streaming SSE, mode selector A/B/C, attachments, stage indicator del agente, scoring en vivo.

## Tareas planificadas

- ⬜ Página selección de modo (cards conceptuales A/B/C con descripciones)
- ⬜ Página chat por sesión `/chat/[sessionId]`
- ⬜ Componente `ChatWindow` con scroll virtualizado
- ⬜ `MessageBubble` con render Markdown (react-markdown + remark-gfm)
- ⬜ `StreamingMessage` con efecto typewriter
- ⬜ Hook `use-chat-stream` (consume SSE del backend `POST /sessions/{id}/messages`)
- ⬜ Manejo de eventos SSE: `message-start`, `stage-change`, `classification`, `text-delta`, `citation`, `scoring`, `document-generated`, `error`, `ping`
- ⬜ Reconexión con `Last-Event-ID` (eventos persistidos 1h en Redis)
- ⬜ `AttachmentUploader` (drag & drop multi-file → Blob via presigned URL)
- ⬜ `StageIndicator` (visualiza ETAPA actual con stepper animado)
- ⬜ `ClassificationCard` (muestra carpeta + tipo sugeridos con confianza)
- ⬜ Lista de sesiones en sidebar con search/filtros
- ⬜ Pausar/reanudar sesión sin pérdida de estado
- ⬜ Preview inline de documentos generados (`DocxViewer`, `PdfViewer`)
- ⬜ Tests E2E del flujo completo de captura

## Definition of Done

- Usuario puede ejecutar flujo completo de captura desde UI
- Streaming es fluido sin pestañeos (60fps)
- Sesiones se pueden pausar y retomar
- Attachments se cargan a Blob Storage exitosamente
- Stage indicator refleja correctamente el progreso

## Dependencias

- **Backend Fase 2 implementado** (streaming SSE + sesiones funcionales) — bloqueante

## Estrategia recomendada

Como la Fase 6 depende del backend (Fase 2), hay dos rutas:

1. **Esperar a backend** — implementar Fase 1+2 antes de Fase 6.
2. **Mock SSE simulado** — implementar Fase 6 con un generator local que simula los eventos del agente (`apps/frontend/src/lib/streaming/mock-sse.ts`). Permite validar UX sin backend. Cuando esté listo, solo se cambia la URL del EventSource.

**Recomendación:** opción 2 — paralelizable y desbloquea validación de UX con stakeholders.

---

# Fase 7 · Frontend · Explorer y Dashboard

**Estado:** ⬜ Pendiente (esqueleto creado en Fase 5) · **Semana roadmap:** 15

## Objetivo

Explorador de conocimiento con filtros + dashboard interactivo de métricas para GK Lead.

## Tareas planificadas

- ⬜ `/explorer` con filtros (categoría, tipo, origen, autoritativo, fecha)
- ⬜ Barra de búsqueda con debounce
- ⬜ `DocumentCard` con badges (scoring, autoritativo, anonimizado)
- ⬜ `/explorer/[docId]` con preview + metadata + citaciones recibidas
- ⬜ `/dashboard` enriquecido:
  - StatCards (ya existen Fase 5)
  - `DocsByCategoryChart` (recharts pie)
  - `ValueScoreDistribution` (recharts bar)
  - `RecentActivity` feed
  - `HotTopics` (consultas más frecuentes + gaps)
- ⬜ `/my-captures` (documentos del usuario actual)
- ⬜ Filtros con URL state (compartible)
- ⬜ Auto-refresh cada 5 min con TanStack Query

## Definition of Done

- Filtros funcionan con URL state compartible
- Dashboard se refresca automáticamente cada 5 min
- Preview de documentos funciona inline sin descargar
- Charts responsive y accesibles

## Dependencias

- Backend Fase 1 (endpoints `GET /documents/search` con filtros)
- Backend Fase 3 (búsqueda vectorial para search-as-you-type opcional)

---

# Fase 8 · Frontend · Cola de ingesta

**Estado:** ⬜ Pendiente · **Semana roadmap:** 16

## Objetivo

UI completa para el flujo de ingesta de documentación aprobada (Modo C).

## Tareas planificadas

- ⬜ `/ingestion` con tabs por status (pending, in_review, completed, rejected)
- ⬜ `UploadZone` con drag & drop multi-file
- ⬜ `IngestionQueue` con acciones (clasificar, aprobar, rechazar)
- ⬜ `/ingestion/[itemId]` con preview + clasificación + `TraceabilityForm`
- ⬜ `TraceabilityForm` (aprobador, fecha, fuente, versión)
- ⬜ Feedback visual durante extracción y indexación (progress bar)
- ⬜ Conflict detection (mostrar si ya existe un doc similar)

## Definition of Done

- Operador puede subir archivo y completar todo el flujo hasta indexación
- Errores de extracción se muestran claramente
- Items rechazados quedan trazables con motivo

## Dependencias

- Backend Fase 4 (endpoints de ingesta + extractores + clasificador)

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

**Estado:** ⬜ Pendiente · **Semanas roadmap:** 18-19

## Objetivo

La app está lista para producción. Performance, accesibilidad, seguridad, observabilidad, i18n.

## Tareas planificadas

### Performance
- ⬜ Suite completa de tests E2E con Playwright (3 modos)
- ⬜ Tests de carga con k6 (50 usuarios concurrentes)
- ⬜ Optimización queries lentas (EXPLAIN ANALYZE sobre queries críticas)
- ⬜ Code splitting + lazy loading en frontend
- ⬜ Reducir tamaño de imágenes Docker

### Seguridad
- ⬜ **Security review** completa (OWASP Top 10)
- ⬜ Activar gates de `npm audit` y `pip-audit` (ya stub en CI)
- ⬜ Rate limiting en endpoints sensibles (100 req/min general, 10/min chat, 5/min upload)
- ⬜ CSRF protection
- ⬜ Content Security Policy estricta
- ⬜ Penetration test con OWASP ZAP en CI
- ⬜ Activar plugin `security-guidance` para revisión continua

### Observabilidad
- ⬜ Alertas Application Insights (error rate, latency, cost)
- ⬜ Dashboards Azure Monitor exportados como JSON

### Accesibilidad
- ⬜ Lighthouse score ≥ 90 (performance + accessibility + best practices)
- ⬜ axe-core en E2E
- ⬜ Navegación por teclado completa

### Documentación
- ⬜ ADRs finales (0002-pgvector, 0003-container-apps, 0004-clean-arch, 0005-langgraph)
- ⬜ Runbooks operativos
- ⬜ Troubleshooting guides

### i18n
- ⬜ es-CO (default) + en-US si aplica

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

1. **Commit inicial** del repo (`git add . && git commit -m "chore: bootstrap monorepo + phase 0 + phase 5 frontend"`)
2. Crear repo en GitHub/Azure DevOps + push
3. Configurar GitHub Variables (`AZURE_ACR_NAME`) y Secrets (`AZURE_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID` con federated credentials OIDC)
4. **Decisión:** arrancar Fase 1 (backend persistencia + auth) o Fase 6 con SSE mockeado en paralelo
5. Si Fase 1: solicitar a TI App Registration en Entra ID para tenant SQA

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
