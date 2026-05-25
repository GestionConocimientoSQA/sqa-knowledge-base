"""Tests del Markdown generator (Fase 2.4).

Cubren:
- Slug builder: acentos, mayúsculas, símbolos, max_words.
- ID matchea el regex Slug del dominio.
- Render del documento incluye todas las secciones.
- Edge: classification/topic ausentes lanzan ValueError.
- is_anonymized se refleja en la tabla.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import TypeAdapter

from sqa_kb.agent.markdown_generator import (
    GeneratedDocument,
    _slugify_topic,
    _titlecase_topic,
    build_document_id,
    render_markdown_document,
)
from sqa_kb.agent.state import (
    AgentState,
    Classification,
    initial_state,
)
from sqa_kb.domain.entities import Slug

# ===========================================================================
# Slug builder
# ===========================================================================


def test_slugify_removes_accents() -> None:
    assert _slugify_topic("detección de fallas") == "deteccion-de-fallas"


def test_slugify_lowercases_and_drops_symbols() -> None:
    assert _slugify_topic("CI/CD pipelines! v2.0") == "cicd-pipelines-v20"


def test_slugify_max_words_truncates() -> None:
    assert (
        _slugify_topic("una guía larga sobre integración continua y entrega")
        == "una-guia-larga-sobre"
    )


def test_slugify_empty_falls_back() -> None:
    assert _slugify_topic("") == "sin-topic"
    assert _slugify_topic("!!!") == "sin-topic"


def test_slugify_only_whitespace_falls_back() -> None:
    assert _slugify_topic("   \t\n  ") == "sin-topic"


def test_build_document_id_matches_domain_slug_regex() -> None:
    """El ID generado debe pasar la validación del tipo Slug del dominio."""
    fecha = datetime(2026, 5, 23, tzinfo=UTC)
    doc_id = build_document_id(
        document_type="MTEC", topic="detección de flaky tests", fecha=fecha
    )
    assert doc_id == "MTEC-deteccion-de-flaky-tests-2026-05-23"
    # Validar contra el TypeAdapter del Slug (regex domain).
    adapter = TypeAdapter(Slug)
    adapter.validate_python(doc_id)  # no lanza ⇒ OK


def test_build_document_id_with_short_topic() -> None:
    fecha = datetime(2026, 5, 23, tzinfo=UTC)
    doc_id = build_document_id(document_type="POL", topic="foo", fecha=fecha)
    assert doc_id == "POL-foo-2026-05-23"


# ===========================================================================
# titlecase
# ===========================================================================


def test_titlecase_preserves_acronyms() -> None:
    """Si usáramos .title() se rompería CI/CD → Ci/Cd."""
    assert _titlecase_topic("CI/CD pipelines") == "CI/CD pipelines"


def test_titlecase_capitalizes_first_letter() -> None:
    assert _titlecase_topic("flaky tests") == "Flaky tests"


def test_titlecase_empty() -> None:
    assert _titlecase_topic("") == ""


# ===========================================================================
# render_markdown_document
# ===========================================================================


def _state_with_capture(*, anonymize: bool = False) -> AgentState:
    state = initial_state(
        session_id="ses-1",
        user_id="oid-1",
        user_name="Andrés",
        mode="capture",
        user_role="QA Architect",
    )
    state.topic = "detección de tests flaky"
    state.classification = Classification(
        category="TEC",
        document_type="MTEC",
        confidence=0.9,
        reasoning="técnico",
    )
    state.free_capture_blocks = [
        "Los tests flaky son tests que pasan a veces y fallan otras.",
        "La causa más común son race conditions y timing.",
    ]
    state.deep_dive_qa = {
        "Cuál fue el problema original": "CI verde un día y rojo al siguiente sin cambios."
    }
    state.is_reusable_content = anonymize
    return state


def test_render_includes_all_sections() -> None:
    state = _state_with_capture()
    fecha = datetime(2026, 5, 23, tzinfo=UTC)
    doc = render_markdown_document(state, now=fecha)

    assert isinstance(doc, GeneratedDocument)
    assert doc.format == "MD"
    assert "Detección de tests flaky" in doc.content  # title capitalized
    assert "TEC" in doc.content
    assert "MTEC" in doc.content
    assert "Andrés" in doc.content
    assert "QA Architect" in doc.content
    assert "race conditions" in doc.content
    assert "CI verde un día" in doc.content
    assert doc.document_id == "MTEC-deteccion-de-tests-flaky-2026-05-23"


def test_render_marks_anonymized_in_metadata_table() -> None:
    state = _state_with_capture(anonymize=True)
    doc = render_markdown_document(state)
    assert "Anonimizado" in doc.content
    assert doc.is_anonymized is True


def test_render_skips_anonymized_row_when_not_marked() -> None:
    state = _state_with_capture(anonymize=False)
    doc = render_markdown_document(state)
    assert "Anonimizado" not in doc.content


def test_render_handles_empty_deep_dive() -> None:
    state = _state_with_capture()
    state.deep_dive_qa = {}
    doc = render_markdown_document(state)
    # El template debería omitir la sección "Precisiones" si está vacía.
    assert "Precisiones" not in doc.content


def test_render_raises_without_classification() -> None:
    state = initial_state(
        session_id="s", user_id="o", user_name="n", mode="capture"
    )
    state.topic = "x"
    with pytest.raises(ValueError, match="classification"):
        render_markdown_document(state)


def test_render_raises_without_topic() -> None:
    state = initial_state(
        session_id="s", user_id="o", user_name="n", mode="capture"
    )
    state.classification = Classification(
        category="TEC", document_type="MTEC", confidence=0.9, reasoning="x"
    )
    state.topic = ""
    with pytest.raises(ValueError, match="topic"):
        render_markdown_document(state)


def test_render_uses_provided_fecha() -> None:
    state = _state_with_capture()
    fecha = datetime(2024, 1, 15, tzinfo=UTC)
    doc = render_markdown_document(state, now=fecha)
    assert "2024-01-15" in doc.content
    assert doc.fecha == fecha
