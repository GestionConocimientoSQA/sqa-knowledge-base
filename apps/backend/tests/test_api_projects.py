"""Tests HTTP del router `/projects` (Fase 9.2).

Cubre el wire FastAPI: serialización camelCase, status codes correctos,
validación de Pydantic (slug pattern, email), errores del servicio
mapeados a 4xx. La lógica fina del servicio ya está en
`test_project_service.py`; acá solo validamos el adapter HTTP.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from sqa_kb.api.dependencies import (
    get_current_user,
    get_project_service,
)
from sqa_kb.domain.entities import User
from sqa_kb.domain.value_objects import ProjectMemberRole, RoleId
from sqa_kb.main import create_app
from sqa_kb.services.project_service import (
    AddMemberInput,
    CreateProjectInput,
    ProjectService,
    UpdateProjectInput,
)
from tests.test_project_service import FakeProjectRepo, FakeUserRepo, _now, _user


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def gk_user() -> User:
    return _user("oid-gk", role=RoleId.GKLEAD, email="gk@sqa.co")


@pytest.fixture
def alice() -> User:
    return _user("oid-alice", role=RoleId.COLABORADOR, email="alice@sqa.co")


@pytest.fixture
def real_service(gk_user, alice):
    """ProjectService real con fakes de repos — la única diferencia con el
    test del service es que acá agregamos auth via TestClient."""
    project_repo = FakeProjectRepo()
    user_repo = FakeUserRepo([gk_user, alice])
    return ProjectService(project_repo, user_repo)


@pytest.fixture
def client(real_service, gk_user) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_project_service] = lambda: real_service
    app.dependency_overrides[get_current_user] = lambda: gk_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def colaborador_client(real_service, alice) -> Iterator[TestClient]:
    """Mismo servicio pero el current_user es un colaborador."""
    app = create_app()
    app.dependency_overrides[get_project_service] = lambda: real_service
    app.dependency_overrides[get_current_user] = lambda: alice
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ===========================================================================
# POST /projects
# ===========================================================================


def test_create_project_returns_201_with_camelcase(client) -> None:
    resp = client.post(
        "/projects",
        json={
            "slug": "cliente-acme",
            "name": "Cliente ACME",
            "description": "Banking client",
            "ownerEmail": "alice@sqa.co",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "cliente-acme"
    # camelCase en wire
    assert "ownerOid" in body
    assert "createdAt" in body


def test_create_project_invalid_slug_422(client) -> None:
    resp = client.post(
        "/projects",
        json={
            "slug": "INVALID-UPPERCASE",
            "name": "X",
            "description": "",
            "ownerEmail": "alice@sqa.co",
        },
    )
    assert resp.status_code == 422


def test_create_project_invalid_email_422(client) -> None:
    resp = client.post(
        "/projects",
        json={
            "slug": "cliente-x",
            "name": "X",
            "description": "",
            "ownerEmail": "not-an-email",
        },
    )
    assert resp.status_code == 422


def test_create_project_unknown_owner_404(client) -> None:
    resp = client.post(
        "/projects",
        json={
            "slug": "cliente-y",
            "name": "Y",
            "description": "",
            "ownerEmail": "no-existe@sqa.co",
        },
    )
    assert resp.status_code == 404


def test_create_project_as_colaborador_forbidden(colaborador_client) -> None:
    resp = colaborador_client.post(
        "/projects",
        json={
            "slug": "cliente-z",
            "name": "Z",
            "description": "",
            "ownerEmail": "alice@sqa.co",
        },
    )
    assert resp.status_code == 403


# ===========================================================================
# GET /projects
# ===========================================================================


def test_list_projects_returns_array(client) -> None:
    # Creamos 2 proyectos primero.
    for slug in ["proj-1", "proj-2"]:
        client.post(
            "/projects",
            json={
                "slug": slug,
                "name": slug,
                "description": "",
                "ownerEmail": "alice@sqa.co",
            },
        )
    resp = client.get("/projects")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 2


# ===========================================================================
# GET/PUT/DELETE /projects/{id}
# ===========================================================================


def test_get_project_detail(client) -> None:
    created = client.post(
        "/projects",
        json={
            "slug": "proj-detail",
            "name": "Detail",
            "description": "",
            "ownerEmail": "alice@sqa.co",
        },
    ).json()
    resp = client.get(f"/projects/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["slug"] == "proj-detail"


def test_update_project_changes_name(client) -> None:
    created = client.post(
        "/projects",
        json={
            "slug": "proj-upd",
            "name": "Old",
            "description": "",
            "ownerEmail": "alice@sqa.co",
        },
    ).json()
    resp = client.put(
        f"/projects/{created['id']}",
        json={"name": "New Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


def test_archive_project_sets_archivedAt(client) -> None:
    created = client.post(
        "/projects",
        json={
            "slug": "proj-arc",
            "name": "ToArchive",
            "description": "",
            "ownerEmail": "alice@sqa.co",
        },
    ).json()
    resp = client.delete(f"/projects/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["archivedAt"] is not None


# ===========================================================================
# Members
# ===========================================================================


def test_list_members_includes_owner(client) -> None:
    created = client.post(
        "/projects",
        json={
            "slug": "proj-mem",
            "name": "M",
            "description": "",
            "ownerEmail": "alice@sqa.co",
        },
    ).json()
    resp = client.get(f"/projects/{created['id']}/members")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["userOid"] == "oid-alice"
    assert body[0]["role"] == "project_owner"


def test_add_member_returns_201(client, real_service) -> None:
    # Sumo un tercer usuario al fake user repo.
    bob = _user("oid-bob", role=RoleId.COLABORADOR, email="bob@sqa.co")
    real_service._users.users[bob.oid] = bob  # type: ignore[attr-defined]

    created = client.post(
        "/projects",
        json={
            "slug": "proj-addm",
            "name": "M",
            "description": "",
            "ownerEmail": "alice@sqa.co",
        },
    ).json()
    resp = client.post(
        f"/projects/{created['id']}/members",
        json={"email": "bob@sqa.co", "role": "member"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["userOid"] == bob.oid
    assert body["role"] == "member"


def test_remove_member_returns_204(client, real_service) -> None:
    bob = _user("oid-bob", role=RoleId.COLABORADOR, email="bob@sqa.co")
    real_service._users.users[bob.oid] = bob  # type: ignore[attr-defined]

    created = client.post(
        "/projects",
        json={
            "slug": "proj-rmm",
            "name": "M",
            "description": "",
            "ownerEmail": "alice@sqa.co",
        },
    ).json()
    client.post(
        f"/projects/{created['id']}/members",
        json={"email": "bob@sqa.co", "role": "member"},
    )
    resp = client.delete(f"/projects/{created['id']}/members/{bob.oid}")
    assert resp.status_code == 204


def test_cannot_remove_owner_via_endpoint(client) -> None:
    created = client.post(
        "/projects",
        json={
            "slug": "proj-rmo",
            "name": "M",
            "description": "",
            "ownerEmail": "alice@sqa.co",
        },
    ).json()
    resp = client.delete(f"/projects/{created['id']}/members/oid-alice")
    # ValidationError → 422 por el handler global
    assert resp.status_code == 422
