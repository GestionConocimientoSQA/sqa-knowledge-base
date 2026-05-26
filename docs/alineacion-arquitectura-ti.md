# Alineación con arquitectura de TI

> **Autor:** Andrés Altamiranda · GK Lead SQA
> **Fecha:** 2026-05-20
> **Estado:** Borrador para revisión con TI
> **Bloquea decisiones técnicas de:** Fase 1 (Backend persistencia), Fase 2 (Agente), Fase 3 (RAG), Fase 11 (Deploy)

## Contexto

TI publicó los lineamientos de arquitectura "Arquitectura base" del tenant SQA. Este documento contrasta esos lineamientos con el stack actual del proyecto SQA Knowledge Base (Fases 0, 5, 6, 7 ya entregadas) e identifica los cambios necesarios para alinear el proyecto al 100% antes de arrancar el backend (Fase 1).

**Stack actual** (de `project_stack_decisions` + [CLAUDE.md](../CLAUDE.md) + [infra/main.bicep](../infra/main.bicep)):
Next.js 15 (App Router + SSR) · FastAPI + Pydantic v2 · SQLAlchemy 2.0 async + PostgreSQL Flexible Server + pgvector · LangGraph + Anthropic SDK + Langfuse · Azure Container Apps + Key Vault + Blob + App Insights + Entra ID · Bicep IaC.

**Arquitectura base TI** (6 capas):

| Capa | Recursos |
|---|---|
| **Seguridad** | Azure Entra ID · Azure Key Vault · Front Door + WAF · HTTPS forzado |
| **Frontend** | Azure Static Web Apps · GitHub Actions · Código HTML/JS |
| **Backend** | Opción A (liviano): Azure Functions · Opción B (web completa): App Service o Container Apps · Azure Comm. Services |
| **AI Gateway** | LiteLLM (rate limiting + costos + logs) · Presidio (PII filter, si la app tiene BD propia) · Claude API |
| **Datos y Memoria** | Azure SQL Serverless (auditoría compartida) · Azure Blob Storage · Azure SQL Database (relacional) · Cosmos DB / Redis (flexible) |
| **Observabilidad** | Application Insights · LiteLLM Dashboard · Alertas automáticas |

---

## 1. Cuadro de alineación

| Capa | Hoy | TI dice | Estado | Acción |
|---|---|---|---|---|
| Identidad | Stub MSAL → Entra ID Fase 11 | Azure Entra ID | ✅ | Alineado |
| Secrets | Azure Key Vault | Azure Key Vault | ✅ | Alineado |
| Border security | (no incluido) | Front Door + WAF + HTTPS forzado | ➕ | Agregar módulo Bicep |
| **Frontend hosting** | Container Apps con Dockerfile multi-stage | Static Web Apps + GitHub Actions | 🔁 | **Cambio mayor** |
| **Frontend stack** | Next.js 15 (App Router, SSR, SSE) | "Código HTML/JS" | ⚠ | **Conflicto** (ver §2.1) |
| CI/CD frontend | GitHub Actions push a ACR | GitHub Actions auto-deploy a SWA | 🔁 | Adaptar workflow |
| Backend hosting | Container Apps | App Service o Container Apps | ✅ | Alineado (mantenemos Container Apps) |
| Backend lenguaje | Python + FastAPI | (no especificado) | ⚠ | Validar con TI |
| Email | (no definido) | Azure Communication Services | ➕ | Agregar (Fase 2/F11) |
| **AI Gateway** | Anthropic SDK directo | LiteLLM proxy | 🔁 | **Cambio mayor** |
| **PII filter** | Anonimizador propio (regex + LLM) en Fase 4 | Presidio antes de Claude | 🔁 | Reemplazar/integrar como callback de LiteLLM |
| Modelo | Claude (Anthropic) | Claude API vía LiteLLM | ✅ | Alineado |
| **DB relacional** | PostgreSQL Flexible Server | Azure SQL Database | 🔁🔁 | **Cambio mayor crítico** |
| **Vector store** | pgvector en mismo Postgres | (no mencionado) | ⚠ | **Sin equivalente nativo en SQL Server** (ver §2.2) |
| Audit log | Tabla `audit_log` en nuestra DB | Azure SQL Serverless compartida entre apps | 🔁 | Duplicar writes o migrar audit |
| Object storage | Azure Blob Storage | Azure Blob Storage | ✅ | Alineado |
| Cache / queue | Redis (arq workers) | Cosmos DB / Redis | ✅ | Alineado (Redis OK; Cosmos no aplica) |
| Observabilidad app | App Insights + structlog + OpenTelemetry | Application Insights | ✅ | Alineado |
| Observabilidad LLM | Langfuse | LiteLLM Dashboard | 🔁 | Reemplazar o coexistir |
| Alertas | Manual, no automatizado | Alertas automáticas (presupuesto/errores) | ➕ | Configurar en App Insights + LiteLLM |

Leyenda: ✅ alineado · ➕ agregar (sin conflicto) · 🔁 cambio · 🔁🔁 cambio mayor crítico · ⚠ conflicto/clarificación

---

## 2. Cambios mayores

### 2.1 🔴 Frontend: Container Apps + Next.js SSR → Static Web Apps

**Problema:** Next.js 15 con App Router que tenemos hoy usa **renderizado dinámico server-side** en algunas rutas. En el build de Fase 7 aparecen como `ƒ` (server-rendered on demand):

```
ƒ /chat/[sessionId]                    62.6 kB         233 kB
ƒ /explorer/[docId]                    7.21 kB         141 kB
```

Azure Static Web Apps con Next.js soporta solo:

- **Static export** (`output: "export"` en `next.config.mjs`) — perdemos rutas dinámicas server-side, layouts dinámicos, fetch en server components.
- **Hybrid mode con Functions API** — cada ruta dinámica se convierte en una Azure Function. Restricciones de tamaño, cold start, sin streaming SSE nativo.

**El streaming SSE del chat (Fase 6) es el bloqueante grande:** SWA no soporta conexiones SSE largas nativamente en su tier estándar. El SSE real (Fase 2) lo emitirá el backend, pero hoy el endpoint del transporte está pensado para ser proxyado desde el frontend.

**Opciones:**

- **A.** Negociar con TI mantener **Container Apps para el frontend** dado el SSE y el SSR.
- **B.** Refactorizar a **SPA pura** (Vite + React + React Router). Reescritura considerable; el código de UI se conserva pero pierde mucho del ecosistema Next.
- **C.** **Mover SSE al backend** (ya planeado) + dejar frontend en SWA como SPA estática que consume el backend con `output: "export"` o adapter de SWA. Esto es razonable y de hecho ya teníamos el SSE planificado en backend.

**Recomendación: opción C.** Cambio mediano:

1. `output: "export"` en `next.config.mjs`.
2. Las rutas `/chat/[sessionId]` y `/explorer/[docId]` pasan a `dynamicParams = false` + client-side routing — Next 15 lo soporta con client components que leen `useParams()`.
3. El SSE ya está en backend desde Fase 2 (`POST /sessions/{id}/messages` con `text/event-stream`).
4. Adaptar `build-and-push.yml` para deploy a SWA en lugar de ACR para frontend.

**Impacto:** ~1-1.5 semanas en Fase 11.

### 2.2 🔴 PostgreSQL + pgvector → Azure SQL Database

**Problema:** Azure SQL Database (SQL Server) no tiene equivalente nativo a pgvector. Hay un tipo `VECTOR` en preview reciente (Azure SQL Database `vector` type) pero con limitaciones:

- Max 1998 dimensiones (Cohere multilingual-v3 usa 1024, OK; otros embeddings de 3072 NO entrarían)
- Sin índice HNSW nativo — usa búsqueda exacta (lenta a gran escala)
- Feature preview, no GA

Esto rompe el plan de **Fase 3 (RAG vectorial)** con búsqueda P95 < 100ms sobre 10k chunks.

**Cambios concretos en el código si pasamos a SQL Server:**

- **Driver async**: `asyncpg` → `aioodbc` (con `pyodbc` y MS ODBC Driver 18)
- **SQLAlchemy dialect**: `postgresql+asyncpg` → `mssql+aioodbc`
- **Tipos**:
  - `JSONB` → `NVARCHAR(MAX)` con check de JSON, o el tipo `JSON` nativo (preview)
  - `UUID` → `UNIQUEIDENTIFIER` o `CHAR(36)`
  - `tsvector` (full-text) → SQL Server Full-Text Search (motor distinto, sintaxis distinta)
  - `vector` → Azure AI Search (ver abajo)
- **Migrations**: Alembic soporta mssql pero las migraciones de F1 (vistas materializadas para `mv_dashboard_stats`, índices GIN, extensions) se reescriben.
- **Compose local**: PostgreSQL+pgvector image → Azure SQL Edge linux container o SQL Server 2022 Express.
- **Sintaxis específica**: LIMIT/OFFSET → TOP / OFFSET FETCH; `||` concat → `+`; `RETURNING` → `OUTPUT`; arrays Postgres no existen → tablas auxiliares.

**Vector store separado — opciones:**

| Opción | Pros | Cons |
|---|---|---|
| **Azure AI Search** (recomendada) | Stack 100% Azure · GA · HNSW · híbrido (vector + BM25) integrado · escala managed | Costo fijo por SKU · separación lógica (los chunks viven en otro servicio) |
| Cosmos DB con vector search | Schema flexible · vectores y data juntos | Modelo de queries distinto (NoSQL) · costos por RU/s |
| pgvector externo (un único Postgres dedicado a vectores) | Mantenemos pgvector que ya conocemos | Desafía el lineamiento TI · contradice §2.2 |

**Recomendación: Azure SQL Database + Azure AI Search.** Mantenemos SQL Server para todo lo relacional (users, sessions, messages, documents, queries, ingestion_items, audit_log) + **Azure AI Search** como vector store de chunks. Esto está totalmente dentro del catálogo Azure de TI.

**Modelo lógico:**

```
Azure SQL Database
├─ users, sessions, messages
├─ documents, capture_scores
├─ queries, query_citations
├─ ingestion_items, drafts
├─ skills, audit_log
└─ mv_dashboard_stats (vista materializada)

Azure AI Search index "kb-chunks"
├─ id (key)
├─ document_id (filter)
├─ category, doc_type (filter, facet)
├─ is_authoritative (boost)
├─ content (full-text)
└─ embedding (vector, 1024 dim, HNSW)
```

El retriever Python (Fase 3) habla con AI Search vía REST/SDK. Cuando se cita un chunk, el `document_id` resuelve a la fila en Azure SQL.

**Impacto:** 2-3 semanas en Fase 1 (afecta TODA la capa de persistencia).

### 2.3 🟡 Anthropic SDK directo → LiteLLM proxy

**Cambio:** el cliente del backend deja de hablar con `api.anthropic.com` y habla con LiteLLM. LiteLLM provee:

- Unified API across providers (Anthropic, OpenAI, Azure OpenAI, Bedrock)
- Rate limiting per-user / per-tenant
- Cost tracking automático (response incluye `usage` + `cost_usd`)
- Fallbacks (si Anthropic está caído, fallback a OpenAI con prompt similar)
- Prompt caching (se mantiene)
- Callbacks pre/post call (acá entra Presidio — §2.4)

**Impacto en código backend:**

```python
# Antes
import anthropic
client = anthropic.AsyncAnthropic(api_key=...)
response = await client.messages.create(...)

# Después
import litellm
response = await litellm.acompletion(
    model="claude-sonnet-4-6",
    api_base="https://litellm.sqa.internal",
    api_key=...,  # token interno LiteLLM, no Anthropic
    messages=[...],
    metadata={"trace_id": ..., "user_oid": ...},
)
```

**Configuración a definir con TI:**
- LiteLLM URL del servicio en el tenant
- Auth mechanism (token virtual por app, API key por servicio)
- Rate limits asignados a SQA Knowledge Base
- Modelos disponibles (Sonnet 4.6 default, Haiku para clasificación, Opus para razonamiento profundo)

**Pregunta para TI:** ¿LiteLLM lo provee TI como servicio managed compartido entre apps, o cada app lo despliega en su propio Container App?

**Impacto:** 3-5 días en Fase 2.

### 2.4 🟡 Presidio (PII filter) antes de Claude

**Nuevo componente** que detecta y enmascara PII antes de enviar a Claude. Se integra naturalmente como **callback pre-call de LiteLLM**.

```
Backend → LiteLLM (callback Presidio) → Claude API
                    ↓
              [PII detectado]
              "Mi nombre es Juan Pérez, DNI 12345678"
                    ↓
              "Mi nombre es <PERSON_1>, DNI <DOC_ID>"
                    ↓
              enviado a Claude
```

**Decisión:** mantener nuestro **anonimizador del workflow del agente** (Fase 4, donde el usuario decide qué anonimizar en el documento generado — es parte del producto) + **agregar Presidio como capa adicional automática** antes de cada llamada a Claude (defensa en profundidad, garantía técnica de que ningún PII llega al modelo).

**Pregunta para TI:** ¿Presidio servicio managed o cada app lo despliega? ¿Se configura como callback obligatorio del LiteLLM compartido?

**Impacto:** 2-3 días en Fase 2/F4.

### 2.5 🟡 Audit log centralizado en Azure SQL Serverless

**TI dice:** "auditoría compartida entre todos los artefactos" → una Azure SQL Serverless central donde todas las apps del tenant publican audit events.

**Pregunta a TI:** ¿el audit log de la app debe vivir SOLO en la Azure SQL Serverless central, o pueden coexistir nuestra tabla `audit_log` interna + un write paralelo al log central?

**Recomendación:** **dual-write** — mantenemos nuestra tabla `audit_log` para queries internas de la app (eficiencia + control de schema + queries por usuario/documento) + **publicamos eventos al log centralizado por callback async** (sin bloquear el path principal).

**Schema mínimo del log central** (a confirmar con TI):
```
app_id (string)         "sqa-kb"
timestamp (datetime)
actor_oid (string)
event_type (string)     "session.created" | "document.indexed" | "taxonomy.changed"
resource_id (string)
metadata (json)
```

**Impacto:** 1-2 días en Fase 1.

---

## 3. Cambios menores

### 3.1 ➕ Front Door + WAF

Módulo Bicep nuevo en `infra/modules/front-door.bicep` (Fase 11):

- Front Door Standard SKU (suficiente para nuestro tráfico)
- WAF policy con managed ruleset (OWASP CRS 3.2)
- Custom rules: rate limiting en `/api/*`, geo-block opcional
- Apuntar al Container App del frontend
- Configurar custom domain SQA (cuando TI lo defina)

**Impacto:** 1-2 días en Fase 11.

### 3.2 ➕ Azure Communication Services

Para notificaciones por email (Fase 2 — alertas a Owners de carpeta cuando aparezca contenido relevante o gaps):

- Recurso ACS + Email Communication Service
- Sender address: `noreply-sqa-kb@sqa.co` (o el que TI prefiera)
- Cliente Python: `azure-communication-email`
- Templates HTML en `apps/backend/src/sqa_kb/notifications/templates/`

**Impacto:** 1 día en Fase 2/F11.

### 3.3 ➕ Alertas automáticas

Rules de App Insights (Fase 10/F11):

| Condición | Acción |
|---|---|
| Error rate > 5% en 5 min | Alerta a Slack/Email |
| P95 latency `/sessions/{id}/messages` > 5s | Alerta |
| Budget App Insights mensual > 80% | Notificación |
| `cost_usd` acumulado del día > umbral | Notificación |

Plus alertas de LiteLLM Dashboard (cost overrun, rate limit hit).

**Impacto:** 1 día en Fase 10.

### 3.4 🔁 Observabilidad LLM: ¿Langfuse o LiteLLM Dashboard?

TI menciona explícitamente **LiteLLM Dashboard** para "tokens consumidos, costos y latencia de Claude". Tenemos dos caminos:

- **Reemplazar Langfuse por LiteLLM Dashboard** — alineado al lineamiento, menos componentes que mantener.
- **Coexistir** — Langfuse para tracing detallado del agente (multi-step LangGraph) + LiteLLM para metrics de gateway.

**Recomendación:** **reemplazar Langfuse por LiteLLM Dashboard** + usar **OpenTelemetry → App Insights** para tracing de los nodos LangGraph (ya estaba en el plan). Reducir el número de servicios externos.

---

## 4. Preguntas para TI

Estas preguntas necesitan respuesta **antes** o **en paralelo** al pedido de Fase 1 ([docs/ti-requirements-fase-1.md](./ti-requirements-fase-1.md)):

| # | Pregunta | Impacto |
|---|---|---|
| 1 | **Frontend SSR/SSE**: ¿podemos mantener Container Apps para el frontend (Next.js con streaming SSE del chat) o exige Static Web Apps? Si SWA, ¿aceptan que el frontend sea SPA pura sin SSR? | Bloquea Fase 11 |
| 2 | **Vector search**: ¿usamos **Azure AI Search** para vectores (alineado al stack Azure) o consideran excepción con PostgreSQL+pgvector dado que es el stack natural para RAG? | Bloquea Fase 1 + Fase 3 |
| 3 | **LiteLLM**: ¿servicio managed por TI o lo deployamos en Container App propio? ¿Endpoint compartido entre apps? ¿Cómo se autentica cada app? | Bloquea Fase 2 |
| 4 | **Presidio**: ¿servicio compartido o cada app lo despliega? ¿Se configura como callback obligatorio del LiteLLM compartido? | Fase 2/F4 |
| 5 | **Audit log central**: ¿tabla central única en Azure SQL Serverless o dual-write desde cada app (manteniendo audit local + log central)? ¿Cuál es el schema esperado? | Fase 1 |
| 6 | **Backend lenguaje**: el diagrama no menciona Python — ¿hay restricción? ¿prefieren .NET o Node? (Asumimos Python+FastAPI por el ecosistema LangGraph + pdfplumber + python-docx) | Bloquea TODO el backend |
| 7 | **Vinculo Front Door**: ¿hay un Front Door del tenant compartido al cual nos vinculamos, o creamos uno propio para SQA-KB? | Fase 11 |
| 8 | **Conditional Access** (ya en [docs/ti-requirements-fase-1.md §3](./ti-requirements-fase-1.md)) | Fase 1 |

---

## 5. Trabajo total estimado para alinear

| Cambio | Esfuerzo | Cuándo | Riesgo |
|---|---|---|---|
| Front Door + WAF (Bicep) | 1-2 días | Fase 11 | Bajo |
| Azure Comm. Services | 1 día | Fase 2/F11 | Bajo |
| Alertas automáticas | 1 día | Fase 10/F11 | Bajo |
| LiteLLM gateway integration | 3-5 días | **Fase 2** | Medio (depende de cómo TI lo provea) |
| Presidio callback | 2-3 días | Fase 2/F4 | Bajo |
| Audit log dual-write | 1-2 días | Fase 1 | Bajo |
| Langfuse → LiteLLM Dashboard | 1 día | Fase 2 | Bajo |
| **PostgreSQL → Azure SQL + AI Search** | **2-3 semanas** | **Fase 1** | **Alto** — afecta TODA la persistencia |
| **Frontend SSR → SPA en SWA** (si TI exige) | **1-1.5 semanas** | Fase 11 | Medio |

**Total adicional sobre el ROADMAP original:** ~3-5 semanas, concentradas en Fase 1 (DB) y Fase 11 (deploy).

**Lo crítico** es resolver el item de **DB ANTES de arrancar Fase 1**, porque toda la capa de persistencia (SQLAlchemy models, repositorios, migrations, vistas) depende de la decisión.

---

## 6. Próximos pasos

1. ✅ **Documento creado** (este archivo).
2. ⬜ **Reunión técnica con TI** para responder las 8 preguntas de §4.
3. ⬜ **Actualizar [ROADMAP-IMPLEMENTACION-SQA-KB.md](../../ROADMAP-IMPLEMENTACION-SQA-KB.md)** con las decisiones finales.
4. ⬜ **Actualizar [docs/architecture/overview.md](./architecture/overview.md)** con el stack ajustado.
5. ⬜ **Actualizar Bicep `infra/`**:
   - Reemplazar `modules/postgres.bicep` por `modules/azure-sql.bicep`
   - Agregar `modules/ai-search.bicep`
   - Agregar `modules/front-door.bicep`
   - Agregar `modules/comm-services.bicep`
   - (Opcional) `modules/litellm.bicep` si lo deployamos nosotros
6. ⬜ **Decidir Estado de Fase 1**: si DB queda definida pre-arranque, podemos avanzar con el schema en Azure SQL en vez de PostgreSQL.

---

## Anexos

- [docs/ti-requirements-fase-1.md](./ti-requirements-fase-1.md) — pedido formal a TI con provisioning de Entra ID + Azure resources
- [infra/README.md](../infra/README.md) — contrato con TI + naming convention
- [ROADMAP-IMPLEMENTACION-SQA-KB.md](../../ROADMAP-IMPLEMENTACION-SQA-KB.md) — plan completo de 12 fases (en raíz del workspace)
- [docs/IMPLEMENTATION-STATUS.md](./IMPLEMENTATION-STATUS.md) — estado de avance real

— Andrés Altamiranda · andres.altamiranda@sqasa.co
