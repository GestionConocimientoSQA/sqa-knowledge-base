"""Tests de `ProjectTaxonomyService` con fakes (Fase 9.4).

Cubre:
- Resolución efectiva (global, sin overrides → global tal cual).
- Override de label (global ARQ con label custom del proyecto).
- Extensión nueva (código que no existe en global, exclusivo del proyecto).
- Override + extensión en el mismo proyecto.
- Autorización: lectura requiere can_read; mutaciones requieren can_edit.
- Validaciones del dominio (code/label no vacío).
- Casos límite (override apuntando a código inexistente, extensión con
  código global ya existente).

Sin DB. Fakes in-memory.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from sqa_kb.domain.entities import (
    Category,
    DocType,
    Project,
    ProjectCategory,
    ProjectDocType,
    User,
)
from sqa_kb.domain.errors import ForbiddenError, NotFoundError, ValidationError
from sqa_kb.domain.value_objects import RoleId
from sqa_kb.services.project_taxonomy_service import (
    CategoryInput,
    DocTypeInput,
    ProjectTaxonomyService,
)
from tests.test_project_service import (
    FakeProjectRepo,
    _now,
    _user,
)


# ===========================================================================
# Fakes
# ===========================================================================


class FakeTaxonomyRepo:
    """Catálogo global — 2 carpetas + 2 tipos para tests."""

    def __init__(self) -> None:
        self._cats = [
            Category(code="TEC", label="Conocimiento Técnico"),
            Category(code="PROC", label="Procesos de Pruebas"),
        ]
        self._types = [
            DocType(code="POL", label="Política"),
            DocType(code="PROC", label="Procedimiento"),
        ]

    async def list_categories(self) -> Sequence[Category]:
        return list(self._cats)

    async def list_doc_types(self) -> Sequence[DocType]:
        return list(self._types)


class FakeProjectTaxonomyRepo:
    def __init__(self) -> None:
        self.cats: dict[tuple[str, str], ProjectCategory] = {}
        self.types: dict[tuple[str, str], ProjectDocType] = {}

    async def list_categories(self, project_id: str) -> Sequence[ProjectCategory]:
        return [c for (pid, _), c in self.cats.items() if pid == project_id]

    async def list_doc_types(self, project_id: str) -> Sequence[ProjectDocType]:
        return [t for (pid, _), t in self.types.items() if pid == project_id]

    async def upsert_category(self, c: ProjectCategory) -> ProjectCategory:
        self.cats[(c.project_id, c.code)] = c
        return c

    async def upsert_doc_type(self, t: ProjectDocType) -> ProjectDocType:
        self.types[(t.project_id, t.code)] = t
        return t

    async def delete_category(self, project_id: str, code: str) -> None:
        self.cats.pop((project_id, code), None)

    async def delete_doc_type(self, project_id: str, code: str) -> None:
        self.types.pop((project_id, code), None)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def gk_lead() -> User:
    return _user("oid-gk", role=RoleId.GKLEAD, email="gk@sqa.co")


@pytest.fixture
def alice() -> User:
    return _user("oid-alice", role=RoleId.COLABORADOR, email="alice@sqa.co")


@pytest.fixture
def bob() -> User:
    return _user("oid-bob", role=RoleId.COLABORADOR, email="bob@sqa.co")


@pytest.fixture
def project_id() -> str:
    return "proj-acme"


@pytest.fixture
def repos(project_id, alice):
    project_repo = FakeProjectRepo()
    project_repo.projects[project_id] = Project(
        id=project_id,
        slug="acme",
        name="Cliente ACME",
        owner_oid=alice.oid,
        created_at=_now(),
    )
    # Alice como project_owner (puede editar taxonomía).
    from sqa_kb.domain.entities import ProjectMember
    from sqa_kb.domain.value_objects import ProjectMemberRole

    project_repo.members[(project_id, alice.oid)] = ProjectMember(
        project_id=project_id,
        user_oid=alice.oid,
        role=ProjectMemberRole.PROJECT_OWNER,
        added_at=_now(),
    )
    taxonomy_repo = FakeTaxonomyRepo()
    project_taxonomy_repo = FakeProjectTaxonomyRepo()
    return project_repo, taxonomy_repo, project_taxonomy_repo


@pytest.fixture
def service(repos):
    project_repo, taxonomy_repo, project_taxonomy_repo = repos
    return ProjectTaxonomyService(
        project_repo, taxonomy_repo, project_taxonomy_repo
    )


# ===========================================================================
# Resolución efectiva
# ===========================================================================


@pytest.mark.asyncio
async def test_effective_without_overrides_equals_global(
    service, alice, project_id
) -> None:
    """Proyecto sin overrides ⇒ catálogo efectivo = global tal cual."""
    eff = await service.effective(alice, project_id)
    codes = [c.code for c in eff.categories]
    assert codes == ["PROC", "TEC"]
    labels = {c.code: c.label for c in eff.categories}
    assert labels["TEC"] == "Conocimiento Técnico"


@pytest.mark.asyncio
async def test_effective_override_replaces_label(
    service, alice, project_id
) -> None:
    """Override sobre TEC ⇒ el label efectivo es el del proyecto."""
    await service.upsert_category(
        alice,
        project_id,
        CategoryInput(code="TEC", label="Tech Stack del Cliente", is_override=True),
    )
    eff = await service.effective(alice, project_id)
    labels = {c.code: c.label for c in eff.categories}
    assert labels["TEC"] == "Tech Stack del Cliente"
    # PROC sigue siendo el global.
    assert labels["PROC"] == "Procesos de Pruebas"


@pytest.mark.asyncio
async def test_effective_extension_adds_new_category(
    service, alice, project_id
) -> None:
    """Extensión con código nuevo ⇒ aparece en el catálogo efectivo."""
    await service.upsert_category(
        alice,
        project_id,
        CategoryInput(code="REG", label="Regulación", is_override=False),
    )
    eff = await service.effective(alice, project_id)
    codes = [c.code for c in eff.categories]
    assert codes == ["PROC", "REG", "TEC"]
    reg = next(c for c in eff.categories if c.code == "REG")
    assert reg.label == "Regulación"


@pytest.mark.asyncio
async def test_effective_combines_override_and_extension(
    service, alice, project_id
) -> None:
    await service.upsert_category(
        alice,
        project_id,
        CategoryInput(code="TEC", label="Tech ACME", is_override=True),
    )
    await service.upsert_category(
        alice,
        project_id,
        CategoryInput(code="REG", label="Regulación BCRA", is_override=False),
    )
    eff = await service.effective(alice, project_id)
    by_code = {c.code: c.label for c in eff.categories}
    assert by_code["TEC"] == "Tech ACME"
    assert by_code["PROC"] == "Procesos de Pruebas"
    assert by_code["REG"] == "Regulación BCRA"


@pytest.mark.asyncio
async def test_effective_doc_types_same_resolution(
    service, alice, project_id
) -> None:
    await service.upsert_doc_type(
        alice,
        project_id,
        DocTypeInput(code="POL", label="Política Corporativa", is_override=True),
    )
    await service.upsert_doc_type(
        alice,
        project_id,
        DocTypeInput(code="REG", label="Regulación", is_override=False),
    )
    eff = await service.effective(alice, project_id)
    by_code = {t.code: t.label for t in eff.doc_types}
    assert by_code["POL"] == "Política Corporativa"
    assert by_code["REG"] == "Regulación"


# ===========================================================================
# Casos límite (la regla del merge tiene ramas)
# ===========================================================================


@pytest.mark.asyncio
async def test_override_apuntando_a_codigo_inexistente_se_ignora(
    service, alice, project_id
) -> None:
    """`is_override=True` pero el code no existe en global ⇒ no se aplica."""
    await service.upsert_category(
        alice,
        project_id,
        CategoryInput(code="ZZZ", label="Inexistente", is_override=True),
    )
    eff = await service.effective(alice, project_id)
    codes = [c.code for c in eff.categories]
    # ZZZ no se agrega: ni reemplaza (no existe) ni se trata como extensión.
    assert "ZZZ" not in codes


@pytest.mark.asyncio
async def test_extension_con_codigo_global_existente_se_ignora(
    service, alice, project_id
) -> None:
    """`is_override=False` pero el code SÍ existe en global ⇒ no se aplica.
    Para customizar un global hay que usar `is_override=True`."""
    await service.upsert_category(
        alice,
        project_id,
        CategoryInput(code="TEC", label="No debería verse", is_override=False),
    )
    eff = await service.effective(alice, project_id)
    by_code = {c.code: c.label for c in eff.categories}
    # TEC mantiene el label global.
    assert by_code["TEC"] == "Conocimiento Técnico"


# ===========================================================================
# Autorización
# ===========================================================================


@pytest.mark.asyncio
async def test_effective_requires_membership_or_gk_lead(
    service, bob, project_id
) -> None:
    """Bob no es miembro ⇒ 404 (convención IDOR)."""
    with pytest.raises(NotFoundError):
        await service.effective(bob, project_id)


@pytest.mark.asyncio
async def test_effective_gk_lead_bypasses_membership(
    service, gk_lead, project_id
) -> None:
    eff = await service.effective(gk_lead, project_id)
    assert eff.project_id == project_id


@pytest.mark.asyncio
async def test_upsert_by_non_owner_member_forbidden(
    service, bob, project_id, repos
) -> None:
    """Bob como `member` (no owner) no puede editar taxonomía."""
    project_repo, _, _ = repos
    from sqa_kb.domain.entities import ProjectMember
    from sqa_kb.domain.value_objects import ProjectMemberRole

    project_repo.members[(project_id, bob.oid)] = ProjectMember(
        project_id=project_id,
        user_oid=bob.oid,
        role=ProjectMemberRole.MEMBER,
        added_at=_now(),
    )
    with pytest.raises(ForbiddenError):
        await service.upsert_category(
            bob, project_id, CategoryInput(code="X", label="X")
        )


@pytest.mark.asyncio
async def test_upsert_validates_non_empty_code_and_label(
    service, alice, project_id
) -> None:
    with pytest.raises(ValidationError):
        await service.upsert_category(
            alice, project_id, CategoryInput(code="   ", label="L")
        )
    with pytest.raises(ValidationError):
        await service.upsert_category(
            alice, project_id, CategoryInput(code="X", label="   ")
        )


# ===========================================================================
# Delete
# ===========================================================================


@pytest.mark.asyncio
async def test_delete_override_restores_global(
    service, alice, project_id
) -> None:
    """Si borro el override de TEC, vuelve a aparecer el label global."""
    await service.upsert_category(
        alice,
        project_id,
        CategoryInput(code="TEC", label="Custom", is_override=True),
    )
    eff_before = {c.code: c.label for c in (await service.effective(alice, project_id)).categories}
    assert eff_before["TEC"] == "Custom"

    await service.delete_category(alice, project_id, "TEC")

    eff_after = {c.code: c.label for c in (await service.effective(alice, project_id)).categories}
    assert eff_after["TEC"] == "Conocimiento Técnico"


@pytest.mark.asyncio
async def test_delete_extension_removes_from_effective(
    service, alice, project_id
) -> None:
    await service.upsert_category(
        alice, project_id, CategoryInput(code="REG", label="Reg")
    )
    await service.delete_category(alice, project_id, "REG")
    eff = await service.effective(alice, project_id)
    assert "REG" not in [c.code for c in eff.categories]
