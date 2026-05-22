"""Tests de los health probes."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from sqa_kb.api.health import register_health_check, reset_health_checks
from sqa_kb.main import create_app
from sqa_kb.ports.gateways import HealthCheckResult


@pytest.fixture
def client() -> Iterator[TestClient]:
    reset_health_checks()
    yield TestClient(create_app())
    reset_health_checks()


def test_root_returns_service_info(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "sqa-knowledge-base"


def test_liveness_probe(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_startup_probe(client: TestClient) -> None:
    response = client.get("/health/startup")
    assert response.status_code == 200
    assert response.json() == {"status": "started"}


def test_readiness_without_checks(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ready", "checks": []}


def test_readiness_with_all_healthy_checks(client: TestClient) -> None:
    class _Ok:
        name = "ok-check"

        async def check(self) -> HealthCheckResult:
            return HealthCheckResult(name=self.name, healthy=True, duration_ms=1.0)

    register_health_check(_Ok())
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert len(body["checks"]) == 1
    assert body["checks"][0]["healthy"] is True


def test_readiness_503_when_check_fails(client: TestClient) -> None:
    class _Down:
        name = "db-down"

        async def check(self) -> HealthCheckResult:
            return HealthCheckResult(
                name=self.name, healthy=False, detail="connection refused"
            )

    register_health_check(_Down())
    response = client.get("/health/ready")
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["status"] == "degraded"
    assert detail["checks"][0]["detail"] == "connection refused"


def test_readiness_check_raising_is_marked_unhealthy(client: TestClient) -> None:
    class _Boom:
        name = "exploding-check"

        async def check(self) -> HealthCheckResult:
            raise RuntimeError("kaboom")

    register_health_check(_Boom())
    response = client.get("/health/ready")
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["checks"][0]["healthy"] is False
    assert "RuntimeError" in detail["checks"][0]["detail"]
