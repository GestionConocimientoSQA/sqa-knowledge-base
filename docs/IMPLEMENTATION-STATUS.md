# Estado de implementación · SQA Knowledge Base

> **Última actualización:** 2026-05-19
> **Documento vivo** — se actualiza al cierre de cada fase.
> Fuente de verdad para `qué está hecho / en curso / pendiente`.

## Resumen ejecutivo

| Indicador | Valor |
|---|---|
| Timeline estimado total | 16-20 semanas |
| Fases totales | 12 (Fase 0 a Fase 11) |
| Fases completadas | **4** (Fase 0 + Fase 5 + Fase 6 + Fase 7) |
| Fase actual | **Fases 10A + 10B ✅** (hardening parcial + extra · branch `fase-10-hardening-extra`) |
| Próxima fase | Fase 1 — Backend (bloqueada por TI: App Registration en Entra ID + decisiones de stack) |
| Bloqueo externo | Fase 1 (backend) espera App Registration en Entra ID por TI |
| Stack productivo | Frontend Next.js 15 ✓ · Backend FastAPI esqueleto ✓ · Infra Bicep esqueleto ✓ |
| Deployable target | Azure (Container Apps, PostgreSQL Flexible Server, Blob, Key Vault, Entra ID, App Insights) |

## Tabla de fases

| Fase | Bloque | Semanas roadmap | Estado | Cobertura |
|---|---|---|---|---|
| 0 | Fundación (monorepo + infra + Azure) | 1 | ✅ Completada | 100% |
| 1 | Backend · Persistencia + Auth Entra ID | 2-3 | ⬜ Pendiente (bloqueada por TI: App Registration) | 0% |
| 2 | Backend · Agente LangGraph (ETAPAS) | 4-6 | ⬜ Pendiente | 0% |
| 3 | Backend · RAG vectorial | 7-8 | ⬜ Pendiente | 0% |
| 4 | Backend · Generación y extracción de docs | 9-10 | ⬜ Pendiente | 0% |
| **5** | **Frontend · Fundación (UI + auth stub)** | **11-12** | **✅ Completada** | **100%** |
| **6** | **Frontend · Chat streaming SSE (con mock-transport)** | **13-14** | **✅ Completada** | **100%** |
| **7** | **Frontend · Explorer + Dashboard interactivo** | **15** | **✅ Completada** | **100%** |
| 8 | Frontend · Cola de ingesta | 16 | ⬜ Pendiente | 0% |
| 9 | Frontend · Admin (usuarios, taxonomía, skills, audit) | 17 | ⬜ Pendiente | 0% |
| 10 | Hardening (perf + a11y + security review) | 18-19 | 🔄 Sub-fases 10A + 10B ✅ | E2E Playwright + axe a11y + CSP + Lighthouse CI + keyboard nav + i18n (es-CO/en-US) + code splitting; falta backend-side |
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
- ⬜ ADRs finales (0002-pgvector → Azure SQL/AI Search según TI, 0003-container-apps, 0004-clean-arch, 0005-langgraph)
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
