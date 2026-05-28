# ADR 0009 · Multi-tenant projects (conocimiento por proyecto)

- **Estado:** aceptado
- **Fecha:** 2026-05-28
- **Decisor:** Andrés Altamiranda (GK Lead, único dev)
- **Fase asociada:** Fase 9 — Frontend Admin + Backend multi-tenant

## Contexto

Hasta Fase 8 el KB es **mono-tenant**: existe una sola base de conocimiento
compartida, todos los usuarios autenticados acceden a todos los documentos,
y los roles (`capturador`, `owner`, `gklead`) son globales. Funciona para
SQA-interno, pero no escala al modelo de negocio real: SQA es una empresa
de testing como servicio que opera con **múltiples clientes/proyectos en
paralelo** (telco, banca, retail, etc.), cada uno con su propia jerga,
regulación, taxonomía y stakeholders.

Necesitamos que cada proyecto tenga su **propia base de conocimiento aislada**,
con un administrador designado por GK, capaz de gobernar miembros, taxonomía
y carga inicial de contexto del cliente, sin que las consultas crucen líneas
entre proyectos. Al mismo tiempo GK debe retener una vista transversal y un
"proyecto raíz" donde guarda conocimiento aplicable a toda la organización.

Este ADR fija el modelo arquitectónico y de roles antes de empezar a escribir
código. Reemplaza el modelo de 3 roles globales por uno de **dos ejes
ortogonales** (rol global × rol per-proyecto).

---

## Decisión

### D1. Aislamiento entre proyectos — *row-level scoping*

Cada tabla con datos vinculados a conocimiento gana una columna
`project_id UUID NOT NULL` con FK a `projects(id)`. Las queries de aplicación
filtran obligatoriamente por `project_id` en el service layer.

```
projects(id, slug, name, description, owner_oid, created_at, archived_at)
project_members(project_id, user_oid, role, added_at)
documents(..., project_id)              -- existente, columna nueva
document_chunks(..., project_id)        -- existente, columna nueva
sessions(..., project_id)               -- existente, columna nueva
queries(..., project_id)                -- existente, columna nueva
ingestion_items(..., project_id)        -- existente, columna nueva
```

No usamos **schema-per-project** (operacionalmente costoso, migraciones × N
proyectos, complica connection pooling) ni **DB-per-project** (overkill, costo
Azure inviable a la escala SQA). PostgreSQL RLS (row-level security) queda
como hardening opcional para Fase 11 si TI lo pide; por ahora la defensa es
exclusivamente en el service layer + tests de aislamiento explícitos.

### D2. Modelo de roles — dos ejes ortogonales

**Eje 1 — Rol global (`users.role`):**

| Rol | Capacidad |
|---|---|
| `colaborador` | Default. Opera dentro de proyectos donde es miembro. No crea proyectos ni administra plataforma. |
| `gk_lead` | Super-admin. Crea proyectos, designa owners, opera cualquier proyecto sin membership, configura taxonomía global, audita. |

**Eje 2 — Rol per-proyecto (`project_members.role`):**

| Rol | Capacidad dentro del proyecto |
|---|---|
| `project_owner` | Admin del proyecto: gestiona miembros, define taxonomía, corre sesión de documentación, aprueba/rechaza ingesta. |
| `member` | Consulta + ingesta. Sube documentos → quedan en estado revisable para que el `project_owner` los admita. |

**Eliminación de `owner` global:** el rol `owner` actual desaparece. Su
semántica de aprobador transversal no aplica en un mundo multi-tenant
(no hay "carpetas globales" que aprobar). Se reemplaza por `project_owner`
per-proyecto.

**Eliminación de `capturador` global:** se renombra a `colaborador` porque el
rol no solo captura — también consulta y revisa. El nombre nuevo refleja el
uso real.

**Matriz de capacidades:**

| Capacidad | colaborador (no miembro) | member | project_owner | gk_lead |
|---|---|---|---|---|
| Ver proyecto | — | si | si | si |
| Hacer queries en el proyecto | — | si | si | si |
| Subir doc a cola ingesta | — | si | si | si |
| Aprobar/rechazar ingesta | — | — | **si (rol principal)** | si (habilitado, uso excepcional) |
| Añadir/quitar miembros | — | — | si | si |
| Editar taxonomía del proyecto | — | — | si | si |
| Correr sesión de documentación | — | — | si | si |
| Crear proyecto | — | — | — | si |
| Eliminar proyecto | — | — | — | si |
| Editar taxonomía global | — | — | — | si |

**Nota sobre GK Lead aprobando:** está habilitado por privilegio (auditoría,
soporte, reemplazo cuando el owner está ausente). En la UI la cola de
aprobación se muestra como tarea pendiente solo en el dashboard del
`project_owner`; GK Lead la ve en modo "supervisión" y debe confirmar con
modal "Aprobar como GK Lead (override)" para dejar trazado quién aprobó.

### D3. Datos existentes — proyecto seed `gk-general`

Migración crea proyecto `gk-general` (owner = GK Lead) y backfilea TODAS las
filas existentes con `project_id = <gk-general>`. Es el "proyecto raíz"
donde GK guarda conocimiento transversal a toda la organización.

**Reglas de migración de roles:**

| Antes (`users.role`) | Después (`users.role`) | Membership en `gk-general` |
|---|---|---|
| `owner` | `colaborador` | `project_owner` |
| `capturador` | `colaborador` | `member` |
| `gklead` | `gk_lead` (rename solo del literal) | — (acceso por privilegio global) |

### D4. Taxonomía por proyecto — herencia + override

Hay un set **global** (las constantes actuales `CATEGORY_LABELS` y
`DOC_TYPE_LABELS` del backend / `lib/taxonomy.ts` del frontend) que sirve de
fallback. Tablas nuevas permiten que cada proyecto extienda o anule:

```
project_categories(project_id, code, label, parent_global_code, is_override)
project_doc_types(project_id, code, label, parent_global_code, is_override)
```

**Resolución efectiva** (servicio `ProjectTaxonomyService`):
1. Empezar con global completo.
2. Aplicar overrides del proyecto (mismo `code` reemplaza `label`).
3. Añadir extensiones nuevas (codes que no existen en el global).

Sin overrides, el proyecto usa la taxonomía global tal cual. El classifier
del agente consulta taxonomía efectiva, no las constantes globales.

### D5. Sesión de documentación con el agente

Nuevo tipo de sesión `documentation` (vs `chat` genérico). Workflow guiado
por un subgrafo LangGraph con 5 steps fijos:

1. **Contexto del cliente** — industria, regulación, glosario inicial.
2. **Taxonomía del proyecto** — qué categorías/tipos necesita (overrides + extensiones).
3. **Fuentes de información** — SharePoint, Drive, repos del cliente.
4. **Términos clave y sinónimos** — alimenta el FTS y el chunking.
5. **Stakeholders y aprobadores** — quién aprueba qué tipo de doc.

Al cierre (`POST /sessions/{id}/finalize`), el agente genera N documentos
`.md` con metadata estructurada (uno por step, o uno consolidado por área)
y los mete al pipeline de ingesta del proyecto. Son la semilla del knowledge.

### D6. Scoping obligatorio de queries

Toda llamada a `/queries`, `/documents`, `/ingestion` requiere `project_id`
(en body, query string o path). El servicio valida:
- El proyecto existe.
- El usuario es miembro O es `gk_lead`.

El frontend siempre tiene un "proyecto activo" en `useActiveProject`
(Zustand + localStorage). GK Lead ve selector con todos los proyectos +
`gk-general`; los demás usuarios solo ven los proyectos donde tienen
membership.

---

## Modelo de datos (ER simplificado)

```
projects ──────────────┐
   ▲                   │
   │                   ├──< project_members
   │                   ├──< project_categories
   │                   ├──< project_doc_types
   │                   ├──< documents (+ project_id)
   │                   ├──< document_chunks (+ project_id)
   │                   ├──< sessions (+ project_id)
   │                   ├──< queries (+ project_id)
   │                   └──< ingestion_items (+ project_id)
   │
users ─────────────────┘   (oid es FK desde project_members.user_oid)
   role: colaborador | gk_lead

project_members
   (project_id, user_oid) PK compuesta
   role: project_owner | member
```

**Índices nuevos críticos:**
- `documents(project_id, status)` — listado por proyecto + estado.
- `document_chunks(project_id, embedding)` — combinado con el HNSW existente.
- `queries(project_id, created_at DESC)` — analytics por proyecto.
- `ingestion_items(project_id, status, uploaded_at DESC)` — cola por proyecto.

---

## Plan de migración por sub-fases

| Sub-fase | Salida | Riesgo |
|---|---|---|
| **9.0** | Este ADR + diseño ER. Sin código. | Bajo. Solo doc. |
| **9.1** | Alembic: crea tablas + columnas `project_id` + seed `gk-general` + backfill + migración de roles. Domain entities `Project`, `ProjectMember`. | Medio. Backfill de chunks puede tardar — usar batches. |
| **9.2** | Backend: `ProjectService` + endpoints `/projects/*` + `PermissionPolicy`. Tests de IDOR. | Medio. La policy es el blindaje principal — necesita cobertura completa. |
| **9.3** | Scoping en retriever / queries / ingesta. Filtros `project_id` + tests de aislamiento. | Alto. Tests críticos que confirmen que A no ve nada de B. |
| **9.4** | `ProjectTaxonomyService` con herencia + override. Endpoints `/projects/{id}/taxonomy`. | Bajo. |
| **9.5** | `DocumentationSessionWorkflow` con subgrafo LangGraph. | Alto. Diseño nuevo, requiere prompt engineering y tests con fakes del SDK. |
| **9.6** | Frontend `/admin/projects` (GK Lead). | Bajo. |
| **9.7** | Frontend `/projects/[id]/admin/*` (project_owner). | Medio. 3 sub-paneles. |
| **9.8** | Frontend selector global + `useActiveProject`. Cableado de scoping en todas las llamadas. | Medio. Refactor cross-cutting de la capa `lib/api/`. |
| **9.9** | Smoke E2E + cierre Fase 9 + merge a master. | Bajo si los previos están sólidos. |

---

## Alternativas consideradas

1. **Schema-per-project en Postgres.** Cada cliente en su propio schema con
   las mismas tablas. **Descartado:** migraciones se multiplican por N
   proyectos, herramientas (alembic, queries de analytics) requieren scripting
   extra, connection pooling se complica. La ganancia de aislamiento físico no
   compensa frente a row-level + RLS opcional futuro.

2. **DB-per-project.** Cada cliente en su propia instancia PostgreSQL.
   **Descartado:** costo Azure prohibitivo (5+ clientes × $50/mes en Flexible
   Server es la mitad del presupuesto Fase 0-11), aislamiento perfecto pero
   excesivo para el threat model SQA (todos los clientes son internos al
   ecosistema SQA Colombia).

3. **Mantener mono-tenant con tags.** Marcar documentos con `client_tag` y
   filtrar en la UI. **Descartado:** no es aislamiento real (cualquier query
   sin filtro devuelve todo), el agente vería contexto cruzado, y la
   taxonomía no podría divergir entre clientes — viola los requisitos.

4. **Workspaces (modelo Notion).** Un workspace tiene proyectos adentro;
   los proyectos no aíslan datos, los workspaces sí. **Descartado para SQA:**
   añade una capa jerárquica que no se justifica con un solo workspace real
   (SQA Colombia). Si crece a multi-país, se puede añadir después.

5. **Roles globales mantenidos + ACL granular por documento.** Cada documento
   tiene una ACL list de usuarios autorizados. **Descartado:** explosión de
   filas en la tabla ACL, performance pobre en queries de listado,
   mantenimiento operacional alto (cada miembro nuevo del proyecto necesita
   ACL en cientos de docs).

---

## Consecuencias

**Positivas:**
- Aislamiento real entre clientes — base para vender el producto a
  externos en el futuro.
- Project owners autónomos — GK Lead no es cuello de botella para
  operar cada cliente.
- Taxonomía adaptable por industria (banca usa `REG` que no aplica a retail).
- Sesión de documentación reduce el costo de onboarding inicial de un nuevo
  proyecto (de "compartirle docs al GK Lead" a "el cliente le cuenta al
  agente").
- Backfill a `gk-general` preserva todo el conocimiento existente sin pérdida.

**Negativas:**
- Refactor cross-cutting: el frontend hoy llama `lib/api/*` sin contexto de
  proyecto; hay que cablear `useActiveProject` en todos los hooks de Fase 5-8.
- Backfill de `document_chunks` puede ser lento si hay muchos chunks
  indexados (usar batches `UPDATE ... WHERE id BETWEEN ...`).
- Tests de aislamiento son obligatorios y aumentan la suite — esperamos
  +30 tests críticos solo en 9.3.
- El concepto "sesión de documentación" es nuevo en LangGraph para el
  proyecto — requiere diseño cuidadoso de prompts y tests con fakes del SDK
  Anthropic.

**Neutras:**
- El rol `owner` global desaparece — usuarios actuales con ese rol pasan
  automáticamente a `project_owner` de `gk-general` sin pérdida de
  capacidades reales.
- RLS de PostgreSQL queda como mejora futura opcional, no parte del MVP.

---

## Referencias

- ROADMAP §13 (Fase 9 — re-scope a multi-tenant)
- ADR 0001 — Monorepo (estructura general)
- `docs/IMPLEMENTATION-STATUS.md` (estado actual)
- `docs/memory/project_roles_capacidades.md` (matriz de roles, se actualiza en 9.1)
- LangGraph docs — subgraphs (para 9.5)
