"""Tests del nodo `consultation` (Fase 2.5, refactor en Fase 3.5).

Cubren:
- Pregunta vacía / sin user msg → pide pregunta.
- Sin chunks en KB → mensaje "no encontré".
- Con chunks (HybridChunk) → llama al LLM con content real, emite
  respuesta con citaciones.
- Threshold de relevancia: alta (distance<=0.5) vs media (<=0.8) vs
  sin_resultados (>0.8). `distance = 1 - score` del hybrid searcher.
- Síntesis del LLM falla → mensaje degradado con last_error.
- citations acumuladas en state (no se pierden entre turnos).

Fase 3.5: el nodo consume `HybridSearcher.search()` → `HybridChunk` con
`content` real. Antes (2.5) tomaba `ExistingDocument` y stub-construía
chunks desde `filename`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from sqa_kb.agent.nodes import make_consultation_node
from sqa_kb.agent.state import AgentState, Citation, initial_state
from sqa_kb.ports.gateways import ChatMessage, LlmCompletion
from sqa_kb.rag.hybrid_search import HybridChunk

# ===========================================================================
# Fakes
# ===========================================================================


def _chunk(
    *,
    document_id: str,
    score: float = 0.9,
    content: str = "Los tests flaky son intermitentes y deben aislarse.",
    section_title: str = "Definición",
) -> HybridChunk:
    return HybridChunk(
        chunk_id=f"chk-{document_id}",
        document_id=document_id,
        chunk_index=0,
        content=content,
        snippet=content[:240],
        section_title=section_title,
        score=score,
        vector_score=score,
        fulltext_score=0.0,
        document_title="Doc",
        document_type="MTEC",
        document_category="TEC",
        authoritative=False,
    )


@dataclass
class _FakeSearcher:
    chunks_to_return: list[HybridChunk] = field(default_factory=list)

    async def search(
        self,
        query: str,  # noqa: ARG002
        *,
        top_k: int = 5,  # noqa: ARG002
        carpetas: Iterable[str] | None = None,  # noqa: ARG002
        tipos: Iterable[str] | None = None,  # noqa: ARG002
        authoritative_only: bool = False,  # noqa: ARG002
        authoritative_boost: float | None = None,  # noqa: ARG002
    ) -> Sequence[HybridChunk]:
        return list(self.chunks_to_return)


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
        searcher=_FakeSearcher(),  # type: ignore[arg-type]
    )
    update = await node(state)
    assert "Decime qué querés consultar" in update["messages"][0]["content"]
    assert update["awaiting_confirmation"] == "consult_more"


async def test_consultation_empty_message_treated_as_no_query() -> None:
    """Edge: usuario manda solo whitespace."""
    state = _state(question="   \n  ")
    node = make_consultation_node(
        gateway=_FakeGateway(),  # type: ignore[arg-type]
        searcher=_FakeSearcher(),  # type: ignore[arg-type]
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
        searcher=_FakeSearcher(),  # type: ignore[arg-type]
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
    chunks = [_chunk(document_id="TEC-flaky-2026-01-01", score=0.9)]
    node = make_consultation_node(
        gateway=_FakeGateway(),  # type: ignore[arg-type]
        searcher=_FakeSearcher(chunks_to_return=chunks),  # type: ignore[arg-type]
    )
    update = await node(state)
    msg = update["messages"][0]
    assert "Los tests flaky son intermitentes" in msg["content"]
    # Citación renderizada por el template:
    assert "TEC-flaky-2026-01-01" in msg["content"]
    # score 0.9 → distance 0.1 → relevancia alta.
    assert update["relevance_level"] == "alta"


async def test_consultation_classifies_relevance_thresholds() -> None:
    """`distance = 1 - score_combinado`. Verificamos los 3 buckets."""
    from sqa_kb.agent.nodes.consultation import _classify_relevance

    assert _classify_relevance(0.30) == "alta"
    assert _classify_relevance(0.50) == "alta"  # boundary inclusive
    assert _classify_relevance(0.51) == "media"
    assert _classify_relevance(0.80) == "media"
    assert _classify_relevance(0.81) == "sin_resultados"


async def test_consultation_relevance_calculated_from_score() -> None:
    """End-to-end: score=0.4 → distance=0.6 → bucket "media"."""
    state = _state(question="x")
    chunks = [_chunk(document_id="TEC-mid", score=0.4)]
    node = make_consultation_node(
        gateway=_FakeGateway(),  # type: ignore[arg-type]
        searcher=_FakeSearcher(chunks_to_return=chunks),  # type: ignore[arg-type]
    )
    update = await node(state)
    assert update["relevance_level"] == "media"


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
    chunks = [_chunk(document_id="NEW-2026-01-01")]
    node = make_consultation_node(
        gateway=_FakeGateway(),  # type: ignore[arg-type]
        searcher=_FakeSearcher(chunks_to_return=chunks),  # type: ignore[arg-type]
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
    chunks = [_chunk(document_id="TEC-x-2026-01-01")]
    node = make_consultation_node(
        gateway=_FakeGateway(should_fail=True),  # type: ignore[arg-type]
        searcher=_FakeSearcher(chunks_to_return=chunks),  # type: ignore[arg-type]
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
        searcher=_FakeSearcher(),  # type: ignore[arg-type]
    )
    update = await node(state)
    assert update["current_query"] == "qué es flaky"
