# ============================================================
# SQA Knowledge Base — Atajos para Windows / PowerShell
# ============================================================
# Equivalente al Makefile. Uso:
#   .\scripts\dev.ps1 <comando>
#
# Ejemplos:
#   .\scripts\dev.ps1 install
#   .\scripts\dev.ps1 up
#   .\scripts\dev.ps1 dev-frontend
#   .\scripts\dev.ps1 test
# ============================================================

param(
    [Parameter(Position = 0)]
    [ValidateSet(
        "help", "install", "up", "down", "down-clean", "logs",
        "dev-frontend", "dev-backend",
        "test", "test-frontend", "test-backend",
        "lint", "typecheck", "build", "db-shell", "clean"
    )]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Invoke-Compose([string[]]$args) {
    Push-Location $root
    try { & docker compose @args } finally { Pop-Location }
}

switch ($Command) {
    "help" {
        Write-Host ""
        Write-Host "SQA KB · comandos disponibles:" -ForegroundColor Cyan
        Write-Host "  install        Instala deps (pnpm + pip backend)"
        Write-Host "  up             docker compose up (Postgres, Azurite, Redis)"
        Write-Host "  down           docker compose down"
        Write-Host "  down-clean     down -v (borra volúmenes)"
        Write-Host "  logs           Logs en streaming"
        Write-Host "  dev-frontend   Next.js dev server :3000"
        Write-Host "  dev-backend    FastAPI :8000"
        Write-Host "  test           Tests frontend + backend"
        Write-Host "  test-frontend  Vitest"
        Write-Host "  test-backend   Pytest"
        Write-Host "  lint           ESLint + ruff"
        Write-Host "  typecheck      tsc --noEmit"
        Write-Host "  build          pnpm build"
        Write-Host "  db-shell       psql contra la DB local"
        Write-Host "  clean          Borra .next / node_modules / __pycache__"
        Write-Host ""
    }
    "install" {
        Push-Location $root
        try {
            pnpm install
            if ($?) {
                Push-Location "$root\apps\backend"
                try { python -m pip install -e ".[dev]" } finally { Pop-Location }
            }
        } finally { Pop-Location }
    }
    "up" {
        Invoke-Compose @("up", "-d")
        Write-Host "Postgres :5432 · Azurite :10000 · Redis :6379" -ForegroundColor Green
    }
    "down" { Invoke-Compose @("down") }
    "down-clean" { Invoke-Compose @("down", "-v") }
    "logs" { Invoke-Compose @("logs", "-f") }
    "dev-frontend" {
        Push-Location $root
        try { pnpm --filter @sqa/frontend dev } finally { Pop-Location }
    }
    "dev-backend" {
        Push-Location "$root\apps\backend"
        try { uvicorn sqa_kb.main:app --reload --port 8000 } finally { Pop-Location }
    }
    "test-frontend" {
        Push-Location $root
        try { pnpm --filter @sqa/frontend test } finally { Pop-Location }
    }
    "test-backend" {
        Push-Location "$root\apps\backend"
        try { pytest -q } finally { Pop-Location }
    }
    "test" {
        & $PSCommandPath "test-frontend"
        if ($?) { & $PSCommandPath "test-backend" }
    }
    "lint" {
        Push-Location $root
        try {
            pnpm --filter @sqa/frontend lint
            Push-Location "$root\apps\backend"
            try { ruff check . } finally { Pop-Location }
        } finally { Pop-Location }
    }
    "typecheck" {
        Push-Location $root
        try { pnpm --filter @sqa/frontend typecheck } finally { Pop-Location }
    }
    "build" {
        Push-Location $root
        try { pnpm --filter @sqa/frontend build } finally { Pop-Location }
    }
    "db-shell" { Invoke-Compose @("exec", "postgres", "psql", "-U", "sqa", "-d", "sqa_kb") }
    "clean" {
        Push-Location $root
        try {
            Remove-Item -Recurse -Force "apps\frontend\.next" -ErrorAction SilentlyContinue
            Remove-Item -Recurse -Force "apps\frontend\node_modules" -ErrorAction SilentlyContinue
            Remove-Item -Recurse -Force "apps\backend\.venv" -ErrorAction SilentlyContinue
            Remove-Item -Recurse -Force "apps\backend\.pytest_cache" -ErrorAction SilentlyContinue
            Get-ChildItem -Path "apps\backend" -Filter "__pycache__" -Recurse -Directory |
                Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
            Remove-Item -Recurse -Force "node_modules" -ErrorAction SilentlyContinue
            Write-Host "Limpio." -ForegroundColor Green
        } finally { Pop-Location }
    }
}
