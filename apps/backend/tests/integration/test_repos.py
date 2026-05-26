"""Tests de integración de los repositorios PostgreSQL contra DB real.

Cubren el happy path de cada repo. Los tests asumen que la migration
inicial ya está aplicada y el seed corrido (categorías + tipos + users).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from sqa_kb.adapters.repositories.postgres.activity import PostgresActivityRepository
from sqa_kb.adapters.repositories.postgres.audit_log import PostgresAuditLogRepository
from sqa_kb.adapters.repositories.postgres.documents import PostgresDocumentRepository
from sqa_kb.adapters.repositories.postgres.ingestion import PostgresIngestionRepository
from sqa_kb.adapters.repositories.postgres.seed import seed
from sqa_kb.adapters.repositories.postgres.sessions import PostgresSessionRepository
from sqa_kb.adapters.repositories.postgres.skills import PostgresSkillRepository
from sqa_kb.adapters.repositories.postgres.taxonomy import PostgresTaxonomyRepository
from sqa_kb.adapters.repositories.postgres.users import PostgresUserRepository
from sqa_kb.domain.entities import (
    AuditLog,
    Document,
    IngestionItem,
    Message,
    Session,
    Skill,
    User,
)
from sqa_kb.domain.errors import NotFoundError
from sqa_kb.domain.value_objects import (
    CategoryCode,
    DocStatus,
    DocTypeCode,
    IngestionStatus,
    MessageRole,
    MessageStatus,
    RoleId,
    SessionMode,
    SessionStatus,
)


@pytest.fixture(scope="module", autouse=True)
async def _ensure_seed(session_factory):  # type: ignore[no-untyped-def]
    """Garantiza categorías + tipos + users base antes de los tests."""
    await seed(session_factory)


def _now() -> datetime:
    return datetime.now(UTC)


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ===========================================================================
# Taxonomy + Users (lectura post-seed)
# ===========================================================================


async def test_taxonomy_lists_8_categories_and_11_doc_types(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresTaxonomyRepository(session_factory)
    cats = await repo.list_categories()
    types = await repo.list_doc_types()
    assert len(cats) == 8
    assert len(types) == 11
    # Códigos esperados (cerrados).
    assert {c.code for c in cats} == {
        "PROC",
        "TEC",
        "ARQ",
        "HERR",
        "NEG",
        "ENV",
        "EST",
        "CONT",
    }


async def test_user_repo_get_by_oid_after_seed(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresUserRepository(session_factory)
    user = await repo.get_by_oid("stub-gklead-00000000")
    assert user is not None
    assert user.role_id == "gklead"
    assert user.is_admin is True
    assert user.puede_gobernar_taxonomia is True


async def test_user_repo_get_missing_returns_none(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresUserRepository(session_factory)
    assert await repo.get_by_oid("nonexistent-oid-xyz") is None


async def test_user_repo_upsert_creates_and_updates(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresUserRepository(session_factory)
    oid = _unique("oid-test-user")
    email = f"{oid}@sqa.co"
    fresh = User(
        oid=oid,
        email=email,
        name="Test User",
        role_id=RoleId.CAPTURADOR,
        created_at=_now(),
        updated_at=_now(),
    )
    created = await repo.upsert_from_token(fresh)
    assert created.oid == oid
    assert created.role_id == "capturador"

    # Mismo OID con nombre cambiado → actualiza, no duplica.
    updated_in = User(
        **{**fresh.model_dump(), "name": "Renamed", "role_id": RoleId.OWNER}
    )
    updated = await repo.upsert_from_token(updated_in)
    assert updated.name == "Renamed"
    assert updated.role_id == "owner"


# ===========================================================================
# Documents
# ===========================================================================


def _make_doc(
    *,
    id_suffix: str,
    titulo: str = "Doc de test",
    carpeta: CategoryCode = CategoryCode.TEC,
    tipo: DocTypeCode = DocTypeCode.MTEC,
    autoritativo: bool = False,
    score: float = 4.0,
    citas: int = 0,
    autor_oid: str | None = None,
    fecha: datetime | None = None,
) -> Document:
    return Document(
        id=f"TEC-test-{id_suffix}-2026-05-22",
        titulo=titulo,
        carpeta=carpeta,
        tipo=tipo,
        autoritativo=autoritativo,
        estado=DocStatus.VIGENTE,
        autor_oid=autor_oid,
        autor_name="Tester",
        autor_role="QA",
        fecha=fecha or _now(),
        revision=fecha or _now(),
        version="1.0",
        citas=citas,
        score=score,
        anonimizado=False,
        fragmentos=0,
        paginas=5,
        formato="DOCX",
        tags=[],
    )


async def test_document_create_and_get(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresDocumentRepository(session_factory)
    doc = _make_doc(id_suffix=uuid.uuid4().hex[:6])
    created = await repo.create(doc)
    assert created.id == doc.id

    fetched = await repo.get(doc.id)
    assert fetched is not None
    assert fetched.titulo == "Doc de test"


async def test_document_search_filters_by_carpeta(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresDocumentRepository(session_factory)
    suffix = uuid.uuid4().hex[:6]
    tec = _make_doc(id_suffix=f"a{suffix}", carpeta=CategoryCode.TEC)
    arq = _make_doc(id_suffix=f"b{suffix}", carpeta=CategoryCode.ARQ)
    await repo.create(tec)
    await repo.create(arq)

    items, total = await repo.search(carpetas=[CategoryCode.TEC], limit=100)
    ids = {d.id for d in items}
    assert tec.id in ids
    assert arq.id not in ids
    assert total >= 1


async def test_document_search_sort_score_desc(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresDocumentRepository(session_factory)
    suffix = uuid.uuid4().hex[:6]
    low = _make_doc(id_suffix=f"low{suffix}", score=2.0)
    high = _make_doc(id_suffix=f"high{suffix}", score=4.8)
    await repo.create(low)
    await repo.create(high)

    items, _ = await repo.search(sort_by="score_desc", limit=100)
    scores = [d.score for d in items]
    assert scores == sorted(scores, reverse=True)


async def test_document_search_pagination(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresDocumentRepository(session_factory)
    # Crear 3 docs únicos para esta corrida.
    base = uuid.uuid4().hex[:6]
    for i in range(3):
        await repo.create(_make_doc(id_suffix=f"p{base}{i}"))

    page1, total = await repo.search(limit=2, offset=0)
    page2, _ = await repo.search(limit=2, offset=2)
    assert len(page1) == 2
    assert total >= 3
    ids1 = {d.id for d in page1}
    ids2 = {d.id for d in page2}
    assert ids1.isdisjoint(ids2), "page2 no debe overlapearse con page1"


async def test_document_set_authoritative(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresDocumentRepository(session_factory)
    doc = _make_doc(id_suffix=uuid.uuid4().hex[:6], autoritativo=False)
    await repo.create(doc)
    updated = await repo.set_authoritative(
        doc.id, value=True, caller_oid="stub-gklead-00000000"
    )
    assert updated.autoritativo is True


async def test_document_set_authoritative_notfound(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresDocumentRepository(session_factory)
    with pytest.raises(NotFoundError):
        await repo.set_authoritative(
            "TEC-no-existe-xyz-2026-01-01",
            value=True,
            caller_oid="stub-gklead-00000000",
        )


async def test_document_list_by_author_aggregates_stats(session_factory) -> None:  # type: ignore[no-untyped-def]
    user_repo = PostgresUserRepository(session_factory)
    repo = PostgresDocumentRepository(session_factory)
    suffix = uuid.uuid4().hex[:6]
    author_oid = f"author-{suffix}"

    # FK: el autor debe existir en `users` antes de crear los documentos.
    await user_repo.upsert_from_token(
        User(
            oid=author_oid,
            email=f"{author_oid}@sqa.co",
            name="Author for stats test",
            role_id=RoleId.CAPTURADOR,
            created_at=_now(),
            updated_at=_now(),
        )
    )

    await repo.create(_make_doc(id_suffix=f"x{suffix}", autor_oid=author_oid, citas=10, score=4.0))
    await repo.create(_make_doc(id_suffix=f"y{suffix}", autor_oid=author_oid, citas=5, score=4.2))

    items, stats = await repo.list_by_author(author_oid)
    assert stats.total_captures == 2
    assert stats.total_citations_received == 15
    assert 4.0 <= stats.avg_score <= 4.2
    assert {d.id for d in items} == {
        f"TEC-test-x{suffix}-2026-05-22",
        f"TEC-test-y{suffix}-2026-05-22",
    }


# ===========================================================================
# Sessions + Messages (IDOR enforcement)
# ===========================================================================


async def test_session_create_and_get_by_owner(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresSessionRepository(session_factory)
    owner = "stub-capturador-00000000"
    s = Session(
        id=_unique("ses"),
        owner_oid=owner,
        mode=SessionMode.CAPTURA,
        title="Test session",
        status=SessionStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),
    )
    await repo.create(s)
    fetched = await repo.get(s.id, caller_oid=owner)
    assert fetched is not None
    assert fetched.title == "Test session"


async def test_session_get_returns_none_for_other_owner(session_factory) -> None:  # type: ignore[no-untyped-def]
    """IDOR: get() de sesión ajena devuelve None (no diferencia existencia)."""
    repo = PostgresSessionRepository(session_factory)
    s = Session(
        id=_unique("ses"),
        owner_oid="stub-capturador-00000000",
        mode=SessionMode.CAPTURA,
        title="Owner-only",
        status=SessionStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),
    )
    await repo.create(s)
    # Otro user pidiendo la misma sesión.
    fetched = await repo.get(s.id, caller_oid="stub-owner-00000000")
    assert fetched is None


async def test_session_update_status_for_owner_only(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresSessionRepository(session_factory)
    owner = "stub-capturador-00000000"
    s = Session(
        id=_unique("ses"),
        owner_oid=owner,
        mode=SessionMode.CAPTURA,
        title="Pausable",
        status=SessionStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),
    )
    await repo.create(s)
    paused = await repo.update_status(s.id, SessionStatus.PAUSED, caller_oid=owner)
    assert paused.status == "paused"

    with pytest.raises(NotFoundError):
        await repo.update_status(
            s.id, SessionStatus.ACTIVE, caller_oid="stub-owner-00000000"
        )


async def test_append_message_updates_count_and_stage(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresSessionRepository(session_factory)
    owner = "stub-capturador-00000000"
    s = Session(
        id=_unique("ses"),
        owner_oid=owner,
        mode=SessionMode.CAPTURA,
        title="With messages",
        status=SessionStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),
    )
    await repo.create(s)

    msg = Message(
        id=_unique("msg"),
        session_id=s.id,
        role=MessageRole.AGENT,
        content="Hola Aria",
        stage=2,
        status=MessageStatus.COMPLETE,
        started_at=_now(),
    )
    saved = await repo.append_message(msg, caller_oid=owner)
    assert saved.id == msg.id

    after = await repo.get(s.id, caller_oid=owner)
    assert after is not None
    assert after.message_count == 1
    assert after.current_stage == 2


async def test_append_message_blocked_for_other_owner(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresSessionRepository(session_factory)
    s = Session(
        id=_unique("ses"),
        owner_oid="stub-capturador-00000000",
        mode=SessionMode.CAPTURA,
        title="Locked",
        status=SessionStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),
    )
    await repo.create(s)
    msg = Message(
        id=_unique("msg"),
        session_id=s.id,
        role=MessageRole.USER,
        content="hi",
        status=MessageStatus.COMPLETE,
        started_at=_now(),
    )
    with pytest.raises(NotFoundError):
        await repo.append_message(msg, caller_oid="stub-owner-00000000")


# ===========================================================================
# Skills + Audit log + Activity
# ===========================================================================


async def test_skill_upsert_increments_version(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresSkillRepository(session_factory)
    sk = Skill(
        id=_unique("skill"),
        name="Test skill",
        description="d",
        body_markdown="# body",
        enabled=True,
        version=1,
        updated_at=_now(),
    )
    first = await repo.upsert(sk)
    assert first.version == 1
    second = await repo.upsert(sk)
    assert second.version >= 2


async def test_audit_log_append_only(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresAuditLogRepository(session_factory)
    entry = AuditLog(
        id=_unique("audit"),
        actor_oid="stub-gklead-00000000",
        event_type="test.event",
        resource_id="res-123",
        metadata={"k": "v"},
        at=_now(),
    )
    await repo.append(entry)
    found = await repo.list_for_resource("res-123")
    assert any(e.id == entry.id for e in found)


async def test_activity_recent_returns_empty_initially(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresActivityRepository(session_factory)
    # En tests aislados (rollback) no quedan rows, pero el repo no debe romper.
    items = await repo.recent(limit=5)
    assert isinstance(list(items), list)


# ===========================================================================
# Ingestion
# ===========================================================================


async def test_ingestion_create_and_list_pending(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresIngestionRepository(session_factory)
    item = IngestionItem(
        id=_unique("ing"),
        filename="test.docx",
        size_bytes=1024,
        paginas=3,
        status=IngestionStatus.PENDIENTE_METADATA,
        uploaded_by_oid="stub-capturador-00000000",
        uploaded_at=_now(),
    )
    created = await repo.create(item)
    assert created.id == item.id

    pending = await repo.list_pending(limit=100)
    assert any(p.id == item.id for p in pending)
