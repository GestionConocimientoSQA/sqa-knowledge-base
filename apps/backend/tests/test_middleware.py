"""Tests del middleware (request-id + error handler)."""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sqa_kb.domain.errors import (
    ConflictError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
)
from sqa_kb.domain.errors import (
    ValidationError as DomainValidationError,
)
from sqa_kb.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    yield TestClient(create_app())


UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def test_request_id_auto_generated_when_missing(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    rid = response.headers["X-Request-ID"]
    assert UUID_RE.match(rid), f"esperaba UUID, recibí {rid!r}"


def test_request_id_propagated_from_request(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "rid-test-123"})
    assert response.headers["X-Request-ID"] == "rid-test-123"


def test_request_id_truncates_overly_long(client: TestClient) -> None:
    # >128 chars → middleware lo descarta y genera uno nuevo (defensa).
    huge = "x" * 200
    response = client.get("/health/live", headers={"X-Request-ID": huge})
    rid = response.headers["X-Request-ID"]
    assert rid != huge
    assert UUID_RE.match(rid)


def test_each_request_gets_independent_rid(client: TestClient) -> None:
    r1 = client.get("/health/live").headers["X-Request-ID"]
    r2 = client.get("/health/live").headers["X-Request-ID"]
    assert r1 != r2


# ---------- error handler ----------


def _app_with_test_routes() -> FastAPI:
    app = create_app()

    @app.get("/_test/notfound")
    async def _nf() -> None:
        raise NotFoundError("missing")

    @app.get("/_test/unauthorized")
    async def _u() -> None:
        raise UnauthorizedError("auth required")

    @app.get("/_test/forbidden")
    async def _f() -> None:
        raise ForbiddenError("no permission")

    @app.get("/_test/validation")
    async def _v() -> None:
        raise DomainValidationError("bad input")

    @app.get("/_test/conflict")
    async def _c() -> None:
        raise ConflictError("already exists")

    @app.get("/_test/rate")
    async def _r() -> None:
        raise RateLimitedError("slow down", retry_after_seconds=42)

    @app.get("/_test/external")
    async def _e() -> None:
        raise ExternalServiceError("anthropic down", service="anthropic")

    @app.get("/_test/boom")
    async def _b() -> None:
        raise RuntimeError("unexpected")

    return app


@pytest.fixture
def custom_client() -> Iterator[TestClient]:
    # raise_server_exceptions=False permite que el handler de Exception
    # registrado en `register_error_handlers` mapee el 500 a JSON en lugar
    # de propagar la excepción al test (default de TestClient).
    yield TestClient(_app_with_test_routes(), raise_server_exceptions=False)


def test_notfound_maps_to_404(custom_client: TestClient) -> None:
    r = custom_client.get("/_test/notfound")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "NotFoundError"
    assert body["error"]["message"] == "missing"
    assert "request_id" in body["error"]


def test_unauthorized_maps_to_401(custom_client: TestClient) -> None:
    assert custom_client.get("/_test/unauthorized").status_code == 401


def test_forbidden_maps_to_403(custom_client: TestClient) -> None:
    assert custom_client.get("/_test/forbidden").status_code == 403


def test_validation_maps_to_422(custom_client: TestClient) -> None:
    assert custom_client.get("/_test/validation").status_code == 422


def test_conflict_maps_to_409(custom_client: TestClient) -> None:
    assert custom_client.get("/_test/conflict").status_code == 409


def test_rate_limited_maps_to_429_with_retry_after(custom_client: TestClient) -> None:
    r = custom_client.get("/_test/rate")
    assert r.status_code == 429
    assert r.headers["Retry-After"] == "42"
    body = r.json()
    assert body["error"]["retry_after_seconds"] == 42


def test_external_service_maps_to_503_with_service(custom_client: TestClient) -> None:
    r = custom_client.get("/_test/external")
    assert r.status_code == 503
    body = r.json()
    assert body["error"]["service"] == "anthropic"


def test_unhandled_exception_maps_to_500(custom_client: TestClient) -> None:
    r = custom_client.get("/_test/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["error"]["code"] == "InternalServerError"
    # No filtramos el mensaje real del exception al cliente.
    assert "unexpected" not in body["error"]["message"]


def test_request_id_present_in_error_payload(custom_client: TestClient) -> None:
    rid = str(uuid.uuid4())
    r = custom_client.get("/_test/notfound", headers={"X-Request-ID": rid})
    assert r.json()["error"]["request_id"] == rid
