"""Kubernetes / Container Apps health probes (12-factor).

Tres probes con semánticas distintas:
- `/health/live` — el proceso está corriendo. Si esto falla, Container Apps reinicia.
- `/health/ready` — dependencias externas alcanzables. Si esto falla, el load
  balancer saca el pod de rotación pero NO reinicia.
- `/health/startup` — bootstrap inicial terminó. Se chequea una vez al arranque.

En Fase 1A `/ready` no chequea nada externo todavía (sin DB conectada).
En 1B se inyectan checks reales vía `register_health_check()`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from fastapi import APIRouter, HTTPException

from sqa_kb.ports.gateways import HealthCheck, HealthCheckResult

router = APIRouter(tags=["health"])


# Registro mutable de health checks. En 1B se llenará al startup con checks
# reales (DB, blob, LLM gateway). Por ahora vacío — `/ready` devuelve OK trivial.
_registered_checks: list[HealthCheck] = []


def register_health_check(check: HealthCheck) -> None:
    """Agrega un verificador al pool global. Llamar al wiring de la app."""
    _registered_checks.append(check)


def reset_health_checks() -> None:
    """Reset — útil entre tests."""
    _registered_checks.clear()


@router.get("/health/live", summary="Liveness — el proceso responde")
async def liveness() -> dict[str, str]:
    """Devuelve 200 mientras el handler responda. No chequea dependencias."""
    return {"status": "live"}


@router.get("/health/startup", summary="Startup — bootstrap completo")
async def startup() -> dict[str, str]:
    """Bootstrap inicial terminó."""
    return {"status": "started"}


@router.get(
    "/health/ready",
    summary="Readiness — dependencias externas alcanzables",
    responses={503: {"description": "Una o más dependencias no responden."}},
)
async def readiness() -> dict[str, object]:
    """Corre todos los `HealthCheck` registrados en paralelo.

    Si alguno falla devuelve 503 con el detalle por check.
    """
    if not _registered_checks:
        return {"status": "ready", "checks": []}

    results = await _run_checks(_registered_checks)
    all_healthy = all(r.healthy for r in results)

    payload: dict[str, object] = {
        "status": "ready" if all_healthy else "degraded",
        "checks": [
            {
                "name": r.name,
                "healthy": r.healthy,
                "detail": r.detail,
                "duration_ms": round(r.duration_ms, 2),
            }
            for r in results
        ],
    }

    if not all_healthy:
        raise HTTPException(status_code=503, detail=payload)

    return payload


async def _run_checks(checks: Sequence[HealthCheck]) -> list[HealthCheckResult]:
    coros = [_safe_check(c) for c in checks]
    return list(await asyncio.gather(*coros))


async def _safe_check(check: HealthCheck) -> HealthCheckResult:
    """Wrappea la excepción de un check para que no tumbe el endpoint."""
    try:
        return await check.check()
    except Exception as exc:  # noqa: BLE001 — defensa en profundidad
        return HealthCheckResult(
            name=check.name,
            healthy=False,
            detail=f"{type(exc).__name__}: {exc}",
        )
