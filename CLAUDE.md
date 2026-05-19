# CLAUDE.md — Instrucciones para Claude Code en este repo

> Este archivo se carga **automáticamente** al iniciar cualquier sesión de Claude Code dentro de `sqa-knowledge-base/`. Es el punto único de verdad para que cualquier sesión arranque con el contexto completo del proyecto sin que el usuario lo reexplique.

## Proyecto

**SQA Knowledge Base** — app web standalone que reemplaza al agente actual de captura/consulta/ingesta del conocimiento del equipo SQA. Multi-usuario con SSO Microsoft Entra ID, desplegada en Azure (Container Apps + PostgreSQL Flexible Server + Blob + Key Vault + App Insights).

- **Único desarrollador:** Andrés Altamiranda (andres.altamiranda@sqasa.co) — GK Lead.
- **Idioma:** español neutro para comunicación; código y nombres técnicos en inglés.
- **Timeline:** 16-20 semanas, 12 fases (0 a 11).

## Antes de hacer cualquier cosa

1. **Leé el estado actual** en `docs/IMPLEMENTATION-STATUS.md`. Ese documento es el espejo del [ROADMAP](../ROADMAP-IMPLEMENTACION-SQA-KB.md) con el avance real. Sabe qué está hecho y qué sigue.
2. **Verificá el git log:**
   ```bash
   git log --oneline -10
   ```
   El último commit indica el punto donde se cerró la sesión anterior.
3. **Revisá la memoria** (`MEMORY.md` ya cargado automáticamente). Tiene decisiones cerradas y preferencias del usuario.

## Reglas absolutas del proyecto

### Estilo de trabajo

- **SOLID estricto** — ver [`docs/development/conventions.md`](docs/development/conventions.md). El usuario lo exigió explícitamente al iniciar Fase 5.
- **Pausa para validar** al cerrar cada tarea principal (no cada cambio menor). Esperar aprobación antes de avanzar a la siguiente fase o área grande.
- **No premature abstractions** — si solo hay un caso, no hace falta una factoría todavía.
- **No backwards-compat shims** — código limpio sobre código histórico.
- **Tono:** técnico, directo, tuteo. Sin emojis en código ni UI.

### Seguridad

- **Cero secretos en el repo.** Los secretos viven en `C:\AriaAppGK\credentials.env` (fuera del árbol). `.gitignore` cubre `credentials.env`, `*.env`, `*.pem`, `*.key`. En Azure prod: Key Vault.
- **Nunca leas** `C:\AriaAppGK\credentials.env`. Solo el código en runtime lo carga.
- **Nunca commitees** archivos con keys reales. Si dudas, mostrale al usuario primero.

### Arquitectura

- **Stack frontend:** Next.js 15 + TS strict + Tailwind 3 + shadcn/ui (componentes manuales, inmutables).
- **Stack backend:** FastAPI + Pydantic v2 + SQLAlchemy 2.0 async + pgvector.
- **Auth:** stub MSAL en localStorage (Fase 5) → @azure/msal-react real (Fase 11). Interfaz estable entre ambos.
- **Capa `lib/api/`** es boundary explícito — UI nunca importa mocks directamente (DIP).
- **Clean Architecture** en backend: domain → adapters (ports), nunca al revés.

### Deploy target

- **Azure exclusivamente.** Container Apps, PostgreSQL Flexible Server, Blob, Key Vault, App Insights, Entra ID.
- **Bicep IaC** en `infra/` — TI ejecuta, Andrés entrega.
- **CI:** GitHub Actions (build + test + push a Azure Container Registry vía OIDC).
- **CD:** Azure DevOps Pipelines lo opera TI.

## Plan de fases (resumen)

| Fase | Bloque | Estado |
|---|---|---|
| 0 | Fundación (monorepo + infra + Azure) | ✅ Completada |
| 1 | Backend · Persistencia + Auth Entra ID | ⬜ Pendiente |
| 2 | Backend · Agente LangGraph (ETAPAS) | ⬜ Pendiente |
| 3 | Backend · RAG vectorial | ⬜ Pendiente |
| 4 | Backend · Generación y extracción docs | ⬜ Pendiente |
| 5 | Frontend · Fundación (UI + auth stub) | ✅ Completada |
| 6 | Frontend · Chat streaming SSE | ⬜ Pendiente ← **siguiente sugerida** |
| 7 | Frontend · Explorer + Dashboard | ⬜ Pendiente |
| 8 | Frontend · Cola de ingesta | ⬜ Pendiente |
| 9 | Frontend · Admin | ⬜ Pendiente |
| 10 | Hardening (perf + a11y + security) | ⬜ Pendiente |
| 11 | Migración legacy + producción Azure | ⬜ Pendiente |

**Detalle completo de cada fase en `docs/IMPLEMENTATION-STATUS.md`** (DoD, entregables, dependencias).

## Cómo arrancar una nueva sesión de Claude Code

Pegale esto a Claude al inicio de la sesión:

```
Retomá el proyecto. Leé docs/IMPLEMENTATION-STATUS.md y MEMORY.md, hacé un git log -10, decime en qué fase estamos y qué sigue.
```

O simplemente:

```
status
```

(si configuramos un alias — ver más abajo).

## Comandos frecuentes

```powershell
# Levantar dependencias locales
docker compose up -d

# Frontend dev
pnpm --filter @sqa/frontend dev          # → http://localhost:3000

# Backend dev (otro terminal)
cd apps\backend
.venv\Scripts\activate
uvicorn sqa_kb.main:app --reload --port 8000   # → http://localhost:8000/docs

# Tests
pnpm --filter @sqa/frontend test         # Vitest
cd apps\backend && .venv\Scripts\pytest -v   # Pytest

# Validar Bicep
C:\Users\evila\.local\bin\bicep.exe build infra\main.bicep

# Atajos PowerShell
.\scripts\dev.ps1 help
```

## Pre-requisitos del entorno (pueden no estar instalados tras reinicio)

| Herramienta | Versión | Cómo recuperar |
|---|---|---|
| Node | 20+ | https://nodejs.org/ |
| pnpm | 9.15+ | `npm i -g pnpm@9.15.0` |
| Python | 3.12+ | https://www.python.org/ |
| Docker Desktop | running | Iniciar Docker Desktop manualmente |
| Bicep CLI | 0.43+ | ya bajado en `C:\Users\evila\.local\bin\bicep.exe` |

Si algo falla, revisar `docs/development/getting-started.md`.

## Cosas a NO hacer

- ❌ No leas `C:\AriaAppGK\credentials.env`.
- ❌ No commitees `node_modules/`, `.venv/`, `.next/`, archivos `.env`, ni nada en `apps/frontend/.next/`.
- ❌ No modifiques los componentes base de `src/components/ui/` (shadcn) — extendé por composición.
- ❌ No uses `any` en TypeScript sin justificación documentada.
- ❌ No mezcles sync con async en Python (FastAPI es async por defecto).
- ❌ No avances a la siguiente fase sin la aprobación explícita del usuario.
- ❌ No instales paquetes "para probar" sin antes verificar que están en el roadmap o el usuario los pidió.

## Decisiones cerradas (no preguntar de nuevo)

- ✅ Stack: Next.js 15 + FastAPI + PostgreSQL + Azure (ver memoria `project-stack-decisions`)
- ✅ Auth Fase 5: stub MSAL con localStorage; Fase 11 swap a Entra ID real
- ✅ Tailwind 3 (no 4) — 4 aún no madura con Next 15
- ✅ shadcn/ui componentes manuales, no CLI
- ✅ Estilo: SOLID estricto, sin emojis, español en docs/comentarios
- ✅ Comunicación: pausa para validar al cerrar cada tarea principal

## Si encontrás trabajo a medias

Si el `git status` muestra archivos sin commit, asumí que la sesión anterior cerró en medio de algo:

1. `git status` y `git diff` para ver el estado.
2. Comparar con la última entrada de `docs/IMPLEMENTATION-STATUS.md` — si dice "completada" pero hay cambios uncommitted, probablemente falta el commit del cierre de fase.
3. Preguntar al usuario antes de descartar o continuar.

---

*Actualizá este archivo solo si cambia algo estructural del proyecto (nueva fase, cambio de stack, nueva regla del usuario). Para tracking de avance usa `docs/IMPLEMENTATION-STATUS.md`.*
