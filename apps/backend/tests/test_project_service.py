"""Tests de `ProjectService` con fakes (Fase 9.2).

Cubre:
- CRUD de proyectos (create / list_visible / get / update / archive).
- Memberships (add / remove / list).
- Matriz de autorización completa por rol global + per-proyecto.
- Validaciones del dominio (slug único, owner_email inexistente,
  no archivar gk-general, no remover al owner del proyecto).

Sin DB — usa fakes en memoria que implementan los Protocols del puerto.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from sqa_kb.domain.entities import (
    Project,
    ProjectMember,
    User,
)
from sqa_kb.domain.errors import ForbiddenError, NotFoundError, ValidationError
from sqa_kb.domain.value_objects import ProjectMemberRole, RoleId
from sqa_kb.services.project_service import (
    AddMemberInput,
    CreateProjectInput,
    PermissionPolicy,
    ProjectService,
    UpdateProjectInput,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _user(oid: str, *, role: RoleId = RoleId.COLABORADOR, email: str | None = None) -> User:
    return User(
        oid=oid,
        email=email or f"{oid}@sqa.co",
        name=f"User {oid}",
        role_id=role,
        created_at=_now(),
        updated_at=_now(),
    )


# ===========================================================================
# Fakes
# ===========================================================================


class FakeProjectRepo:
    """In-memory ProjectRepository."""

    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}
        self.members: dict[tuple[str, str], ProjectMember] = {}

    async def create(self, project: Project) -> Project:
        self.projects[project.id] = project
        return project

    async def get(self, project_id: str) -> Project | None:
        return self.projects.get(project_id)

    async def get_by_slug(self, slug: str) -> Project | None:
        for p in self.projects.values():
            if p.slug == slug:
                return p
        return None

    async def list_all(self) -> Sequence[Project]:
        return list(self.projects.values())

    async def list_for_user(self, user_oid: str) -> Sequence[Project]:
        member_pids = {pid for (pid, uoid) in self.members if uoid == user_oid}
        return [self.projects[pid] for pid in member_pids if pid in self.projects]

    async def update(self, project: Project) -> Project:
        if project.id not in self.projects:
            raise NotFoundError(f"Proyecto {project.id} no encontrado")
        self.projects[project.id] = project
        return project

    async def archive(self, project_id: str) -> Project:
        if project_id not in self.projects:
            raise NotFoundError(f"Proyecto {project_id} no encontrado")
        existing = self.projects[project_id]
        archived = existing.model_copy(update={"archived_at": _now()})
        self.projects[project_id] = archived
        return archived

    async def add_member(self, member: ProjectMember) -> ProjectMember:
        self.members[(member.project_id, member.user_oid)] = member
        return member

    async def remove_member(self, project_id: str, user_oid: str) -> None:
        self.members.pop((project_id, user_oid), None)

    async def list_members(self, project_id: str) -> Sequence[ProjectMember]:
        return [m for (pid, _), m in self.members.items() if pid == project_id]

    async def get_membership(
        self, project_id: str, user_oid: str
    ) -> ProjectMember | None:
        return self.members.get((project_id, user_oid))


class FakeUserRepo:
    def __init__(self, users: list[User]) -> None:
        self.users = {u.oid: u for u in users}

    async def upsert_from_token(self, user: User) -> User:
        self.users[user.oid] = user
        return user

    async def get_by_oid(self, oid: str) -> User | None:
        return self.users.get(oid)

    async def get_by_email(self, email: str) -> User | None:
        for u in self.users.values():
            if u.email.lower() == email.lower():
                return u
        return None

    async def list_by_role(self, role: str, *, limit: int = 50) -> Sequence[User]:
        return [u for u in self.users.values() if u.role_id == role][:limit]


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def gk_lead() -> User:
    return _user("oid-gk", role=RoleId.GKLEAD, email="gk@sqa.co")


@pytest.fixture
def alice() -> User:
    """colaborador genérico — Alice."""
    return _user("oid-alice", role=RoleId.COLABORADOR, email="alice@sqa.co")


@pytest.fixture
def bob() -> User:
    """Otro colaborador — Bob."""
    return _user("oid-bob", role=RoleId.COLABORADOR, email="bob@sqa.co")


@pytest.fixture
def repos(gk_lead, alice, bob):
    project_repo = FakeProjectRepo()
    user_repo = FakeUserRepo([gk_lead, alice, bob])
    return project_repo, user_repo


@pytest.fixture
def service(repos):
    project_repo, user_repo = repos
    return ProjectService(project_repo, user_repo)


# ===========================================================================
# PermissionPolicy
# ===========================================================================


@pytest.mark.asyncio
async def test_policy_gk_lead_can_everything(repos, gk_lead) -> None:
    project_repo, _ = repos
    policy = PermissionPolicy(project_repo)
    m = await policy.resolve(gk_lead, "any-project-id")
    assert m.is_gk_lead
    assert m.can_approve
    assert m.can_manage_members


@pytest.mark.asyncio
async def test_policy_colaborador_without_membership_cannot(repos, alice) -> None:
    project_repo, _ = repos
    policy = PermissionPolicy(project_repo)
    m = await policy.resolve(alice, "some-project")
    assert not m.can_read
    assert not m.can_approve


@pytest.mark.asyncio
async def test_policy_member_can_read_not_approve(repos, alice) -> None:
    project_repo, _ = repos
    await project_repo.add_member(
        ProjectMember(
            project_id="proj-1",
            user_oid=alice.oid,
            role=ProjectMemberRole.MEMBER,
            added_at=_now(),
        )
    )
    policy = PermissionPolicy(project_repo)
    m = await policy.resolve(alice, "proj-1")
    assert m.can_read
    assert m.can_ingest
    assert not m.can_approve


# ===========================================================================
# create
# ===========================================================================


@pytest.mark.asyncio
async def test_create_project_by_gklead_assigns_owner(service, gk_lead, alice) -> None:
    project = await service.create(
        gk_lead,
        CreateProjectInput(
            slug="cliente-acme",
            name="Cliente ACME",
            description="Banking client",
            owner_email=alice.email,
        ),
    )
    assert project.slug == "cliente-acme"
    assert project.owner_oid == alice.oid

    # Y la membership de Alice como project_owner debe existir.
    members = await service.list_members(gk_lead, project.id)
    assert len(members) == 1
    assert members[0].user_oid == alice.oid
    assert members[0].role == ProjectMemberRole.PROJECT_OWNER


@pytest.mark.asyncio
async def test_create_project_forbidden_for_colaborador(service, alice) -> None:
    with pytest.raises(ForbiddenError, match="Solo GK Lead"):
        await service.create(
            alice,
            CreateProjectInput(
                slug="proj-x", name="X", description="", owner_email=alice.email
            ),
        )


@pytest.mark.asyncio
async def test_create_project_duplicate_slug_rejected(service, gk_lead, alice) -> None:
    await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-dup", name="A", description="", owner_email=alice.email),
    )
    with pytest.raises(ValidationError, match="ya está en uso"):
        await service.create(
            gk_lead,
            CreateProjectInput(slug="proj-dup", name="B", description="", owner_email=alice.email),
        )


@pytest.mark.asyncio
async def test_create_project_unknown_owner_email_404(service, gk_lead) -> None:
    with pytest.raises(NotFoundError, match="no encontrado"):
        await service.create(
            gk_lead,
            CreateProjectInput(
                slug="proj-z", name="Z", description="", owner_email="no-existe@sqa.co"
            ),
        )


# ===========================================================================
# list_visible
# ===========================================================================


@pytest.mark.asyncio
async def test_list_visible_gklead_sees_all(service, gk_lead, alice) -> None:
    await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-a", name="A", description="", owner_email=alice.email),
    )
    await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-b", name="B", description="", owner_email=alice.email),
    )
    projects = await service.list_visible(gk_lead)
    assert len(projects) == 2


@pytest.mark.asyncio
async def test_list_visible_colaborador_sees_only_member_projects(
    service, gk_lead, alice, bob
) -> None:
    # Alice es owner de A; Bob no es miembro de nada.
    await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-a", name="A", description="", owner_email=alice.email),
    )
    alice_visible = await service.list_visible(alice)
    bob_visible = await service.list_visible(bob)
    assert len(alice_visible) == 1
    assert len(bob_visible) == 0


# ===========================================================================
# get + IDOR
# ===========================================================================


@pytest.mark.asyncio
async def test_get_project_not_member_returns_404(
    service, gk_lead, alice, bob
) -> None:
    project = await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-a", name="A", description="", owner_email=alice.email),
    )
    # Bob no es miembro → 404 (no diferenciamos 404 de 403 por IDOR).
    with pytest.raises(NotFoundError):
        await service.get(bob, project.id)


@pytest.mark.asyncio
async def test_get_project_gklead_bypasses_membership(service, gk_lead, alice) -> None:
    project = await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-a", name="A", description="", owner_email=alice.email),
    )
    # gk_lead no es miembro pero ve por privilegio.
    got = await service.get(gk_lead, project.id)
    assert got.id == project.id


# ===========================================================================
# update
# ===========================================================================


@pytest.mark.asyncio
async def test_update_by_project_owner(service, gk_lead, alice) -> None:
    project = await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-a", name="Old", description="", owner_email=alice.email),
    )
    updated = await service.update(
        alice, project.id, UpdateProjectInput(name="New name")
    )
    assert updated.name == "New name"


@pytest.mark.asyncio
async def test_update_by_member_forbidden(service, gk_lead, alice, bob, repos) -> None:
    project_repo, _ = repos
    project = await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-a", name="A", description="", owner_email=alice.email),
    )
    # Bob es member, no owner.
    await project_repo.add_member(
        ProjectMember(
            project_id=project.id,
            user_oid=bob.oid,
            role=ProjectMemberRole.MEMBER,
            added_at=_now(),
        )
    )
    with pytest.raises(ForbiddenError):
        await service.update(bob, project.id, UpdateProjectInput(name="hax"))


# ===========================================================================
# archive
# ===========================================================================


@pytest.mark.asyncio
async def test_archive_by_gklead(service, gk_lead, alice) -> None:
    project = await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-a", name="A", description="", owner_email=alice.email),
    )
    archived = await service.archive(gk_lead, project.id)
    assert archived.archived_at is not None


@pytest.mark.asyncio
async def test_archive_gk_general_rejected(service, gk_lead, alice, repos) -> None:
    """No se puede archivar el proyecto raíz."""
    project_repo, _ = repos
    project_repo.projects["proj-root"] = Project(
        id="proj-root",
        slug="gk-general",
        name="GK General",
        owner_oid=gk_lead.oid,
        created_at=_now(),
    )
    with pytest.raises(ValidationError, match="proyecto raíz"):
        await service.archive(gk_lead, "proj-root")


@pytest.mark.asyncio
async def test_archive_by_colaborador_forbidden(service, gk_lead, alice) -> None:
    project = await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-a", name="A", description="", owner_email=alice.email),
    )
    with pytest.raises(ForbiddenError):
        await service.archive(alice, project.id)


# ===========================================================================
# members
# ===========================================================================


@pytest.mark.asyncio
async def test_add_member_by_owner(service, gk_lead, alice, bob) -> None:
    project = await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-a", name="A", description="", owner_email=alice.email),
    )
    added = await service.add_member(
        alice,
        project.id,
        AddMemberInput(email=bob.email, role=ProjectMemberRole.MEMBER),
    )
    assert added.user_oid == bob.oid
    assert added.role == ProjectMemberRole.MEMBER


@pytest.mark.asyncio
async def test_add_member_by_member_forbidden(
    service, gk_lead, alice, bob, repos
) -> None:
    project_repo, _ = repos
    project = await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-a", name="A", description="", owner_email=alice.email),
    )
    # Bob entra como member.
    await project_repo.add_member(
        ProjectMember(
            project_id=project.id,
            user_oid=bob.oid,
            role=ProjectMemberRole.MEMBER,
            added_at=_now(),
        )
    )
    # Bob intenta añadir a otro — denied.
    with pytest.raises(ForbiddenError):
        await service.add_member(
            bob,
            project.id,
            AddMemberInput(email="charlie@sqa.co", role=ProjectMemberRole.MEMBER),
        )


@pytest.mark.asyncio
async def test_remove_member_by_owner(service, gk_lead, alice, bob) -> None:
    project = await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-a", name="A", description="", owner_email=alice.email),
    )
    await service.add_member(
        alice, project.id, AddMemberInput(email=bob.email, role=ProjectMemberRole.MEMBER)
    )
    await service.remove_member(alice, project.id, bob.oid)
    members = await service.list_members(alice, project.id)
    assert bob.oid not in [m.user_oid for m in members]


@pytest.mark.asyncio
async def test_cannot_remove_project_owner(service, gk_lead, alice) -> None:
    project = await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-a", name="A", description="", owner_email=alice.email),
    )
    with pytest.raises(ValidationError, match="owner"):
        await service.remove_member(gk_lead, project.id, alice.oid)


@pytest.mark.asyncio
async def test_add_member_idempotent_updates_role(
    service, gk_lead, alice, bob
) -> None:
    project = await service.create(
        gk_lead,
        CreateProjectInput(slug="proj-a", name="A", description="", owner_email=alice.email),
    )
    await service.add_member(
        alice, project.id, AddMemberInput(email=bob.email, role=ProjectMemberRole.MEMBER)
    )
    promoted = await service.add_member(
        alice,
        project.id,
        AddMemberInput(email=bob.email, role=ProjectMemberRole.PROJECT_OWNER),
    )
    assert promoted.role == ProjectMemberRole.PROJECT_OWNER
