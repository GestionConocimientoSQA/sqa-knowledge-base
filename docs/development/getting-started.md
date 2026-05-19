# Getting started

## Pre-requisitos

| Tool | Versión | Cómo |
|---|---|---|
| Node.js | 20+ | https://nodejs.org/ |
| pnpm | 9.15+ | `npm i -g pnpm@9.15.0` |
| Python | 3.12+ | https://www.python.org/ |
| Docker Desktop | 4.x | https://www.docker.com/ |
| Git | 2.x | https://git-scm.com/ |
| Make | opcional | Git for Windows lo incluye, o `choco install make` |

## Primer setup

```powershell
# 1. Clonar el repo
git clone <url> sqa-knowledge-base
cd sqa-knowledge-base

# 2. Copiar .env.example y colocar API keys reales en C:\AriaAppGK\credentials.env
copy .env.example .env

# 3. Instalar dependencias
pnpm install
cd apps\backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
cd ..\..

# 4. Levantar dependencias (Postgres + Azurite + Redis)
docker compose up -d

# 5. Correr migraciones (a partir de Fase 1)
# cd apps\backend
# alembic upgrade head

# 6. Arrancar el frontend
pnpm --filter @sqa/frontend dev   # abre http://localhost:3000

# 7. (En otra terminal) arrancar el backend
cd apps\backend
uvicorn sqa_kb.main:app --reload --port 8000   # http://localhost:8000/docs
```

## Atajos (PowerShell)

```powershell
.\scripts\dev.ps1 up             # docker compose up
.\scripts\dev.ps1 dev-frontend
.\scripts\dev.ps1 dev-backend
.\scripts\dev.ps1 test
.\scripts\dev.ps1 db-shell
```

O con `make` si está instalado:

```bash
make help
make up
make dev-frontend
make test
```

## Credenciales

Los secretos (ANTHROPIC_API_KEY, etc.) viven en `C:\AriaAppGK\credentials.env`
— **fuera del repo**. Ver [secrets-handling.md](./secrets-handling.md).

## Troubleshooting

- **`pnpm install` lento en Windows:** activá Defender exclusion para
  `node_modules` o usá WSL.
- **`docker compose up` falla:** verificá que Docker Desktop está corriendo y
  que los puertos 5432/10000/6379 están libres.
- **Build falla con error de symlink:** desactivá `output: standalone` en
  `next.config.mjs` (ya está condicional por `NEXT_BUILD_STANDALONE` env).
