# ============================================================
# SQA Knowledge Base - Status snapshot
# ============================================================
# Vista rapida del estado del proyecto.
# Uso: .\scripts\status.ps1
# ============================================================

$ErrorActionPreference = "SilentlyContinue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Write-Section($title) {
    Write-Host ""
    Write-Host "--- $title ---" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "SQA Knowledge Base - status" -ForegroundColor Yellow
Write-Host "Directorio: $root" -ForegroundColor DarkGray
Write-Host (Get-Date -Format "yyyy-MM-dd HH:mm") -ForegroundColor DarkGray

# Git
Write-Section "Git"
if (Test-Path "$root\.git") {
    $branch = git rev-parse --abbrev-ref HEAD 2>$null
    $commits = git rev-list --count HEAD 2>$null
    if (-not $commits) { $commits = 0 }
    $last = git log -1 --pretty=format:"%h %s (%cr)" 2>$null
    if (-not $last) { $last = "(sin commits aun)" }
    $dirty = (git status --short 2>$null | Measure-Object).Count
    Write-Host "  Branch:        $branch"
    Write-Host "  Commits:       $commits"
    Write-Host "  Ultimo commit: $last"
    Write-Host "  Sin commitear: $dirty archivos"
} else {
    Write-Host "  Sin repo git inicializado" -ForegroundColor Yellow
}

# Fases
Write-Section "Fases"
$statusFile = "docs\IMPLEMENTATION-STATUS.md"
if (Test-Path $statusFile) {
    $tableLines = Get-Content $statusFile -Encoding UTF8 |
        Select-String -Pattern "^\| (\d+|\*\*\d+)" |
        Where-Object { $_.Line -notmatch "archivos esperados" } |
        ForEach-Object { $_.Line }
    if ($tableLines) {
        $tableLines | ForEach-Object { Write-Host "  $_" }
    }
    Write-Host ""
    Write-Host "  Detalle completo: docs\IMPLEMENTATION-STATUS.md"
} else {
    Write-Host "  Falta docs\IMPLEMENTATION-STATUS.md" -ForegroundColor Yellow
}

# Servicios locales
Write-Section "Servicios locales"
$ports = [ordered]@{
    3000  = "Frontend Next.js"
    8000  = "Backend FastAPI"
    5432  = "Postgres"
    6379  = "Redis"
    10000 = "Azurite Blob"
}
foreach ($p in $ports.GetEnumerator()) {
    $listening = (Get-NetTCPConnection -LocalPort $p.Name -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0
    if ($listening) {
        Write-Host ("  [UP]  {0,-6} {1}" -f $p.Name, $p.Value) -ForegroundColor Green
    } else {
        Write-Host ("  [off] {0,-6} {1}" -f $p.Name, $p.Value) -ForegroundColor DarkGray
    }
}

# Docker Compose
Write-Section "Docker Compose"
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    $psOutput = docker compose ps --format "table {{.Service}}`t{{.State}}`t{{.Health}}" 2>$null
    if ($psOutput) {
        $psOutput | ForEach-Object { Write-Host "  $_" }
    } else {
        Write-Host "  (compose down - ningun servicio corriendo)" -ForegroundColor DarkGray
    }
} else {
    Write-Host "  Docker no disponible" -ForegroundColor Yellow
}

# Toolchain
Write-Section "Toolchain"
$tools = @(
    @{ name = "node";   cmd = "node --version" },
    @{ name = "pnpm";   cmd = "pnpm --version" },
    @{ name = "python"; cmd = "python --version" },
    @{ name = "docker"; cmd = "docker --version" }
)
foreach ($t in $tools) {
    try {
        $v = Invoke-Expression $t.cmd 2>$null
        if ($v) {
            Write-Host ("  {0,-10} {1}" -f $t.name, ($v | Select-Object -First 1))
        } else {
            Write-Host ("  {0,-10} (no encontrado)" -f $t.name) -ForegroundColor Yellow
        }
    } catch {
        Write-Host ("  {0,-10} (error)" -f $t.name) -ForegroundColor Yellow
    }
}

# Proximo paso
Write-Section "Proximo paso"
Write-Host "  Para retomar con Claude Code, abri una sesion en este directorio"
Write-Host "  y pegale este mensaje:"
Write-Host ""
Write-Host "    Retoma el proyecto. Lee CLAUDE.md y docs/IMPLEMENTATION-STATUS.md," -ForegroundColor DarkCyan
Write-Host "    deci en que fase estamos y que sigue." -ForegroundColor DarkCyan
Write-Host ""
