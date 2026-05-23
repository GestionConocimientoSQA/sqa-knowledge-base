"""Tests unitarios del AgentState (Fase 2.1).

Cubren happy path + validaciones de Pydantic. No tocan DB ni LangGraph.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sqa_kb.agent.state import (
    AgentState,
    Citation,
    Classification,
    ExistingDocument,
    Traceability,
    initial_state,
)

# ===========================================================================
# Construction
# ===========================================================================


def test_initial_state_for_capture_mode() -> None:
    state = initial_state(
        session_id="ses-1",
        user_id="oid-1",
        user_name="Andrés",
        mode="capture",
    )
    assert state.session_id == "ses-1"
    assert state.mode == "capture"
    assert state.current_stage == "ETAPA_0"
    assert state.messages == []
    assert state.classification is None
    assert state.total_cost_usd == 0.0
    assert state.needs_user_input is False


def test_initial_state_accepts_user_role() -> None:
    state = initial_state(
        session_id="ses-1",
        user_id="oid-1",
        user_name="A",
        mode="consultation",
        user_role="Automation Engineer",
    )
    assert state.user_role == "Automation Engineer"


def test_initial_state_rejects_invalid_mode() -> None:
    with pytest.raises(ValidationError):
        initial_state(
            session_id="ses-1",
            user_id="oid-1",
            user_name="A",
            mode="invalid_mode",  # type: ignore[arg-type]
        )


# ===========================================================================
# Defaults
# ===========================================================================


def test_default_collections_are_independent() -> None:
    """Sanity check del `default_factory=list` — dos instancias no deben
    compartir referencia."""
    a = initial_state(session_id="a", user_id="o", user_name="n", mode="capture")
    b = initial_state(session_id="b", user_id="o", user_name="n", mode="capture")
    a.free_capture_blocks.append("foo")
    assert b.free_capture_blocks == []


def test_default_messages_empty() -> None:
    state = initial_state(session_id="s", user_id="o", user_name="n", mode="capture")
    assert state.messages == []
    assert state.active_skills == []
    assert state.existing_documents == []
    assert state.citations == []


# ===========================================================================
# Sub-modelos
# ===========================================================================


def test_classification_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        Classification(
            category="TEC",
            document_type="MTEC",
            confidence=1.5,
            reasoning="x",
        )


def test_classification_rejects_negative_confidence() -> None:
    with pytest.raises(ValidationError):
        Classification(
            category="TEC",
            document_type="MTEC",
            confidence=-0.1,
            reasoning="x",
        )


def test_citation_position_must_be_non_negative() -> None:
    with pytest.raises(ValidationError):
        Citation(
            document_id="d1",
            filename="f.md",
            chunk_id="c1",
            snippet="...",
            position=-1,
        )


def test_existing_document_distance_must_be_non_negative() -> None:
    with pytest.raises(ValidationError):
        ExistingDocument(
            document_id="d1",
            filename="f.md",
            category="TEC",
            document_type="MTEC",
            distance=-0.01,
            created_at="2026-01-01",
        )


def test_traceability_optional_source_version() -> None:
    """`source_version` opcional para casos donde la fuente no tiene versionado."""
    t = Traceability(
        approved_by="oid-owner",
        approval_date="2026-05-01",
        source_origin="SharePoint",
    )
    assert t.source_version is None


# ===========================================================================
# Extra fields forbidden
# ===========================================================================


def test_agent_state_forbids_extra_fields() -> None:
    """Si un nodo intenta meter una key fuera del schema falla rápido."""
    with pytest.raises(ValidationError):
        AgentState(
            session_id="s",
            user_id="o",
            user_name="n",
            mode="capture",
            current_stage="ETAPA_0",
            something_random=True,  # type: ignore[call-arg]
        )


def test_classification_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Classification(
            category="TEC",
            document_type="MTEC",
            confidence=0.9,
            reasoning="x",
            foo="bar",  # type: ignore[call-arg]
        )


# ===========================================================================
# Mode-specific fields
# ===========================================================================


def test_capture_fields_optional_at_init() -> None:
    state = initial_state(session_id="s", user_id="o", user_name="n", mode="capture")
    assert state.topic is None
    assert state.classification is None
    assert state.is_reusable_content is None
    assert state.summary_validated is False
    assert state.generated_document_id is None
    assert state.capture_scoring is None


def test_consultation_fields_optional_at_init() -> None:
    state = initial_state(
        session_id="s", user_id="o", user_name="n", mode="consultation"
    )
    assert state.current_query is None
    assert state.relevance_level is None
    assert state.retrieved_chunks == []
    assert state.citations == []


def test_ingestion_fields_optional_at_init() -> None:
    state = initial_state(
        session_id="s", user_id="o", user_name="n", mode="ingestion"
    )
    assert state.ingestion_item_id is None
    assert state.extracted_text is None
    assert state.sections_detected is None
    assert state.traceability is None


def test_state_serializes_to_json_and_back() -> None:
    """Roundtrip JSON — el checkpointer hace esto en cada `aput`."""
    state = initial_state(
        session_id="ses-1", user_id="oid-1", user_name="A", mode="capture"
    )
    state.classification = Classification(
        category="TEC",
        document_type="MTEC",
        confidence=0.92,
        reasoning="topic claramente técnico",
    )
    state.total_input_tokens = 42
    state.total_cost_usd = 0.000615

    raw = state.model_dump_json()
    restored = AgentState.model_validate_json(raw)

    assert restored == state
    assert restored.classification is not None
    assert restored.classification.confidence == pytest.approx(0.92)


# ===========================================================================
# Counters
# ===========================================================================


def test_counters_reject_negative() -> None:
    with pytest.raises(ValidationError):
        AgentState(
            session_id="s",
            user_id="o",
            user_name="n",
            mode="capture",
            current_stage="ETAPA_0",
            total_input_tokens=-1,
        )
    with pytest.raises(ValidationError):
        AgentState(
            session_id="s",
            user_id="o",
            user_name="n",
            mode="capture",
            current_stage="ETAPA_0",
            total_cost_usd=-0.01,
        )


def test_retry_count_non_negative() -> None:
    with pytest.raises(ValidationError):
        AgentState(
            session_id="s",
            user_id="o",
            user_name="n",
            mode="capture",
            current_stage="ETAPA_0",
            retry_count=-1,
        )
