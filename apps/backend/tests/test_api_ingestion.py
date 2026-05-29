"""Tests del router /ingestion (Fase 4.5).

Usan TestClient + dependency_overrides para inyectar un IngestionService
fake + CurrentUser. Sin DB ni Blob real. Verifican el wiring HTTP:
status codes, serialización camelCase, ruteo, validación de body.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from sqa_kb.api.dependencies import (
    get_current_user,
    get_ingestion_service,
    get_project_service,
)
from sqa_kb.domain.entities import IngestionItem, Project, User
from sqa_kb.domain.value_objects import (
    IngestionStatus,
    RoleId,
)
from sqa_kb.main import create_app

_PROJECT_ID = "00000000-0000-0000-0000-000000000001"


def _item(item_id: str = "ing-abc123", status=IngestionStatus.PENDIENTE_METADATA) -> IngestionItem:  # type: ignore[no-untyped-def]
    return IngestionItem(
        id=item_id,
        project_id=_PROJECT_ID,
        filename="memoria.docx",
        size_bytes=1024,
        status=status,
        uploaded_by_oid="stub-capturador-00000000",
        uploaded_at=datetime(2026, 5, 26, tzinfo=UTC),
        blob_path=f"{item_id}/memoria.docx",
    )


@dataclass
class _FakeProjectService:
    """Acepta cualquier project_id (los tests de IDOR viven en test_api_projects)."""

    async def get(self, caller: User, project_id: str) -> Project:  # noqa: ARG002
        return Project(
            id=project_id,
            slug="proj-test",
            name="Proyecto de test",
            owner_oid=caller.oid,
            created_at=datetime.now(UTC),
        )


@dataclass
class _FakeService:
    """Imita la API pública del IngestionService."""

    last_upload: dict | None = None  # type: ignore[type-arg]
    last_classify_id: str = ""
    last_approve: dict | None = None  # type: ignore[type-arg]
    last_reject: dict | None = None  # type: ignore[type-arg]
    list_filter: object = None
    items_to_return: list[IngestionItem] = field(default_factory=list)

    async def upload(
        self,
        *,
        filename: str,
        data: bytes,
        uploaded_by_oid: str,
        project_id: str,
        source_origin: str = "",
    ) -> IngestionItem:
        self.last_upload = {
            "filename": filename,
            "size": len(data),
            "oid": uploaded_by_oid,
            "project_id": project_id,
            "source": source_origin,
        }
        return _item()

    async def classify(self, item_id: str) -> IngestionItem:
        self.last_classify_id = item_id
        return _item(item_id, status=IngestionStatus.EN_REVISION)

    async def approve(  # type: ignore[no-untyped-def]
        self, item_id: str, *, traceability, approver_oid: str, approver_name: str
    ) -> IngestionItem:
        self.last_approve = {
            "item_id": item_id,
            "category": str(traceability.category),
            "type": str(traceability.document_type),
            "approver_oid": approver_oid,
            "approver_name": approver_name,
        }
        return _item(item_id, status=IngestionStatus.INDEXADO)

    async def reject(self, item_id: str, *, reason: str) -> IngestionItem:
        self.last_reject = {"item_id": item_id, "reason": reason}
        return _item(item_id, status=IngestionStatus.RECHAZADO)

    async def list_items(  # type: ignore[no-untyped-def] # noqa: ARG002
        self, *, statuses=None, limit: int = 50, offset: int = 0
    ) -> Sequence[IngestionItem]:
        self.list_filter = list(statuses) if statuses else None
        return self.items_to_return


def _user() -> User:
    """Fase 9.1: usamos gklead para que `is_admin = True` y los endpoints
    de ingesta admitan al test (gating actual). En 9.3 esto se reemplaza
    por verificación de membership."""
    now = datetime.now(UTC)
    return User(
        oid="stub-gklead-00000000",
        email="t@sqasa.co",
        name="Tester",
        role_id=RoleId.GKLEAD,
        carpetas_owned=[],
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def client_and_service() -> Iterator[tuple[TestClient, _FakeService]]:
    app = create_app()
    svc = _FakeService()
    app.dependency_overrides[get_ingestion_service] = lambda: svc
    app.dependency_overrides[get_project_service] = lambda: _FakeProjectService()
    app.dependency_overrides[get_current_user] = lambda: _user()
    with TestClient(app) as client:
        yield client, svc
    app.dependency_overrides.clear()


# ===========================================================================
# POST /ingestion (upload)
# ===========================================================================


def test_upload_returns_201_and_item(client_and_service) -> None:  # type: ignore[no-untyped-def]
    client, svc = client_and_service
    resp = client.post(
        f"/ingestion?projectId={_PROJECT_ID}",
        files={"file": ("memoria.docx", b"contenido binario", "application/octet-stream")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == "ing-abc123"
    assert body["status"] == "pendiente-metadata"
    # camelCase en el wire.
    assert "uploadedAt" in body
    assert "blobPath" in body
    # El servicio recibió el archivo.
    assert svc.last_upload is not None
    assert svc.last_upload["filename"] == "memoria.docx"
    assert svc.last_upload["oid"] == "stub-gklead-00000000"


def test_upload_passes_source_origin_query(client_and_service) -> None:  # type: ignore[no-untyped-def]
    client, svc = client_and_service
    resp = client.post(
        f"/ingestion?projectId={_PROJECT_ID}&sourceOrigin=https://sp/x",
        files={"file": ("a.docx", b"x", "application/octet-stream")},
    )
    assert resp.status_code == 201
    assert svc.last_upload["source"] == "https://sp/x"
    assert svc.last_upload["project_id"] == _PROJECT_ID


# ===========================================================================
# POST /ingestion/{id}/classify
# ===========================================================================


def test_classify_returns_item_en_revision(client_and_service) -> None:  # type: ignore[no-untyped-def]
    client, svc = client_and_service
    resp = client.post("/ingestion/ing-xyz/classify")
    assert resp.status_code == 200
    assert resp.json()["status"] == "en-revision"
    assert svc.last_classify_id == "ing-xyz"


# ===========================================================================
# POST /ingestion/{id}/approve
# ===========================================================================


def test_approve_with_traceability(client_and_service) -> None:  # type: ignore[no-untyped-def]
    client, svc = client_and_service
    resp = client.post(
        "/ingestion/ing-xyz/approve",
        json={
            "approvedBy": "Camila Pereyra",
            "approvalDate": "2026-05-20",
            "sourceOrigin": "https://sp/doc",
            "version": "2.1",
            "category": "TEC",
            "documentType": "MTEC",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "indexado"
    assert svc.last_approve["category"] == "TEC"
    assert svc.last_approve["type"] == "MTEC"
    assert svc.last_approve["approver_name"] == "Tester"


def test_approve_missing_required_field_returns_422(client_and_service) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_and_service
    resp = client.post(
        "/ingestion/ing-xyz/approve",
        json={"approvalDate": "2026-05-20", "category": "TEC", "documentType": "MTEC"},
    )
    assert resp.status_code == 422  # falta approvedBy


def test_approve_invalid_category_returns_422(client_and_service) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_and_service
    resp = client.post(
        "/ingestion/ing-xyz/approve",
        json={
            "approvedBy": "X",
            "approvalDate": "2026-05-20",
            "category": "NOEXISTE",
            "documentType": "MTEC",
        },
    )
    assert resp.status_code == 422


# ===========================================================================
# GET /ingestion
# ===========================================================================


def test_list_returns_items(client_and_service) -> None:  # type: ignore[no-untyped-def]
    client, svc = client_and_service
    svc.items_to_return = [_item("ing-1"), _item("ing-2")]
    resp = client.get("/ingestion")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_filters_by_status_query(client_and_service) -> None:  # type: ignore[no-untyped-def]
    client, svc = client_and_service
    svc.items_to_return = [_item("ing-1", status=IngestionStatus.EN_REVISION)]
    resp = client.get("/ingestion?status=en-revision")
    assert resp.status_code == 200
    assert svc.list_filter == [IngestionStatus.EN_REVISION]


def test_list_multiple_status_filters(client_and_service) -> None:  # type: ignore[no-untyped-def]
    client, svc = client_and_service
    resp = client.get("/ingestion?status=en-revision&status=indexado")
    assert resp.status_code == 200
    assert set(svc.list_filter) == {
        IngestionStatus.EN_REVISION,
        IngestionStatus.INDEXADO,
    }


def test_list_invalid_status_returns_422(client_and_service) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_and_service
    resp = client.get("/ingestion?status=noexiste")
    assert resp.status_code == 422


def test_list_limit_out_of_range_returns_422(client_and_service) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_and_service
    resp = client.get("/ingestion?limit=500")
    assert resp.status_code == 422


# ===========================================================================
# POST /ingestion/{id}/reject
# ===========================================================================


def test_reject_with_reason(client_and_service) -> None:  # type: ignore[no-untyped-def]
    client, svc = client_and_service
    resp = client.post(
        "/ingestion/ing-xyz/reject", json={"reason": "No cumple el estándar"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rechazado"
    assert svc.last_reject["item_id"] == "ing-xyz"
    assert svc.last_reject["reason"] == "No cumple el estándar"


def test_reject_missing_reason_returns_422(client_and_service) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_and_service
    resp = client.post("/ingestion/ing-xyz/reject", json={})
    assert resp.status_code == 422
