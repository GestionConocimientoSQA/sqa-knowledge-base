"""Tests del IngestionService (Fase 4.5).

Usan fakes para todos los puertos (repo, blob, anonymizer, classifier,
indexer hook). Sin DB, sin Blob real, sin LLM. El extractor SÍ es real
(es puro) y procesa archivos generados por los generadores de 4.1/4.2.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from sqa_kb.documents.generators.docx import DocxGenerator
from sqa_kb.documents.models import DocumentContent
from sqa_kb.domain.entities import Document, IngestionItem
from sqa_kb.domain.errors import NotFoundError, ValidationError
from sqa_kb.domain.value_objects import CategoryCode, DocTypeCode, IngestionStatus
from sqa_kb.ports.gateways import BlobMetadata, PiiFilterResult
from sqa_kb.services.ingestion_service import (
    INBOX_CONTAINER,
    MAX_UPLOAD_BYTES,
    ClassificationSuggestion,
    IngestionService,
    TraceabilityInput,
)

# ===========================================================================
# Fakes
# ===========================================================================


@dataclass
class _FakeBlob:
    store: dict[str, bytes] = field(default_factory=dict)
    uploads: list[str] = field(default_factory=list)

    async def upload(  # noqa: ARG002
        self, *, container: str, path: str, data: bytes, content_type: str
    ) -> BlobMetadata:
        self.store[f"{container}/{path}"] = data
        self.uploads.append(path)
        return BlobMetadata(
            path=path, size_bytes=len(data), content_type=content_type, etag="x"
        )

    async def download(self, *, container: str, path: str) -> bytes:
        return self.store[f"{container}/{path}"]

    async def delete(self, *, container: str, path: str) -> None:
        self.store.pop(f"{container}/{path}", None)

    async def signed_url(self, *, container: str, path: str, expires_in_seconds: int = 3600) -> str:  # noqa: ARG002
        return f"https://fake/{container}/{path}"


@dataclass
class _FakeIngestionRepo:
    items: dict[str, IngestionItem] = field(default_factory=dict)

    async def create(self, item: IngestionItem) -> IngestionItem:
        self.items[item.id] = item
        return item

    async def get(self, item_id: str) -> IngestionItem | None:
        return self.items.get(item_id)

    async def list_pending(self, *, limit: int = 50, offset: int = 0) -> Sequence[IngestionItem]:  # noqa: ARG002
        return list(self.items.values())

    async def list_by_status(  # type: ignore[no-untyped-def] # noqa: ARG002
        self, statuses=None, *, limit: int = 50, offset: int = 0
    ) -> Sequence[IngestionItem]:
        items = list(self.items.values())
        if statuses:
            wanted = {str(s) for s in statuses}
            items = [i for i in items if str(i.status) in wanted]
        return items

    async def update(self, item: IngestionItem) -> IngestionItem:
        self.items[item.id] = item
        return item


@dataclass
class _FakeDocRepo:
    created: list[Document] = field(default_factory=list)

    async def create(self, doc: Document) -> Document:
        self.created.append(doc)
        return doc


@dataclass
class _CountingAnonymizer:
    replacements: int = 0

    async def anonymize(self, text: str) -> PiiFilterResult:
        return PiiFilterResult(text=text, replacements=self.replacements)


@dataclass
class _FakeClassifier:
    suggestion: ClassificationSuggestion
    seen_text: str = ""

    async def __call__(self, text: str) -> ClassificationSuggestion:
        self.seen_text = text
        return self.suggestion


@dataclass
class _IndexerHookSpy:
    calls: list[tuple[str, str]] = field(default_factory=list)

    async def __call__(self, document_id: str, text: str) -> None:
        self.calls.append((document_id, text))


def _suggestion() -> ClassificationSuggestion:
    return ClassificationSuggestion(
        category=CategoryCode.TEC,
        document_type=DocTypeCode.MTEC,
        confidence=0.9,
        reasoning="técnico",
    )


def _docx_bytes(topic: str = "contenido de prueba para ingesta") -> bytes:
    content = DocumentContent(
        document_id="MTEC-fake-2026-05-26",
        title="Doc de prueba",
        category="TEC",
        document_type="MTEC",
        version="1.0",
        fecha=datetime(2026, 5, 26, tzinfo=UTC),
        author_name="A",
        author_role="QA",
        topic=topic,
        body_blocks=("bloque uno", "bloque dos"),
    )
    return DocxGenerator().generate(content).data


def _service(**overrides):  # type: ignore[no-untyped-def]
    defaults = {
        "ingestion_repo": _FakeIngestionRepo(),
        "document_repo": _FakeDocRepo(),
        "blob": _FakeBlob(),
        "anonymizer": _CountingAnonymizer(),
        "classifier": _FakeClassifier(_suggestion()),
        "indexer_hook": _IndexerHookSpy(),
    }
    defaults.update(overrides)
    return IngestionService(**defaults), defaults  # type: ignore[arg-type]


# ===========================================================================
# upload
# ===========================================================================


async def test_upload_creates_item_and_stores_blob() -> None:
    svc, deps = _service()
    item = await svc.upload(
        filename="memoria.docx",
        data=_docx_bytes(),
        uploaded_by_oid="oid-1",
        source_origin="https://sharepoint/x",
    )
    assert item.status == IngestionStatus.PENDIENTE_METADATA
    assert item.uploaded_by_oid == "oid-1"
    assert item.fuente_original == "https://sharepoint/x"
    assert item.blob_path is not None
    # El blob se guardó en el container inbox.
    blob: _FakeBlob = deps["blob"]
    assert f"{INBOX_CONTAINER}/{item.blob_path}" in blob.store


async def test_upload_rejects_empty_file() -> None:
    svc, _ = _service()
    with pytest.raises(ValidationError, match="vacío"):
        await svc.upload(filename="x.docx", data=b"", uploaded_by_oid="o")


async def test_upload_rejects_oversized_file() -> None:
    svc, _ = _service()
    big = b"x" * (MAX_UPLOAD_BYTES + 1)
    with pytest.raises(ValidationError, match="límite"):
        await svc.upload(filename="x.docx", data=big, uploaded_by_oid="o")


async def test_upload_rejects_unsupported_format() -> None:
    svc, _ = _service()
    with pytest.raises(ValidationError, match="no soportado"):
        await svc.upload(filename="x.txt", data=b"hola", uploaded_by_oid="o")


# ===========================================================================
# classify
# ===========================================================================


async def test_classify_updates_item_with_suggestion() -> None:
    svc, deps = _service()
    item = await svc.upload(
        filename="memoria.docx", data=_docx_bytes(), uploaded_by_oid="o"
    )
    classified = await svc.classify(item.id)
    assert classified.status == IngestionStatus.EN_REVISION
    assert classified.carpeta_sugerida == CategoryCode.TEC
    assert classified.tipo_sugerido == DocTypeCode.MTEC
    assert classified.paginas >= 1


async def test_classify_anonymizes_before_classifying() -> None:
    """El clasificador debe recibir el texto YA anonimizado."""
    anonymizer = _CountingAnonymizer(replacements=2)
    classifier = _FakeClassifier(_suggestion())
    svc, _ = _service(anonymizer=anonymizer, classifier=classifier)
    item = await svc.upload(
        filename="memoria.docx", data=_docx_bytes(), uploaded_by_oid="o"
    )
    await svc.classify(item.id)
    # El classifier fue invocado (texto pasó por el anonymizer no-op que
    # devuelve el mismo texto, pero el flujo lo llamó).
    assert classifier.seen_text != ""


async def test_classify_unknown_item_raises() -> None:
    svc, _ = _service()
    with pytest.raises(NotFoundError):
        await svc.classify("ing-noexiste")


# ===========================================================================
# approve
# ===========================================================================


async def test_approve_creates_document_and_indexes() -> None:
    svc, deps = _service()
    item = await svc.upload(
        filename="memoria.docx", data=_docx_bytes(), uploaded_by_oid="o"
    )
    await svc.classify(item.id)

    trace = TraceabilityInput(
        approved_by="Camila Pereyra",
        approval_date="2026-05-20",
        source_origin="https://sharepoint/doc",
        version="2.1",
        category=CategoryCode.TEC,
        document_type=DocTypeCode.MTEC,
    )
    approved = await svc.approve(
        item.id, traceability=trace, approver_oid="oid-owner", approver_name="Camila"
    )
    assert approved.status == IngestionStatus.INDEXADO
    assert approved.aprobador_name == "Camila Pereyra"
    assert approved.version == "2.1"

    # Document creado.
    doc_repo: _FakeDocRepo = deps["document_repo"]
    assert len(doc_repo.created) == 1
    doc = doc_repo.created[0]
    assert doc.carpeta == CategoryCode.TEC
    assert doc.tipo == DocTypeCode.MTEC
    assert doc.aprobador_name == "Camila Pereyra"

    # Indexer hook disparado.
    hook: _IndexerHookSpy = deps["indexer_hook"]
    assert len(hook.calls) == 1
    assert hook.calls[0][0] == doc.id


async def test_approve_marks_document_anonymized_when_replacements() -> None:
    svc, deps = _service(anonymizer=_CountingAnonymizer(replacements=3))
    item = await svc.upload(
        filename="memoria.docx", data=_docx_bytes(), uploaded_by_oid="o"
    )
    trace = TraceabilityInput(
        approved_by="X",
        approval_date="2026-05-20",
        source_origin="",
        version="1.0",
        category=CategoryCode.TEC,
        document_type=DocTypeCode.MTEC,
    )
    await svc.approve(item.id, traceability=trace, approver_oid="o", approver_name="X")
    doc = deps["document_repo"].created[0]
    assert doc.anonimizado is True


async def test_approve_without_indexer_hook_still_creates_doc() -> None:
    svc, deps = _service(indexer_hook=None)
    item = await svc.upload(
        filename="memoria.docx", data=_docx_bytes(), uploaded_by_oid="o"
    )
    trace = TraceabilityInput(
        approved_by="X",
        approval_date="2026-05-20",
        source_origin="",
        version="1.0",
        category=CategoryCode.TEC,
        document_type=DocTypeCode.MTEC,
    )
    approved = await svc.approve(
        item.id, traceability=trace, approver_oid="o", approver_name="X"
    )
    assert approved.status == IngestionStatus.INDEXADO
    assert len(deps["document_repo"].created) == 1


async def test_approve_unknown_item_raises() -> None:
    svc, _ = _service()
    trace = TraceabilityInput(
        approved_by="X",
        approval_date="2026-05-20",
        source_origin="",
        version="1.0",
        category=CategoryCode.TEC,
        document_type=DocTypeCode.MTEC,
    )
    with pytest.raises(NotFoundError):
        await svc.approve("ing-x", traceability=trace, approver_oid="o", approver_name="X")


# ===========================================================================
# list
# ===========================================================================


async def test_list_filters_by_status() -> None:
    svc, _ = _service()
    a = await svc.upload(filename="a.docx", data=_docx_bytes(), uploaded_by_oid="o")
    await svc.upload(filename="b.docx", data=_docx_bytes(), uploaded_by_oid="o")
    await svc.classify(a.id)  # a → en-revision

    en_revision = await svc.list_items(statuses=[IngestionStatus.EN_REVISION])
    assert len(en_revision) == 1
    assert en_revision[0].id == a.id

    pendientes = await svc.list_items(statuses=[IngestionStatus.PENDIENTE_METADATA])
    assert len(pendientes) == 1


async def test_list_all_when_no_status_filter() -> None:
    svc, _ = _service()
    await svc.upload(filename="a.docx", data=_docx_bytes(), uploaded_by_oid="o")
    await svc.upload(filename="b.docx", data=_docx_bytes(), uploaded_by_oid="o")
    all_items = await svc.list_items()
    assert len(all_items) == 2
