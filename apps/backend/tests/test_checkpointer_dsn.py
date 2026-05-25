"""Tests unitarios del helper `psycopg_dsn` — no requiere DB."""

from __future__ import annotations

import pytest

from sqa_kb.adapters.checkpointer.postgres import psycopg_dsn


def test_dsn_strips_asyncpg_prefix() -> None:
    assert (
        psycopg_dsn("postgresql+asyncpg://u:p@h:5432/db")
        == "postgresql://u:p@h:5432/db"
    )


def test_dsn_strips_psycopg_prefix() -> None:
    """SQLAlchemy con psycopg sync usa este prefijo; lo normalizamos."""
    assert (
        psycopg_dsn("postgresql+psycopg://u:p@h:5432/db")
        == "postgresql://u:p@h:5432/db"
    )


def test_dsn_normalizes_legacy_postgres_prefix() -> None:
    assert (
        psycopg_dsn("postgres://u:p@h:5432/db") == "postgresql://u:p@h:5432/db"
    )


def test_dsn_passes_through_psycopg_native() -> None:
    """Si ya viene en formato psycopg lo dejamos intacto."""
    assert (
        psycopg_dsn("postgresql://u:p@h:5432/db?sslmode=require")
        == "postgresql://u:p@h:5432/db?sslmode=require"
    )


def test_dsn_empty_raises() -> None:
    with pytest.raises(ValueError, match="DSN vacío"):
        psycopg_dsn("")


def test_dsn_unknown_prefix_raises() -> None:
    with pytest.raises(ValueError, match="DSN no reconocido"):
        psycopg_dsn("mysql://u:p@h/db")


def test_dsn_only_prefix_no_host() -> None:
    """Caso borde: prefijo sin resto. Igual aplica conversión (lo deja en
    `postgresql://`) — la validación final del host la hace psycopg al
    intentar conectar."""
    assert psycopg_dsn("postgresql+asyncpg://") == "postgresql://"


def test_dsn_preserves_query_string() -> None:
    assert (
        psycopg_dsn("postgresql+asyncpg://u:p@h/db?application_name=foo")
        == "postgresql://u:p@h/db?application_name=foo"
    )


def test_dsn_preserves_special_chars_in_password() -> None:
    """Passwords con caracteres especiales se preservan tal cual."""
    assert (
        psycopg_dsn("postgresql+asyncpg://u:p%40ss@h/db")
        == "postgresql://u:p%40ss@h/db"
    )
