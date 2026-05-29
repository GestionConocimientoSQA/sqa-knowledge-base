"""Tests HTTP del router `/projects/{id}/taxonomy` (Fase 9.4)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from sqa_kb.api.dependencies import (
    get_current_user,
    get_project_taxonomy_service,
)
from sqa_kb.domain.entities import (
    Project,
    ProjectMember,
    User,
)
from sqa_kb.domain.value_objects import ProjectMemberRole, RoleId
from sqa_kb.main import create_app
from sqa_kb.services.project_taxonomy_service import ProjectTaxonomyService
from tests.test_project_service import FakeProjectRepo, _now, _user
from tests.test_project_taxonomy_service import (
    FakeProjectTaxonomyRepo,
    FakeTaxonomyRepo,
)


_PROJECT_ID = "proj-acme"


@pytest.fixture
def gk_user() -> User:
    return _user("oid-gk", role=RoleId.GKLEAD, email="gk@sqa.co")


@pytest.fixture
def alice() -> User:
    return _user("oid-alice", role=RoleId.COLABORADOR, email="alice@sqa.co")


@pytest.fixture
def real_service(alice):
    project_repo = FakeProjectRepo()
    project_repo.projects[_PROJECT_ID] = Project(
        id=_PROJECT_ID,
        slug="acme",
        name="ACME",
        owner_oid=alice.oid,
        created_at=_now(),
    )
    project_repo.members[(_PROJECT_ID, alice.oid)] = ProjectMember(
        project_id=_PROJECT_ID,
        user_oid=alice.oid,
        role=ProjectMemberRole.PROJECT_OWNER,
        added_at=_now(),
    )
    return ProjectTaxonomyService(
        project_repo, FakeTaxonomyRepo(), FakeProjectTaxonomyRepo()
    )


@pytest.fixture
def client_as_owner(real_service, alice) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_project_taxonomy_service] = lambda: real_service
    app.dependency_overrides[get_current_user] = lambda: alice
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_as_gklead(real_service, gk_user) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_project_taxonomy_service] = lambda: real_service
    app.dependency_overrides[get_current_user] = lambda: gk_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_get_effective_returns_global_when_no_overrides(client_as_owner) -> None:
    resp = client_as_owner.get(f"/projects/{_PROJECT_ID}/taxonomy")
    assert resp.status_code == 200
    body = resp.json()
    assert body["projectId"] == _PROJECT_ID
    codes = sorted(c["code"] for c in body["categories"])
    assert codes == ["PROC", "TEC"]
    # camelCase wire.
    assert all("isProjectExtension" in c for c in body["categories"])


def test_put_override_changes_effective_label(client_as_owner) -> None:
    resp = client_as_owner.put(
        f"/projects/{_PROJECT_ID}/taxonomy/categories/TEC",
        json={"label": "Tech ACME", "isOverride": True},
    )
    assert resp.status_code == 200
    eff = client_as_owner.get(f"/projects/{_PROJECT_ID}/taxonomy").json()
    by_code = {c["code"]: c["label"] for c in eff["categories"]}
    assert by_code["TEC"] == "Tech ACME"


def test_put_extension_appears_in_effective(client_as_owner) -> None:
    resp = client_as_owner.put(
        f"/projects/{_PROJECT_ID}/taxonomy/categories/REG",
        json={"label": "Regulación BCRA", "isOverride": False},
    )
    assert resp.status_code == 200
    eff = client_as_owner.get(f"/projects/{_PROJECT_ID}/taxonomy").json()
    reg = next(c for c in eff["categories"] if c["code"] == "REG")
    assert reg["isProjectExtension"] is True
    assert reg["label"] == "Regulación BCRA"


def test_delete_override_restores_global(client_as_owner) -> None:
    client_as_owner.put(
        f"/projects/{_PROJECT_ID}/taxonomy/categories/TEC",
        json={"label": "Custom", "isOverride": True},
    )
    resp = client_as_owner.delete(f"/projects/{_PROJECT_ID}/taxonomy/categories/TEC")
    assert resp.status_code == 204
    eff = client_as_owner.get(f"/projects/{_PROJECT_ID}/taxonomy").json()
    by_code = {c["code"]: c["label"] for c in eff["categories"]}
    assert by_code["TEC"] == "Conocimiento Técnico"


def test_overrides_list_only_project_specific(client_as_owner) -> None:
    client_as_owner.put(
        f"/projects/{_PROJECT_ID}/taxonomy/categories/REG",
        json={"label": "Reg"},
    )
    resp = client_as_owner.get(f"/projects/{_PROJECT_ID}/taxonomy/overrides")
    assert resp.status_code == 200
    body = resp.json()
    cat_codes = [c["code"] for c in body["categories"]]
    # Solo REG (no incluye TEC/PROC del global).
    assert cat_codes == ["REG"]


def test_doc_type_upsert_and_delete(client_as_owner) -> None:
    resp = client_as_owner.put(
        f"/projects/{_PROJECT_ID}/taxonomy/doc-types/REG",
        json={"label": "Regulación BCRA"},
    )
    assert resp.status_code == 200
    resp = client_as_owner.delete(f"/projects/{_PROJECT_ID}/taxonomy/doc-types/REG")
    assert resp.status_code == 204


def test_gk_lead_can_edit_taxonomy_of_any_project(client_as_gklead) -> None:
    """GK Lead opera sin necesidad de membership."""
    resp = client_as_gklead.put(
        f"/projects/{_PROJECT_ID}/taxonomy/categories/REG",
        json={"label": "Reg"},
    )
    assert resp.status_code == 200
