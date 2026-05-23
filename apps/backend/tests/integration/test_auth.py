"""Tests de integración del flujo completo auth: dev token → /auth/me."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from sqa_kb.adapters.repositories.postgres.seed import seed
from sqa_kb.main import create_app


@pytest.fixture(scope="module")
async def _seed_db(session_factory) -> None:  # type: ignore[no-untyped-def]
    """Sembrar la DB con usuarios stub antes de los tests."""
    await seed(session_factory)


@pytest.fixture(scope="module")
def client(_seed_db) -> Iterator[TestClient]:  # type: ignore[no-untyped-def]
    yield TestClient(create_app())


def test_me_without_authorization_returns_401(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UnauthorizedError"


def test_me_with_invalid_token_returns_401(client: TestClient) -> None:
    response = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


def test_me_with_unknown_oid_returns_401(client: TestClient) -> None:
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer dev:oid-no-existe-123"},
    )
    assert response.status_code == 401
    assert "no existe" in response.json()["error"]["message"].lower()


def test_me_with_capturador_token(client: TestClient) -> None:
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer dev:stub-capturador-00000000"},
    )
    assert response.status_code == 200
    body = response.json()
    # El backend serializa en camelCase (alias_generator=to_camel) para que
    # el frontend pueda usarlo sin mappers manuales.
    assert body["oid"] == "stub-capturador-00000000"
    assert body["roleId"] == "capturador"
    assert body["isAdmin"] is False
    assert body["puedeGobernarTaxonomia"] is False
    assert body["puedeVerMetricasGlobales"] is False


def test_me_with_owner_token_returns_carpetas_owned(client: TestClient) -> None:
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer dev:stub-owner-00000000"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["roleId"] == "owner"
    assert body["isAdmin"] is True
    assert "TEC" in body["carpetasOwned"]
    assert "ARQ" in body["carpetasOwned"]


def test_me_with_gklead_has_full_powers(client: TestClient) -> None:
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer dev:stub-gklead-00000000"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["roleId"] == "gklead"
    assert body["isAdmin"] is True
    assert body["puedeGobernarTaxonomia"] is True
    assert body["puedeVerMetricasGlobales"] is True


def test_me_propagates_request_id_to_error_payload(client: TestClient) -> None:
    """Cuando falla la auth, el error incluye `request_id` para tracing."""
    response = client.get(
        "/auth/me",
        headers={"X-Request-ID": "rid-test-abc"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["request_id"] == "rid-test-abc"
    assert response.headers["X-Request-ID"] == "rid-test-abc"
