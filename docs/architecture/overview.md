# Arquitectura · Overview

## Vista de 10.000 pies

SQA Knowledge Base es una app web standalone que reemplaza al agente actual
(Claude Code + Cowork) por una experiencia productiva, multiusuario y
desplegada en Azure de la organización.

```
                         Internet
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
   [Azure Container Apps]         [Azure Container Apps]
     Frontend (Next.js)            Backend (FastAPI)
              │                           │
              └──────── REST/SSE ─────────┘
                            │
        ┌───────────────────┼───────────────────────┐
        ▼                   ▼                       ▼
   [PostgreSQL          [Blob Storage]        [Key Vault]
    Flexible Server      base-conocimiento     ANTHROPIC_API_KEY
    + pgvector]          inbox-pendientes      conexiones
    datos + vectores     borradores            JWKS endpoint
                                                    │
                            ┌───────────────────────┘
                            ▼
                  [Application Insights]    [Langfuse]
                   métricas + traces        traces LLM
                            │                     │
                            └──── observabilidad ─┘

   [Microsoft Entra ID]  ←── autenticación SSO
   [Anthropic API]       ←── LLM (externo, fuera de Azure)
```

## Capas conceptuales (backend)

Clean Architecture — dependencias apuntan hacia adentro:

```
[ API (FastAPI routers) ]     ← capa de transporte
        │
        ▼
[ Agent (LangGraph) ]         ← orquestación de conversación
        │
        ▼
[ Domain (modelos + services + ports) ]  ← núcleo, sin frameworks
        ▲
        │
[ Adapters: persistence · llm · storage · auth ]  ← implementaciones de ports
```

El dominio nunca importa frameworks (FastAPI, SQLAlchemy, anthropic SDK).
Los adapters implementan interfaces (`ports`) definidas en el dominio.

## Componentes principales del frontend

```
src/
├── app/                   ← routing (App Router)
│   ├── (auth)/            ← rutas no autenticadas
│   └── (app)/             ← rutas autenticadas con layout principal
├── components/
│   ├── ui/                ← shadcn/ui (inmutable)
│   ├── brand/             ← Aria mascot, SQA logo
│   ├── layout/            ← Sidebar, Topbar
│   ├── chat/              ← chat window, message bubble, stage indicator (Fase 6)
│   ├── documents/         ← document card, scoring badge (Fase 7)
│   └── shared/            ← empty/loading/error states, stat card
├── lib/
│   ├── api/               ← capa boundary contra el backend (DIP)
│   ├── auth/              ← stub MSAL ↔ MSAL real (interfaz estable)
│   └── streaming/         ← consumidor SSE (Fase 6)
├── hooks/
├── stores/                ← Zustand para estado UI cliente
└── types/                 ← contratos compartidos
```

## Principios transversales

1. **SOLID** estricto en código (ver `docs/development/conventions.md`).
2. **12-factor app** en backend — config via env, stateless, logs a stdout.
3. **Tipos compartidos** front↔back vía OpenAPI (Fase 1+).
4. **Boundaries explícitos** — UI nunca toca DB; backend nunca emite HTML.
5. **Observabilidad de primera** — todo request con `X-Request-ID` + trace.
6. **Cero secretos en repo** — Key Vault en Azure, `credentials.env` local.

## Referencias

- [ROADMAP completo](../../../ROADMAP-IMPLEMENTACION-SQA-KB.md) (en raíz padre)
- [ADRs](./adr/)
- [Despliegue a Azure](../deployment/) (pendiente, Fase 11)
