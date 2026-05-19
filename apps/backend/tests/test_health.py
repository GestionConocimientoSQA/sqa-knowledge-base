"""Smoke tests del esqueleto FastAPI."""

import pytest
from fastapi.testclient import TestClient

from sqa_kb.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_root_returns_service_info(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "sqa-knowledge-base"


def test_liveness_probe(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "live"}


def test_readiness_probe(client: TestClient) -> None:
    assert client.get("/health/ready").json() == {"status": "ready"}
