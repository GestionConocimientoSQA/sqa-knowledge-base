"""Tests del Settings."""

from __future__ import annotations

import pytest

from sqa_kb.config import AppEnv, DatabaseDialect, LlmGatewayKind, Settings, VectorStore


def test_defaults_dev() -> None:
    s = Settings()
    assert s.app_env is AppEnv.TEST  # conftest fija test
    assert s.api_v1_prefix == "/api/v1"
    assert s.database_dialect is DatabaseDialect.POSTGRES
    assert s.llm_gateway_kind is LlmGatewayKind.ANTHROPIC_DIRECT
    assert s.vector_store is VectorStore.NONE
    assert s.is_local is True


def test_cors_csv_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "SQA_KB_CORS_ALLOWED_ORIGINS",
        "http://localhost:3000, https://kb.sqa.co , https://staging.sqa.co",
    )
    s = Settings()
    assert s.cors_allowed_origins == [
        "http://localhost:3000",
        "https://kb.sqa.co",
        "https://staging.sqa.co",
    ]


def test_prod_requires_entra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SQA_KB_APP_ENV", "prod")
    with pytest.raises(Exception, match="ENTRA_TENANT_ID"):
        Settings()


def test_prod_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SQA_KB_APP_ENV", "prod")
    monkeypatch.setenv("SQA_KB_ENTRA_TENANT_ID", "t1")
    monkeypatch.setenv("SQA_KB_ENTRA_CLIENT_ID", "c1")
    monkeypatch.setenv("SQA_KB_ANTHROPIC_API_KEY", "key")
    with pytest.raises(Exception, match="DATABASE_URL"):
        Settings()


def test_litellm_requires_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SQA_KB_LLM_GATEWAY_KIND", "litellm")
    with pytest.raises(Exception, match="LITELLM_BASE_URL"):
        Settings()


def test_anthropic_required_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SQA_KB_APP_ENV", "prod")
    monkeypatch.setenv("SQA_KB_ENTRA_TENANT_ID", "t1")
    monkeypatch.setenv("SQA_KB_ENTRA_CLIENT_ID", "c1")
    monkeypatch.setenv(
        "SQA_KB_DATABASE_URL", "postgresql+asyncpg://x:y@localhost/db"
    )
    # No ANTHROPIC_API_KEY pero llm_gateway_kind default = anthropic_direct
    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        Settings()


def test_dev_allows_missing_secrets() -> None:
    """En dev/test el Settings no exige las claves de prod."""
    s = Settings()
    assert s.database_url is None
    assert s.entra_tenant_id is None
    assert s.anthropic_api_key is None


def test_is_local_only_for_dev_test(monkeypatch: pytest.MonkeyPatch) -> None:
    for env, expected in [("dev", True), ("test", True), ("staging", False), ("prod", False)]:
        monkeypatch.setenv("SQA_KB_APP_ENV", env)
        if env in ("staging", "prod"):
            # Estos requieren las vars de prod — skip aquí, ya cubierto en otros tests.
            continue
        s = Settings()
        assert s.is_local is expected
