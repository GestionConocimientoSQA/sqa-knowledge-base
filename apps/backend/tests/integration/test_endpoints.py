"""Tests E2E de los endpoints CRUD del API.

Cubren el flujo completo HTTP → handler → service → repo → DB, incluyendo
los headers de auth con el dev provider.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from sqa_kb.adapters.repositories.postgres import models
from sqa_kb.adapters.repositories.postgres.seed import seed
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.main import create_app

CAPTURADOR = "Bearer dev:stub-capturador-00000000"
OWNER = "Bearer dev:stub-owner-00000000"
GKLEAD = "Bearer dev:stub-gklead-00000000"


@pytest.fixture(scope="module")
async def _seed_db(session_factory) -> None:  # type: ignore[no-untyped-def]
    await seed(session_factory)


@pytest.fixture(scope="module")
def client(_seed_db) -> Iterator[TestClient]:  # type: ignore[no-untyped-def]
    """Cliente module-scoped — el `create_app()` crea un AsyncEngine que
    se atacha al event loop del primer test; reusarlo entre tests evita
    el `Event loop is closed` cuando otro test abre uno nuevo."""
    yield TestClient(create_app())


# ===========================================================================
# Taxonomy
# ===========================================================================


def test_categories_requires_auth(client: TestClient) -> None:
    assert client.get("/categories").status_code == 401


def test_categories_returns_8(client: TestClient) -> None:
    response = client.get("/categories", headers={"Authorization": CAPTURADOR})
    assert response.status_code == 200
    cats = response.json()
    assert len(cats) == 8
    assert {c["code"] for c in cats} == {
        "PROC", "TEC", "ARQ", "HERR", "NEG", "ENV", "EST", "CONT",
    }


def test_doc_types_returns_11(client: TestClient) -> None:
    response = client.get("/doc-types", headers={"Authorization": CAPTURADOR})
    assert response.status_code == 200
    assert len(response.json()) == 11


# ===========================================================================
# Documents
# ===========================================================================


async def _make_doc_in_db(session_factory, *, id: str, **overrides) -> None:  # type: ignore[no-untyped-def]
    """Helper para crear documentos directos en DB (más rápido que via API)."""
    defaults = {
        "id": id,
        "titulo": "Doc test",
        "carpeta": "TEC",
        "tipo": "MTEC",
        "autoritativo": False,
        "estado": "vigente",
        "autor_oid": None,
        "autor_name": "Test",
        "autor_role": "QA",
        "fecha": datetime.now(UTC),
        "revision": datetime.now(UTC),
        "version": "1.0",
        "citas": 0,
        "score": 4.0,
        "anonimizado": False,
        "fragmentos": 0,
        "paginas": 5,
        "formato": "DOCX",
        "tags": [],
        "resumen": "",
    }
    defaults.update(overrides)
    async with session_scope(session_factory) as db:
        db.add(models.DocumentModel(**defaults))


async def test_document_search_empty(client: TestClient) -> None:
    """Sin docs sembrados (más allá de los de otros tests), la búsqueda
    devuelve un response paginado válido."""
    response = client.get(
        "/documents",
        headers={"Authorization": CAPTURADOR},
        params={"limit": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert body["page"] == 1
    assert body["limit"] == 5


async def test_document_search_with_filters(
    client: TestClient, session_factory  # type: ignore[no-untyped-def]
) -> None:
    suffix = uuid.uuid4().hex[:6]
    await _make_doc_in_db(
        session_factory,
        id=f"TEC-test-{suffix}-2026-05-22",
        carpeta="TEC",
        tipo="MTEC",
    )
    response = client.get(
        "/documents",
        headers={"Authorization": CAPTURADOR},
        params={"carpetas": "TEC", "tipos": "MTEC", "limit": 100},
    )
    assert response.status_code == 200
    body = response.json()
    ids = [d["id"] for d in body["items"]]
    assert f"TEC-test-{suffix}-2026-05-22" in ids


async def test_document_detail_returns_404_for_unknown(client: TestClient) -> None:
    response = client.get(
        "/documents/no-existe-xyz",
        headers={"Authorization": CAPTURADOR},
    )
    assert response.status_code == 404


async def test_set_authoritative_capturador_forbidden(
    client: TestClient, session_factory  # type: ignore[no-untyped-def]
) -> None:
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"TEC-test-{suffix}-2026-05-22"
    await _make_doc_in_db(session_factory, id=doc_id, autoritativo=False)

    response = client.patch(
        f"/documents/{doc_id}/authoritative",
        headers={"Authorization": CAPTURADOR},
        json={"value": True},
    )
    assert response.status_code == 403


async def test_set_authoritative_gklead_ok(
    client: TestClient, session_factory  # type: ignore[no-untyped-def]
) -> None:
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"TEC-test-{suffix}-2026-05-22"
    await _make_doc_in_db(session_factory, id=doc_id, autoritativo=False)

    response = client.patch(
        f"/documents/{doc_id}/authoritative",
        headers={"Authorization": GKLEAD},
        json={"value": True},
    )
    assert response.status_code == 200
    assert response.json()["autoritativo"] is True


async def test_set_authoritative_owner_on_own_folder(
    client: TestClient, session_factory  # type: ignore[no-untyped-def]
) -> None:
    # Owner seed tiene carpetas_owned=[TEC, ARQ] — un doc TEC pasa.
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"TEC-test-{suffix}-2026-05-22"
    await _make_doc_in_db(session_factory, id=doc_id, carpeta="TEC")

    response = client.patch(
        f"/documents/{doc_id}/authoritative",
        headers={"Authorization": OWNER},
        json={"value": True},
    )
    assert response.status_code == 200


async def test_set_authoritative_owner_on_other_folder_forbidden(
    client: TestClient, session_factory  # type: ignore[no-untyped-def]
) -> None:
    # Owner NO tiene PROC en sus carpetas_owned → 403.
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"PROC-test-{suffix}-2026-05-22"
    await _make_doc_in_db(session_factory, id=doc_id, carpeta="PROC")

    response = client.patch(
        f"/documents/{doc_id}/authoritative",
        headers={"Authorization": OWNER},
        json={"value": True},
    )
    assert response.status_code == 403


# ===========================================================================
# Sessions
# ===========================================================================


def test_create_session_201(client: TestClient) -> None:
    response = client.post(
        "/sessions",
        headers={"Authorization": CAPTURADOR},
        json={"mode": "captura"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["mode"] == "captura"
    assert body["status"] == "active"
    assert body["owner_oid"] == "stub-capturador-00000000"
    assert body["title"] == "Nueva captura"


def test_create_and_get_session_round_trip(client: TestClient) -> None:
    created = client.post(
        "/sessions",
        headers={"Authorization": CAPTURADOR},
        json={"mode": "consulta", "title": "Test query"},
    ).json()

    response = client.get(
        f"/sessions/{created['id']}",
        headers={"Authorization": CAPTURADOR},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Test query"


def test_get_session_idor_returns_404_for_other_owner(client: TestClient) -> None:
    """Owner crea sesión, Capturador intenta leerla → 404 (no diferenciamos)."""
    created = client.post(
        "/sessions",
        headers={"Authorization": OWNER},
        json={"mode": "captura"},
    ).json()

    response = client.get(
        f"/sessions/{created['id']}",
        headers={"Authorization": CAPTURADOR},
    )
    assert response.status_code == 404


def test_pause_session(client: TestClient) -> None:
    created = client.post(
        "/sessions",
        headers={"Authorization": CAPTURADOR},
        json={"mode": "captura"},
    ).json()

    response = client.patch(
        f"/sessions/{created['id']}/status",
        headers={"Authorization": CAPTURADOR},
        json={"status": "paused"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "paused"


def test_delete_session_returns_204(client: TestClient) -> None:
    created = client.post(
        "/sessions",
        headers={"Authorization": CAPTURADOR},
        json={"mode": "captura"},
    ).json()

    response = client.delete(
        f"/sessions/{created['id']}",
        headers={"Authorization": CAPTURADOR},
    )
    assert response.status_code == 204

    # Verificar que ya no se encuentra.
    response = client.get(
        f"/sessions/{created['id']}",
        headers={"Authorization": CAPTURADOR},
    )
    assert response.status_code == 404


def test_list_sessions_only_returns_own(client: TestClient) -> None:
    # Crear 1 sesión como Owner y 1 como Capturador.
    client.post(
        "/sessions",
        headers={"Authorization": OWNER},
        json={"mode": "captura"},
    )
    capt_session = client.post(
        "/sessions",
        headers={"Authorization": CAPTURADOR},
        json={"mode": "captura"},
    ).json()

    response = client.get(
        "/sessions",
        headers={"Authorization": CAPTURADOR},
    )
    assert response.status_code == 200
    body = response.json()
    own_ids = {s["id"] for s in body}
    assert capt_session["id"] in own_ids
    assert all(s["owner_oid"] == "stub-capturador-00000000" for s in body)


# ===========================================================================
# My captures
# ===========================================================================


def test_my_captures_returns_stats(client: TestClient) -> None:
    """Sin docs del Capturador en DB devuelve totals en 0."""
    response = client.get(
        "/my-captures",
        headers={"Authorization": CAPTURADOR},
    )
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "stats" in body
    assert body["stats"]["total_captures"] == len(body["items"])


# ===========================================================================
# Dashboard
# ===========================================================================


def test_dashboard_activity_empty(client: TestClient) -> None:
    response = client.get(
        "/dashboard/activity",
        headers={"Authorization": CAPTURADOR},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_dashboard_hot_topics_empty(client: TestClient) -> None:
    response = client.get(
        "/dashboard/hot-topics",
        headers={"Authorization": CAPTURADOR},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
