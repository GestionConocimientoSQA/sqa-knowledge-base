"""Kubernetes/Container Apps health probes (12-factor)."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """The process is running."""
    return {"status": "live"}


@router.get("/health/ready")
async def readiness() -> dict[str, str]:
    """The app can serve traffic (DB/deps reachable)."""
    # Fase 1+: validar conexión a PostgreSQL y dependencies externas.
    return {"status": "ready"}


@router.get("/health/startup")
async def startup() -> dict[str, str]:
    """The app finished initial bootstrap."""
    return {"status": "started"}
