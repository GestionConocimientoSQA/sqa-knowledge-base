# ADR 0001 · Monorepo

- **Estado:** aceptado
- **Fecha:** 2026-05-19
- **Decisor:** Andrés Altamiranda

## Contexto

El proyecto SQA Knowledge Base tiene dos artefactos desplegables (frontend
Next.js + backend FastAPI), tipos compartidos (OpenAPI → TypeScript), un único
desarrollador y una sola release line. Necesitamos decidir si separar en
múltiples repos o mantenerlos juntos.

## Decisión

Usar **monorepo único** organizado por apps:

```
sqa-knowledge-base/
├── apps/{frontend, backend}
├── packages/api-types       (tipos generados desde OpenAPI)
├── infra/                   (Bicep)
├── docs/
└── scripts/
```

Manager: **pnpm workspaces** para JS/TS, **uv** para Python (cada uno en su app).

## Alternativas consideradas

1. **Polyrepo (frontend + backend + infra separados)** — Descartado: tres
   repos para un único dev triplican la fricción de cambios cross-cutting
   (cambio de contrato API + UI consumidora + migración DB). El roadmap
   espera changes frecuentes así.
2. **Monorepo con Nx/Turborepo** — Descartado: complejidad innecesaria con
   solo dos apps. pnpm workspaces ya cubre orchestration y caching básico.

## Consecuencias

**Positivas:**
- Cambios de contrato (OpenAPI) atómicos en un solo PR.
- Un solo issue tracker, un solo CI.
- Branch única → versionado coherente entre apps.
- Tipos siempre sincronizados.

**Negativas:**
- CI tiene que detectar áreas cambiadas (`paths-filter`) para no correr todo
  todo el tiempo.
- Permisos GitHub son a nivel repo — no se puede dar read-only a TI sobre
  `infra/` sin darles read del código completo (se acepta).
- Tamaño del repo crece más rápido que un polyrepo.

## Referencias

- ROADMAP §6 (estructura del monorepo)
