"""Tests del filename builder (Fase 4.5)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqa_kb.documents.filename import build_filename

_FECHA = datetime(2026, 5, 26, tzinfo=UTC)


def test_build_filename_basic() -> None:
    name = build_filename(
        document_type="MTEC", topic="flaky tests en CI", fecha=_FECHA, extension="docx"
    )
    assert name == "MTEC-flaky-tests-en-ci-2026-05-26.docx"


def test_build_filename_strips_leading_dot_from_extension() -> None:
    name = build_filename(
        document_type="POL", topic="retención", fecha=_FECHA, extension=".pdf"
    )
    assert name.endswith(".pdf")
    assert not name.endswith("..pdf")


def test_build_filename_lowercases_extension() -> None:
    name = build_filename(
        document_type="PRES", topic="roadmap", fecha=_FECHA, extension="PPTX"
    )
    assert name.endswith(".pptx")


def test_build_filename_empty_extension_no_dot() -> None:
    name = build_filename(
        document_type="MTEC", topic="x", fecha=_FECHA, extension=""
    )
    assert "." not in name
    assert name.startswith("MTEC-")
    assert name.endswith("-2026-05-26")


def test_build_filename_accents_normalized() -> None:
    name = build_filename(
        document_type="GUIA", topic="migración a postgres", fecha=_FECHA, extension="md"
    )
    # Los acentos se normalizan (migración → migracion).
    assert "migracion" in name
    assert "ó" not in name


def test_build_filename_date_format() -> None:
    name = build_filename(
        document_type="MTEC",
        topic="x",
        fecha=datetime(2026, 1, 5, tzinfo=UTC),
        extension="pdf",
    )
    assert "2026-01-05" in name
