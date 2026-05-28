"""Tests del dominio multi-tenant (Fase 9.1).

Cobertura:
- `Project` entity: slug pattern, archived flag.
- `ProjectMember` entity.
- `ProjectMembership` value object: matriz `can_*` para los 4 escenarios
  ortogonales (global × per-proyecto).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sqa_kb.domain.entities import (
    Project,
    ProjectMember,
    ProjectMembership,
)
from sqa_kb.domain.errors import ValidationError
from sqa_kb.domain.value_objects import ProjectMemberRole, RoleId


def _now() -> datetime:
    return datetime.now(UTC)


# ===========================================================================
# Project
# ===========================================================================


def test_project_minimal_valid() -> None:
    p = Project(
        id="proj-1",
        slug="cliente-acme",
        name="Cliente ACME",
        owner_oid="oid-gk",
        created_at=_now(),
    )
    assert p.archived_at is None
    assert p.description == ""


def test_project_slug_must_be_lowercase_kebab() -> None:
    """El slug es URL-safe: lowercase, kebab-case, sin acentos ni símbolos."""
    with pytest.raises((ValidationError, ValueError)):
        Project(
            id="proj-1",
            slug="Cliente_ACME",  # invalido: mayúsculas + underscore
            name="X",
            owner_oid="oid-gk",
            created_at=_now(),
        )


def test_project_slug_min_length_two() -> None:
    with pytest.raises((ValidationError, ValueError)):
        Project(
            id="proj-1",
            slug="a",  # demasiado corto
            name="X",
            owner_oid="oid-gk",
            created_at=_now(),
        )


def test_project_with_archived_at() -> None:
    archived = _now()
    p = Project(
        id="proj-1",
        slug="legacy-x",
        name="Legacy X",
        owner_oid="oid-gk",
        created_at=_now(),
        archived_at=archived,
    )
    assert p.archived_at == archived


# ===========================================================================
# ProjectMember
# ===========================================================================


def test_project_member_with_owner_role() -> None:
    m = ProjectMember(
        project_id="proj-1",
        user_oid="oid-camila",
        role=ProjectMemberRole.PROJECT_OWNER,
        added_at=_now(),
    )
    assert m.role == ProjectMemberRole.PROJECT_OWNER


def test_project_member_with_member_role() -> None:
    m = ProjectMember(
        project_id="proj-1",
        user_oid="oid-lucia",
        role=ProjectMemberRole.MEMBER,
        added_at=_now(),
    )
    assert m.role == ProjectMemberRole.MEMBER


# ===========================================================================
# ProjectMembership — matriz de capacidades (los 4 escenarios)
# ===========================================================================


def _membership(
    *, global_role: RoleId, project_role: ProjectMemberRole | None
) -> ProjectMembership:
    return ProjectMembership(
        project_id="proj-1",
        user_oid="oid-x",
        global_role=global_role,
        project_role=project_role,
    )


def test_membership_gk_lead_can_do_everything() -> None:
    """GK Lead: super-admin. Todas las capacidades True aunque NO sea miembro."""
    m = _membership(global_role=RoleId.GKLEAD, project_role=None)
    assert m.is_gk_lead
    assert m.can_read
    assert m.can_ingest
    assert m.can_approve
    assert m.can_manage_members
    assert m.can_edit_taxonomy
    assert m.can_run_documentation_session


def test_membership_project_owner_can_govern_project() -> None:
    """project_owner: gobierna su proyecto, pero NO es admin global."""
    m = _membership(
        global_role=RoleId.COLABORADOR,
        project_role=ProjectMemberRole.PROJECT_OWNER,
    )
    assert not m.is_gk_lead
    assert m.is_project_owner
    assert m.can_read
    assert m.can_ingest
    assert m.can_approve
    assert m.can_manage_members
    assert m.can_edit_taxonomy
    assert m.can_run_documentation_session


def test_membership_member_can_read_and_ingest_only() -> None:
    """member: lee y aporta. NO aprueba ni administra."""
    m = _membership(
        global_role=RoleId.COLABORADOR,
        project_role=ProjectMemberRole.MEMBER,
    )
    assert m.can_read
    assert m.can_ingest
    assert not m.can_approve
    assert not m.can_manage_members
    assert not m.can_edit_taxonomy
    assert not m.can_run_documentation_session


def test_membership_colaborador_without_membership_can_nothing() -> None:
    """colaborador sin membership en ESE proyecto: cero acceso."""
    m = _membership(global_role=RoleId.COLABORADOR, project_role=None)
    assert not m.can_read
    assert not m.can_ingest
    assert not m.can_approve
    assert not m.can_manage_members
    assert not m.can_edit_taxonomy
    assert not m.can_run_documentation_session


def test_membership_gk_lead_overrides_membership() -> None:
    """GK Lead conserva sus poderes aunque tenga membership de member."""
    m = _membership(
        global_role=RoleId.GKLEAD,
        project_role=ProjectMemberRole.MEMBER,
    )
    assert m.is_gk_lead
    assert m.can_approve
    assert m.can_manage_members
