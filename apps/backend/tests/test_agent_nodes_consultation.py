"""Tests del nodo `consultation` (Fase 2.5, modo B).

Cubren:
- Pregunta vacía / sin user msg → pide pregunta.
- Sin chunks en KB → mensaje "no encontré".
- Con chunks → llama al LLM, emite respuesta con citaciones.
- Threshold de relevancia: alta (<=0.5) vs media (<=0.8).
- Síntesis del LLM falla → mensaje degradado con last_error.
- citations acumuladas en state (no se pierden entre turnos).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqa_kb.agent.nodes import make_consultation_node
from sqa_kb.agent.state import AgentState, Citation, initial_state
from sqa_kb.domain.entities import Document
from sqa_kb.domain.value_objects import CategoryCode, DocStatus, DocTypeCode
from sqa_kb.ports.gateways import ChatMessage, LlmCompletion

# ===========================================================================
# Fakes
# ===========================================================================


def _doc(id: str) -> Document:
    now = datetime.now(UTC)
    return Document(
        id=id,
        titulo="Doc",
        carpeta=CategoryCode.TEC,
        tipo=DocTypeCode.MTEC,
        autoritativo=False,
        estado=DocStatus.VIGENTE,
        autor_name="A",
        autor_role="QA",
        fecha=now,
        revision=now,
        version="1.0",
        formato="MD",
    )


@dataclass
class _FakeDocRepo:
    docs_to_return: list[Document] = field(default_factory=list)

    async def search(  # noqa: PLR0913
        self, **kwargs  # type: ignore[no-untyped-def]
    ) -> tuple[Sequence[Document], int]:
        return list(self.docs_to_return), len(self.docs_to_return)


@dataclass
class _FakeGateway:
    answer_text: str = "Los tests flaky son intermitentes [doc:TEC-flaky-2026-01-01]."
    should_fail: bool = False

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        metadata: Mapping[str, str] | None = None,
    ) -> LlmCompletion:
        if self.should_fail:
            raise RuntimeError("LLM down")
        return LlmCompletion(
            text=self.answer_text,
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.0001,
            model=model or "claude-sonnet-4-5",
        )

    async def stream(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError


def _state(question: str | None = None) -> AgentState:
    s = initial_state(
        session_id="ses-1", user_id="oid-1", user_name="Andrés", mode="consultation"
    )
    if question:
        s.messages.append({"role": "user", "content": question, "stage": None})
    return s


# ===========================================================================
# Empty / edge cases
# ===========================================================================


async def test_consultation_asks_for_query_when_no_user_msg() -> None:
    state = _state()
    node = make_consultation_node(
        gateway=_FakeGateway(),  # type: ignore[arg-type]
        document_repo=_FakeDocRepo(),  # type: ignore[arg-type]
    )
    update = await node(state)
    assert "Decime qué querés consultar" in update["messages"][0]["content"]
    assert update["awaiting_confirmation"] == "consult_more"


async def test_consultation_empty_message_treated_as_no_query() -> None:
    """Edge: usuario manda solo whitespace."""
    state = _state(question="   \n  ")
    node = make_consultation_node(
        gateway=_FakeGateway(),  # type: ignore[arg-type]
        document_repo=_FakeDocRepo(),  # type: ignore[arg-type]
    )
    update = await node(state)
    assert "Decime qué" in update["messages"][0]["content"]


# ===========================================================================
# No results
# ===========================================================================


async def test_consultation_emits_no_results_when_kb_empty() -> None:
    state = _state(question="qué es lo más raro del KB")
    node = make_consultation_node(
        gateway=_FakeGateway(),  # type: ignore[arg-type]
        document_repo=_FakeDocRepo(),  # type: ignore[arg-type]
    )
    update = await node(state)
    msg = update["messages"][0]
    assert "No encontré información" in msg["content"]
    assert update["relevance_level"] == "sin_resultados"
    assert update["current_query"] == "qué es lo más raro del KB"


# ===========================================================================
# Happy path con chunks
# ===========================================================================


async def test_consultation_synthesizes_with_chunks() -> None:
    state = _state(question="qué son flaky tests")
    node = make_consultation_node(
        gateway=_FakeGateway(),  # type: ignore[arg-type]
        document_repo=_FakeDocRepo(docs_to_return=[_doc("TEC-flaky-2026-01-01")]),  # type: ignore[arg-type]
    )
    update = await node(state)
    msg = update["messages"][0]
    assert "Los tests flaky son intermitentes" in msg["content"]
    # Citación renderizada por el template:
    assert "TEC-flaky-2026-01-01" in msg["content"]
    # Stub distance = 0.30 → relevancia alta.
    assert update["relevance_level"] == "alta"


async def test_consultation_classifies_relevance_media_between_thresholds() -> None:
    """Stub: 4 docs → distances 0.30/0.40/0.50/0.60. El primero (0.30) cae en
    "alta". Para forzar "media" probamos con un solo doc cuyo distance sea
    >0.5 — pero el stub siempre da 0.30 al primero. Probamos la función
    helper directo."""
    from sqa_kb.agent.nodes.consultation import _classify_relevance

    assert _classify_relevance(0.30) == "alta"
    assert _classify_relevance(0.50) == "alta"  # boundary inclusive
    assert _classify_relevance(0.51) == "media"
    assert _classify_relevance(0.80) == "media"
    assert _classify_relevance(0.81) == "sin_resultados"


async def test_consultation_appends_citations_to_state() -> None:
    """Si state ya tenía citations de turno anterior, las nuevas se suman."""
    state = _state(question="x")
    state.citations = [
        Citation(
            document_id="OLD",
            filename="old.md",
            chunk_id="c0",
            snippet="...",
            position=0,
        )
    ]
    node = make_consultation_node(
        gateway=_FakeGateway(),  # type: ignore[arg-type]
        document_repo=_FakeDocRepo(docs_to_return=[_doc("NEW-2026-01-01")]),  # type: ignore[arg-type]
    )
    update = await node(state)
    # OLD + NEW
    cite_ids = [c.document_id for c in update["citations"]]
    assert "OLD" in cite_ids
    assert "NEW-2026-01-01" in cite_ids


# ===========================================================================
# Errores
# ===========================================================================


async def test_consultation_degraded_when_llm_fails() -> None:
    state = _state(question="x")
    node = make_consultation_node(
        gateway=_FakeGateway(should_fail=True),  # type: ignore[arg-type]
        document_repo=_FakeDocRepo(docs_to_return=[_doc("TEC-x-2026-01-01")]),  # type: ignore[arg-type]
    )
    update = await node(state)
    msg = update["messages"][0]
    assert "no pude armar una respuesta" in msg["content"].lower()
    assert update["last_error"] == "synthesis_failed"
    # Igualmente queda awaiting_confirmation=consult_more para reintento.
    assert update["awaiting_confirmation"] == "consult_more"


async def test_consultation_persists_query_in_state() -> None:
    state = _state(question="qué es flaky")
    node = make_consultation_node(
        gateway=_FakeGateway(),  # type: ignore[arg-type]
        document_repo=_FakeDocRepo(),  # type: ignore[arg-type]
    )
    update = await node(state)
    assert update["current_query"] == "qué es flaky"
