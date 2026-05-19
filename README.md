# SQA Knowledge Base

App standalone que reemplaza al agente actual de captura/consulta/ingesta
del conocimiento del equipo SQA. Implementa el [ROADMAP](../ROADMAP-IMPLEMENTACION-SQA-KB.md).

Estado: **Fase 0 + Fase 5 completadas y validadas** (2026-05-19).

📋 **Ver [docs/IMPLEMENTATION-STATUS.md](./docs/IMPLEMENTATION-STATUS.md)** para el detalle completo
fase por fase: lo entregado, lo pendiente, criterios de aceptación y validaciones.

## Estructura

```
sqa-knowledge-base/
├── apps/
│   ├── frontend/        Next.js 15 + React 19 + Tailwind + shadcn/ui
│   └── backend/         FastAPI + Pydantic v2 (esqueleto)
├── package.json         pnpm workspace root
└── pnpm-workspace.yaml
```

## Quick start

### Frontend

```bash
cd apps/frontend
pnpm install
pnpm dev
```

Abre http://localhost:3000 → selector de rol de prueba (auth stub).

### Backend

```bash
cd apps/backend
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn sqa_kb.main:app --reload --port 8000
```

http://localhost:8000/docs

## Tests

```bash
pnpm --filter @sqa/frontend test          # vitest
cd apps/backend && pytest -q              # pytest
```

## Plan de fases (frontend)

| Fase | Alcance | Estado |
|------|---------|--------|
| 5 | Fundación: stack, tema SQA, layout, login stub, páginas placeholder | **en curso** |
| 6 | Chat con streaming SSE para los 3 modos | pendiente |
| 7 | Explorer + Dashboard interactivo | pendiente |
| 8 | Cola de ingesta + workflow de aprobación | pendiente |
| 9 | Admin (usuarios, taxonomía, skills, audit) | pendiente |
| 10 | Hardening (perf, a11y, security review, i18n) | pendiente |
