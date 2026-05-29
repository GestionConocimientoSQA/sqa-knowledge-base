"""Tests de `DocumentationSessionService` (Fase 9.5).

Cubre:
- start: crea sesión en step `context`.
- submit_step: avanza al siguiente, valida payload, rechaza saltos.
- finalize: genera N docs `.md` y los manda a ingesta.
- abandon: cierra sin generar docs.
- Autorización: solo project_owner / gk_lead pueden editar.
- Renderers de markdown por step (funciones puras).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from sqa_kb.domain.entities import (
    DocumentationSession,
    IngestionItem,
    Project,
    ProjectMember,
    User,
)
from sqa_kb.domain.errors import ForbiddenError, NotFoundError, ValidationError
from sqa_kb.domain.value_objects import (
    DocumentationSessionStatus,
    DocumentationStep,
    IngestionStatus,
    ProjectMemberRole,
    RoleId,
)
from sqa_kb.services.documentation_session_service import (
    DocumentationSessionService,
    _render_glossary,
    _render_sources,
    _render_stakeholders,
    _render_taxonomy,
)
from tests.test_project_service import FakeProjectRepo, _now, _user


# ===========================================================================
# Fakes
# ===========================================================================


class FakeDocSessionRepo:
    def __init__(self) -> None:
        self.sessions: dict[str, DocumentationSession] = {}

    async def create(self, s: DocumentationSession) -> DocumentationSession:
        self.sessions[s.id] = s
        return s

    async def get(self, sid: str) -> DocumentationSession | None:
        return self.sessions.get(sid)

    async def list_for_project(self, pid: str) -> Sequence[DocumentationSession]:
        return [s for s in self.sessions.values() if s.project_id == pid]

    async def update(self, s: DocumentationSession) -> DocumentationSession:
        self.sessions[s.id] = s
        return s


class FakeIngestionService:
    """Imita la API pública de `IngestionService.upload`."""

    def __init__(self) -> None:
        self.uploaded: list[dict] = []  # type: ignore[type-arg]
        self._counter = 0

    async def upload(
        self,
        *,
        filename: str,
        data: bytes,
        uploaded_by_oid: str,
        project_id: str,
        source_origin: str = "",
    ) -> IngestionItem:
        self._counter += 1
        item_id = f"ing-fake-{self._counter:04d}"
        self.uploaded.append(
            {
                "filename": filename,
                "data": data,
                "project_id": project_id,
                "source_origin": source_origin,
            }
        )
        return IngestionItem(
            id=item_id,
            project_id=project_id,
            filename=filename,
            size_bytes=len(data),
            status=IngestionStatus.PENDIENTE_METADATA,
            uploaded_by_oid=uploaded_by_oid,
            uploaded_at=_now(),
            blob_path=f"{item_id}/{filename}",
        )


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def gk_lead() -> User:
    return _user("oid-gk", role=RoleId.GKLEAD)


@pytest.fixture
def alice() -> User:
    return _user("oid-alice", role=RoleId.COLABORADOR)


@pytest.fixture
def bob() -> User:
    return _user("oid-bob", role=RoleId.COLABORADOR)


@pytest.fixture
def project_id() -> str:
    return "proj-acme"


@pytest.fixture
def repos(project_id, alice):
    project_repo = FakeProjectRepo()
    project_repo.projects[project_id] = Project(
        id=project_id,
        slug="acme",
        name="ACME",
        owner_oid=alice.oid,
        created_at=_now(),
    )
    project_repo.members[(project_id, alice.oid)] = ProjectMember(
        project_id=project_id,
        user_oid=alice.oid,
        role=ProjectMemberRole.PROJECT_OWNER,
        added_at=_now(),
    )
    return project_repo, FakeDocSessionRepo(), FakeIngestionService()


@pytest.fixture
def service(repos):
    project_repo, doc_repo, ingestion = repos
    return DocumentationSessionService(doc_repo, project_repo, ingestion)


def _full_step_payloads() -> dict[DocumentationStep, dict]:
    """Payloads válidos para los 5 steps (utilidad de tests)."""
    return {
        DocumentationStep.CONTEXT: {
            "industry": "Banca",
            "regulation": "BCRA Comm A 7724",
            "initial_glossary": ["KYC", "AML"],
        },
        DocumentationStep.TAXONOMY: {
            "category_extensions": ["REG"],
            "doc_type_extensions": [],
            "notes": "Solo categoría regulatoria por ahora.",
        },
        DocumentationStep.SOURCES: {
            "sources": ["SharePoint/ACME/QA", "https://confluence.acme.com"],
            "access_notes": "Acceso vía VPN corporativa",
        },
        DocumentationStep.GLOSSARY: {
            "terms": [
                {"term": "KYC", "definition": "Know Your Customer", "synonyms": "conoce-tu-cliente"},
                {"term": "AML", "definition": "Anti-Money Laundering", "synonyms": ""},
            ]
        },
        DocumentationStep.STAKEHOLDERS: {
            "stakeholders": [
                {"name": "Mariana", "role": "CISO", "area": "Seguridad", "approves": "POL"},
            ]
        },
    }


# ===========================================================================
# Lifecycle
# ===========================================================================


@pytest.mark.asyncio
async def test_start_creates_in_progress_session(service, alice, project_id) -> None:
    s = await service.start(alice, project_id)
    assert s.status == DocumentationSessionStatus.IN_PROGRESS
    assert s.current_step == DocumentationStep.CONTEXT
    assert s.step_data == {}
    assert s.owner_oid == alice.oid


@pytest.mark.asyncio
async def test_start_forbidden_for_non_member(service, bob, project_id) -> None:
    with pytest.raises(ForbiddenError):
        await service.start(bob, project_id)


@pytest.mark.asyncio
async def test_start_allowed_for_gk_lead_without_membership(
    service, gk_lead, project_id
) -> None:
    s = await service.start(gk_lead, project_id)
    assert s.status == DocumentationSessionStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_submit_step_advances_to_next(service, alice, project_id) -> None:
    s = await service.start(alice, project_id)
    payloads = _full_step_payloads()
    updated = await service.submit_step(
        alice, s.id, DocumentationStep.CONTEXT, payloads[DocumentationStep.CONTEXT]
    )
    assert updated.current_step == DocumentationStep.TAXONOMY
    assert "context" in updated.step_data


@pytest.mark.asyncio
async def test_submit_wrong_step_rejected(service, alice, project_id) -> None:
    """Step esperado != step enviado → ValidationError."""
    s = await service.start(alice, project_id)
    with pytest.raises(ValidationError, match="Se esperaba"):
        await service.submit_step(
            alice, s.id, DocumentationStep.TAXONOMY, {"category_extensions": []}
        )


@pytest.mark.asyncio
async def test_submit_invalid_payload_rejected(service, alice, project_id) -> None:
    """Payload sin campos obligatorios → ValidationError."""
    s = await service.start(alice, project_id)
    with pytest.raises(ValidationError, match="Payload inválido"):
        await service.submit_step(
            alice, s.id, DocumentationStep.CONTEXT, {"industry": ""}  # min_length=1
        )


@pytest.mark.asyncio
async def test_submit_last_step_keeps_current(service, alice, project_id) -> None:
    """Al enviar el último step, current queda en stakeholders (no avanza)."""
    s = await service.start(alice, project_id)
    payloads = _full_step_payloads()
    for step in [
        DocumentationStep.CONTEXT,
        DocumentationStep.TAXONOMY,
        DocumentationStep.SOURCES,
        DocumentationStep.GLOSSARY,
    ]:
        s = await service.submit_step(alice, s.id, step, payloads[step])
    s = await service.submit_step(
        alice, s.id, DocumentationStep.STAKEHOLDERS, payloads[DocumentationStep.STAKEHOLDERS]
    )
    assert s.current_step == DocumentationStep.STAKEHOLDERS
    assert len(s.step_data) == 5


@pytest.mark.asyncio
async def test_finalize_generates_5_documents_and_marks_finalized(
    service, alice, project_id, repos
) -> None:
    _, _, ingestion = repos
    s = await service.start(alice, project_id)
    for step, payload in _full_step_payloads().items():
        s = await service.submit_step(alice, s.id, step, payload)

    finalized = await service.finalize(alice, s.id)

    assert finalized.status == DocumentationSessionStatus.FINALIZED
    assert finalized.finalized_at is not None
    assert len(finalized.generated_document_ids) == 5
    assert len(ingestion.uploaded) == 5
    # Cada upload va al proyecto correcto + tiene source_origin con el
    # session id (trazabilidad).
    for up in ingestion.uploaded:
        assert up["project_id"] == project_id
        assert f"documentation-session:{s.id}" == up["source_origin"]
    # Los archivos son `.md` con frontmatter YAML.
    for up in ingestion.uploaded:
        assert up["filename"].endswith(".md")
        assert up["data"].startswith(b"---\nsession_id:")


@pytest.mark.asyncio
async def test_finalize_with_missing_steps_rejected(
    service, alice, project_id
) -> None:
    s = await service.start(alice, project_id)
    payloads = _full_step_payloads()
    s = await service.submit_step(
        alice, s.id, DocumentationStep.CONTEXT, payloads[DocumentationStep.CONTEXT]
    )
    with pytest.raises(ValidationError, match="Faltan steps"):
        await service.finalize(alice, s.id)


@pytest.mark.asyncio
async def test_abandon_marks_session_abandoned(service, alice, project_id) -> None:
    s = await service.start(alice, project_id)
    ab = await service.abandon(alice, s.id)
    assert ab.status == DocumentationSessionStatus.ABANDONED


@pytest.mark.asyncio
async def test_cannot_resubmit_after_finalize(service, alice, project_id) -> None:
    s = await service.start(alice, project_id)
    for step, payload in _full_step_payloads().items():
        s = await service.submit_step(alice, s.id, step, payload)
    await service.finalize(alice, s.id)

    with pytest.raises(ValidationError, match="no está en progreso"):
        await service.submit_step(
            alice,
            s.id,
            DocumentationStep.STAKEHOLDERS,
            _full_step_payloads()[DocumentationStep.STAKEHOLDERS],
        )


@pytest.mark.asyncio
async def test_get_session_not_found(service, alice) -> None:
    with pytest.raises(NotFoundError):
        await service.get(alice, "no-existe")


@pytest.mark.asyncio
async def test_list_for_project_returns_only_project_sessions(
    service, alice, project_id
) -> None:
    await service.start(alice, project_id)
    await service.start(alice, project_id)
    items = await service.list_for_project(alice, project_id)
    assert len(items) == 2


# ===========================================================================
# Renderers (puros)
# ===========================================================================


def test_render_taxonomy_with_extensions() -> None:
    out = _render_taxonomy(
        {"category_extensions": ["REG"], "doc_type_extensions": ["MAN"]}
    )
    joined = "\n".join(out)
    assert "REG" in joined
    assert "MAN" in joined


def test_render_taxonomy_empty_falls_back_to_message() -> None:
    out = _render_taxonomy({})
    assert "Sin extensiones" in out[0]


def test_render_sources_handles_empty() -> None:
    out = _render_sources({})
    assert "sin fuentes" in out[0].lower()


def test_render_glossary_handles_terms_list() -> None:
    out = _render_glossary({"terms": [{"term": "API", "definition": "..."}]})
    assert "API" in out[0]


def test_render_stakeholders_builds_markdown_table() -> None:
    out = _render_stakeholders(
        {"stakeholders": [{"name": "A", "role": "B", "area": "C", "approves": "POL"}]}
    )
    text = out[0]
    assert "|" in text  # tabla
    assert "Stakeholders" in text
