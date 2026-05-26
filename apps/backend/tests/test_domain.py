"""Tests del dominio — value objects, entities, errors."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sqa_kb.domain.entities import (
    CitationPayload,
    Document,
    Message,
    ScoringPayload,
    Session,
    User,
)
from sqa_kb.domain.errors import (
    ConflictError,
    DomainError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
    ValidationError,
)
from sqa_kb.domain.value_objects import (
    CategoryCode,
    DocStatus,
    DocTypeCode,
    MessageRole,
    MessageStatus,
    RoleId,
    SessionMode,
    SessionStatus,
    is_valid_stage,
)

# ---------- value_objects ----------


def test_is_valid_stage_accepts_0_to_5() -> None:
    for i in range(6):
        assert is_valid_stage(i), f"{i} debe ser válido"


def test_is_valid_stage_accepts_c_and_i() -> None:
    assert is_valid_stage("C")
    assert is_valid_stage("I")


@pytest.mark.parametrize("bad", [-1, 6, 100, "X", "", None, True, False, 3.5])
def test_is_valid_stage_rejects_invalid(bad: object) -> None:
    assert not is_valid_stage(bad)


def test_enums_exhaustivos() -> None:
    assert len(list(CategoryCode)) == 8
    assert len(list(DocTypeCode)) == 11
    assert len(list(RoleId)) == 3
    assert set(SessionMode) == {SessionMode.CAPTURA, SessionMode.CONSULTA, SessionMode.INGESTA}


# ---------- entities ----------


def _now() -> datetime:
    return datetime.now(UTC)


def test_user_is_admin_for_owner_and_gklead() -> None:
    base = {
        "email": "x@sqa.co",
        "name": "X",
        "created_at": _now(),
        "updated_at": _now(),
    }
    assert User(oid="o1", role_id=RoleId.OWNER, **base).is_admin
    assert User(oid="o2", role_id=RoleId.GKLEAD, **base).is_admin
    assert not User(oid="o3", role_id=RoleId.CAPTURADOR, **base).is_admin


def test_user_carpetas_owned_only_for_owner() -> None:
    # Semánticamente las carpetas_owned solo tienen sentido para Owner.
    # El modelo NO lo enforce hoy (es soft) — confiamos en services.
    u = User(
        oid="o1",
        email="x@sqa.co",
        name="X",
        role_id=RoleId.OWNER,
        carpetas_owned=[CategoryCode.TEC, CategoryCode.ARQ],
        created_at=_now(),
        updated_at=_now(),
    )
    assert CategoryCode.TEC in u.carpetas_owned


def test_session_minimal_valid() -> None:
    s = Session(
        id="ses-1",
        owner_oid="oid-1",
        mode=SessionMode.CAPTURA,
        title="Nueva captura",
        status=SessionStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),
    )
    assert s.message_count == 0
    assert s.current_stage is None


def test_session_title_empty_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017, BLE001 — pydantic.ValidationError
        Session(
            id="ses-1",
            owner_oid="oid-1",
            mode=SessionMode.CAPTURA,
            title="",
            status=SessionStatus.ACTIVE,
            created_at=_now(),
            updated_at=_now(),
        )


def test_message_invalid_stage_raises_domain_error() -> None:
    with pytest.raises(ValidationError, match="Stage inválido"):
        Message(
            id="m1",
            session_id="ses-1",
            role=MessageRole.AGENT,
            content="hola",
            stage=99,  # type: ignore[arg-type]
            status=MessageStatus.COMPLETE,
            started_at=_now(),
        )


def test_message_stage_c_for_consulta() -> None:
    m = Message(
        id="m1",
        session_id="ses-1",
        role=MessageRole.AGENT,
        content="hola",
        stage="C",
        status=MessageStatus.COMPLETE,
        started_at=_now(),
    )
    assert m.stage == "C"


def test_scoring_constraints() -> None:
    ok = ScoringPayload(
        specificity=4.2,
        depth=4.0,
        reusability=3.8,
        uniqueness=4.3,
        value_score=4.1,
    )
    assert ok.value_score == 4.1

    with pytest.raises(Exception):  # noqa: B017, BLE001
        ScoringPayload(
            specificity=0.5, depth=4, reusability=4, uniqueness=4, value_score=4
        )


def test_citation_payload_requires_all_fields() -> None:
    with pytest.raises(Exception):  # noqa: B017, BLE001
        CitationPayload(
            document_id="d1",
            filename="",
            section="§1",
            snippet="snippet",
        )


def test_document_slug_format_enforced() -> None:
    # OK: TEC-flakiness-detection-2026-04-22
    doc = Document(
        id="TEC-flakiness-detection-2026-04-22",
        titulo="x",
        carpeta=CategoryCode.TEC,
        tipo=DocTypeCode.MTEC,
        autoritativo=True,
        estado=DocStatus.VIGENTE,
        autor_name="A",
        autor_role="QA",
        fecha=_now(),
        revision=_now(),
        version="1.0",
        formato="DOCX",
    )
    assert doc.carpeta == "TEC"


def test_document_slug_invalid_format_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017, BLE001
        Document(
            id="invalid-slug",  # no respeta el patrón
            titulo="x",
            carpeta=CategoryCode.TEC,
            tipo=DocTypeCode.MTEC,
            autoritativo=True,
            estado=DocStatus.VIGENTE,
            autor_name="A",
            autor_role="QA",
            fecha=_now(),
            revision=_now(),
            version="1.0",
            formato="DOCX",
        )


# ---------- errors ----------


def test_domain_error_carries_code() -> None:
    err = NotFoundError("not here")
    assert err.code == "NotFoundError"
    assert err.message == "not here"


def test_custom_code_override() -> None:
    err = DomainError("oops", code="OOPS_42")
    assert err.code == "OOPS_42"


def test_rate_limited_retry_after() -> None:
    err = RateLimitedError("slow down", retry_after_seconds=30)
    assert err.retry_after_seconds == 30


def test_external_service_error_service_field() -> None:
    err = ExternalServiceError("anthropic down", service="anthropic")
    assert err.service == "anthropic"


def test_all_error_types_are_domain_error() -> None:
    for cls in (
        NotFoundError,
        UnauthorizedError,
        ForbiddenError,
        ValidationError,
        ConflictError,
    ):
        instance = cls("x")
        assert isinstance(instance, DomainError)
