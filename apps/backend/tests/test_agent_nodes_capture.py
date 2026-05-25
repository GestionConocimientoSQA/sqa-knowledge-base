"""Tests de los nodos free_capture, deep_dive, validation_summary, generation
(Fase 2.4).

Cada nodo se ejerce aislado del grafo. Fakes para gateway y document_repo.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from langgraph.types import Command

from sqa_kb.agent.nodes import (
    make_deep_dive_node,
    make_free_capture_node,
    make_generation_node,
    make_validation_summary_node,
)
from sqa_kb.agent.nodes.deep_dive import QUESTIONS_BY_TYPE
from sqa_kb.agent.state import AgentState, Classification, initial_state
from sqa_kb.domain.entities import Document
from sqa_kb.ports.gateways import ChatMessage, LlmCompletion


def _unwrap(result: dict[str, Any] | Command) -> dict[str, Any]:
    """Devuelve el dict del partial update, sea retorno directo o Command."""
    if isinstance(result, Command):
        return result.update or {}
    return result


def _goto(result: dict[str, Any] | Command) -> str | None:
    return result.goto if isinstance(result, Command) else None


# ===========================================================================
# Fakes compartidos
# ===========================================================================


@dataclass
class _FakeDocRepo:
    created: list[Document] = field(default_factory=list)
    should_fail: bool = False

    async def create(self, document: Document) -> Document:
        if self.should_fail:
            raise RuntimeError("simulated PG error")
        self.created.append(document)
        return document

    # Stub para search (no se usa en estos tests pero el Protocol lo exige).
    async def search(  # noqa: PLR0913
        self, **kwargs  # type: ignore[no-untyped-def]
    ) -> tuple[Sequence[Document], int]:
        return [], 0


@dataclass
class _FakeGateway:
    scoring_response: str = (
        '{"specificity":4,"depth":4,"reusability":3,"uniqueness":4,'
        '"value_score":3.8,"observations":"buena base"}'
    )

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        metadata: Mapping[str, str] | None = None,
    ) -> LlmCompletion:
        return LlmCompletion(
            text=self.scoring_response,
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.0001,
            model=model or "claude-sonnet-4-5",
        )

    async def stream(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError


def _state_with_classification() -> AgentState:
    state = initial_state(
        session_id="ses-1", user_id="oid-1", user_name="Andrés", mode="capture"
    )
    state.topic = "flaky tests en CI"
    state.classification = Classification(
        category="TEC",
        document_type="MTEC",
        confidence=0.9,
        reasoning="técnico",
    )
    return state


def _add_user_msg(state: AgentState, content: str) -> None:
    state.messages.append({"role": "user", "content": content, "stage": None})


def _add_agent_msg(state: AgentState, stage: str, content: str = "x") -> None:
    state.messages.append({"role": "agent", "content": content, "stage": stage})


# ===========================================================================
# free_capture
# ===========================================================================


async def test_free_capture_emits_prompt_when_awaiting_classification() -> None:
    """Vengo de identification con awaiting_confirmation=classification → emito prompt."""
    state = _state_with_classification()
    state.awaiting_confirmation = "classification"
    state.current_stage = "ETAPA_1"
    _add_agent_msg(state, "ETAPA_1", "propuesta")
    _add_user_msg(state, "ok dale")

    node = make_free_capture_node()
    update = await node(state)

    msg = update["messages"][0]
    assert "tus propias palabras" in msg["content"]
    assert update["current_stage"] == "ETAPA_2"
    assert update["awaiting_confirmation"] == "free_capture_more"
    assert update["classification_confirmed"] is True


async def test_free_capture_stores_block_and_advances() -> None:
    """Vuelta siguiente: usuario respondió con el contenido. Devuelve Command
    que delega a deep_dive."""
    state = _state_with_classification()
    state.awaiting_confirmation = "free_capture_more"
    state.current_stage = "ETAPA_2"
    _add_agent_msg(state, "ETAPA_2", "contame")
    _add_user_msg(state, "Los flaky son tests intermitentes por race conditions.")

    node = make_free_capture_node()
    result = await node(state)

    assert _goto(result) == "deep_dive"
    update = _unwrap(result)
    assert update["free_capture_blocks"] == [
        "Los flaky son tests intermitentes por race conditions."
    ]
    assert update["awaiting_confirmation"] is None
    assert update["needs_user_input"] is False


async def test_free_capture_strips_whitespace_from_block() -> None:
    state = _state_with_classification()
    state.awaiting_confirmation = "free_capture_more"
    _add_user_msg(state, "   con espacios  \n")
    node = make_free_capture_node()
    update = _unwrap(await node(state))
    assert update["free_capture_blocks"] == ["con espacios"]


async def test_free_capture_ignores_empty_block() -> None:
    """Si el usuario manda solo espacios, no acumulamos string vacío."""
    state = _state_with_classification()
    state.awaiting_confirmation = "free_capture_more"
    _add_user_msg(state, "   ")
    node = make_free_capture_node()
    update = _unwrap(await node(state))
    assert update["free_capture_blocks"] == []


async def test_free_capture_without_user_msg_asks_again() -> None:
    """Edge: dispatcher nos llevó sin user msg."""
    state = _state_with_classification()
    state.awaiting_confirmation = "classification"
    # state.messages está vacío

    node = make_free_capture_node()
    update = await node(state)

    assert update["needs_user_input"] is True
    assert update["awaiting_confirmation"] == "free_capture_more"


# ===========================================================================
# deep_dive
# ===========================================================================


async def test_deep_dive_emits_questions_for_mtec() -> None:
    state = _state_with_classification()  # document_type=MTEC
    state.current_stage = "ETAPA_2"
    _add_user_msg(state, "los flaky son ...")

    node = make_deep_dive_node()
    update = await node(state)

    msg = update["messages"][0]
    # MTEC tiene 3 preguntas pre-armadas
    for question in QUESTIONS_BY_TYPE["MTEC"]:
        assert question in msg["content"]
    assert update["current_stage"] == "ETAPA_3"
    assert update["awaiting_confirmation"] == "deep_dive_answers"


async def test_deep_dive_emits_generic_question_for_unknown_type() -> None:
    """Si el tipo no está en el banco, degrada a pregunta genérica."""
    state = _state_with_classification()
    state.classification = Classification(
        category="TEC", document_type="NEW", confidence=0.5, reasoning="x"  # type: ignore[arg-type]
    )
    state.current_stage = "ETAPA_2"
    _add_user_msg(state, "x")

    node = make_deep_dive_node()
    update = await node(state)

    msg = update["messages"][0]
    assert "Hay algo más específico" in msg["content"]


async def test_deep_dive_stores_answers_and_advances() -> None:
    state = _state_with_classification()
    state.awaiting_confirmation = "deep_dive_answers"
    state.current_stage = "ETAPA_3"
    _add_agent_msg(state, "ETAPA_3", "preguntas")
    _add_user_msg(state, "1. fue race condition; 2. probamos retry primero")

    node = make_deep_dive_node()
    result = await node(state)

    assert _goto(result) == "validation_summary"
    update = _unwrap(result)
    assert update["awaiting_confirmation"] is None
    assert update["needs_user_input"] is False
    qa = update["deep_dive_qa"]
    assert len(qa) == 1
    answer = next(iter(qa.values()))
    assert "race condition" in answer


async def test_deep_dive_without_classification_bypasses() -> None:
    """Defensivo: si llegamos sin clasificación, no rompemos."""
    state = initial_state(
        session_id="s", user_id="o", user_name="n", mode="capture"
    )
    _add_user_msg(state, "x")

    node = make_deep_dive_node()
    update = await node(state)

    assert update["current_stage"] == "ETAPA_3"
    assert "messages" not in update  # no emite nada, sigue


async def test_deep_dive_stores_empty_answer_does_not_create_entry() -> None:
    """Si el usuario manda solo whitespace, no creamos key vacía."""
    state = _state_with_classification()
    state.awaiting_confirmation = "deep_dive_answers"
    _add_user_msg(state, "   ")

    node = make_deep_dive_node()
    update = _unwrap(await node(state))
    assert update["deep_dive_qa"] == {}


# ===========================================================================
# validation_summary
# ===========================================================================


async def test_validation_summary_emits_full_recap() -> None:
    state = _state_with_classification()
    state.free_capture_blocks = ["bloque A", "bloque B"]
    state.deep_dive_qa = {"P1": "R1"}
    state.current_stage = "ETAPA_3"
    _add_user_msg(state, "ok")

    node = make_validation_summary_node()
    update = await node(state)

    msg = update["messages"][0]
    assert "flaky tests en CI" in msg["content"]
    assert "bloque A" in msg["content"]
    assert "bloque B" in msg["content"]
    assert "P1" in msg["content"]
    assert update["awaiting_confirmation"] == "summary"
    assert update["current_stage"] == "ETAPA_4"


async def test_validation_summary_marks_validated_on_confirmation() -> None:
    state = _state_with_classification()
    state.awaiting_confirmation = "summary"
    _add_agent_msg(state, "ETAPA_4", "resumen")
    _add_user_msg(state, "sí dale")

    node = make_validation_summary_node()
    result = await node(state)

    assert _goto(result) == "generation"
    update = _unwrap(result)
    assert update["summary_validated"] is True
    assert update["awaiting_confirmation"] is None


async def test_validation_summary_aborts_without_classification() -> None:
    state = initial_state(
        session_id="s", user_id="o", user_name="n", mode="capture"
    )
    node = make_validation_summary_node()
    update = await node(state)

    assert update["last_error"]
    assert update["awaiting_confirmation"] == "error"


async def test_validation_summary_shows_anonymization_notice_when_marked() -> None:
    state = _state_with_classification()
    state.is_reusable_content = True
    _add_user_msg(state, "ok")

    node = make_validation_summary_node()
    update = await node(state)
    assert "anonimizar" in update["messages"][0]["content"].lower()


# ===========================================================================
# generation (cadena interna)
# ===========================================================================


async def test_generation_success_creates_document_and_scores() -> None:
    state = _state_with_classification()
    state.free_capture_blocks = ["contenido capturado"]
    state.summary_validated = True
    state.current_stage = "ETAPA_4"

    gateway = _FakeGateway()
    repo = _FakeDocRepo()
    node = make_generation_node(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
    )
    update = await node(state)

    assert update["current_stage"] == "ETAPA_5"
    assert update["generated_document_id"] is not None
    assert update["generated_document_id"].startswith("MTEC-flaky-tests-en-ci-")
    assert update["capture_scoring"] is not None
    assert update["capture_scoring"].specificity == 4
    assert update["needs_user_input"] is False

    # El doc fue creado en el repo
    assert len(repo.created) == 1
    created = repo.created[0]
    assert created.titulo == "Flaky tests en CI"
    assert created.autor_oid == "oid-1"


async def test_generation_continues_when_scoring_fails() -> None:
    """Si scoring tira, persistimos el doc igual y emitimos sin score."""

    @dataclass
    class _ExplodingGateway:
        async def complete(
            self,
            messages: Sequence[ChatMessage],
            *,
            model: str | None = None,
            max_tokens: int = 1024,
            temperature: float = 0.7,
            metadata: Mapping[str, str] | None = None,
        ) -> LlmCompletion:
            raise RuntimeError("upstream LLM down")

        async def stream(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise NotImplementedError

    state = _state_with_classification()
    state.free_capture_blocks = ["x"]
    gateway = _ExplodingGateway()
    repo = _FakeDocRepo()
    node = make_generation_node(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
    )
    update = await node(state)

    # Doc se persistió
    assert len(repo.created) == 1
    # Pero scoring quedó None
    assert update["capture_scoring"] is None
    assert update["generated_document_id"] is not None


async def test_generation_fails_when_repo_errors() -> None:
    """Si el repo rompe, emitimos disculpa con last_error."""
    state = _state_with_classification()
    state.free_capture_blocks = ["x"]
    gateway = _FakeGateway()
    repo = _FakeDocRepo(should_fail=True)
    node = make_generation_node(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
    )
    update = await node(state)

    assert update["last_error"]
    assert "no pude persistirlo" in update["messages"][0]["content"].lower()


async def test_generation_fails_when_classification_missing() -> None:
    """Si llegamos sin clasificación (no debería pasar) → emite error."""
    state = initial_state(
        session_id="s", user_id="o", user_name="n", mode="capture"
    )
    state.topic = "x"
    gateway = _FakeGateway()
    repo = _FakeDocRepo()
    node = make_generation_node(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
    )
    update = await node(state)
    assert update["last_error"]
    assert repo.created == []


async def test_generation_marks_anonymized_when_reusable() -> None:
    state = _state_with_classification()
    state.free_capture_blocks = ["x"]
    state.is_reusable_content = True
    gateway = _FakeGateway()
    repo = _FakeDocRepo()
    node = make_generation_node(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
    )
    await node(state)
    created = repo.created[0]
    assert created.anonimizado is True


# ===========================================================================
# generation — hook indexer (Fase 3.6)
# ===========================================================================


@dataclass
class _FakeIndexer:
    """Fake mínimo del `Indexer` para verificar el hook del nodo."""

    calls: list[dict[str, Any]] = field(default_factory=list)
    should_fail: bool = False

    async def index_document(
        self, document_id: str, *, sections, text=None, replace=True  # type: ignore[no-untyped-def]
    ):
        self.calls.append(
            {
                "document_id": document_id,
                "sections": list(sections),
                "text": text,
                "replace": replace,
            }
        )
        if self.should_fail:
            raise RuntimeError("indexer down")
        from sqa_kb.rag.indexer import IndexerResult

        return IndexerResult(
            document_id=document_id,
            chunks_created=2,
            tokens_embedded=20,
            cost_usd=0.0001,
            sub_batches=1,
            replaced_old_chunks=0,
        )


async def test_generation_calls_indexer_when_configured() -> None:
    """Hook RAG: si hay indexer cableado, dispara index_document_background
    con el content markdown como única Section."""
    state = _state_with_classification()
    state.free_capture_blocks = ["contenido capturado"]
    indexer = _FakeIndexer()
    node = make_generation_node(
        gateway=_FakeGateway(),  # type: ignore[arg-type]
        document_repo=_FakeDocRepo(),  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
    )
    update = await node(state)

    assert update["generated_document_id"] is not None
    # El indexer fue llamado con el id del doc generado.
    assert len(indexer.calls) == 1
    call = indexer.calls[0]
    assert call["document_id"] == update["generated_document_id"]
    # 1 Section con el markdown completo.
    assert len(call["sections"]) == 1
    section = call["sections"][0]
    assert section.title == "Flaky tests en CI"
    # El content del Section es el markdown renderizado (contiene el title).
    assert "Flaky tests en CI" in section.content


async def test_generation_no_indexer_no_op() -> None:
    """Sin indexer (back-compat), el nodo no intenta indexar."""
    state = _state_with_classification()
    state.free_capture_blocks = ["x"]
    node = make_generation_node(
        gateway=_FakeGateway(),  # type: ignore[arg-type]
        document_repo=_FakeDocRepo(),  # type: ignore[arg-type]
        # sin indexer
    )
    update = await node(state)
    # El nodo cerró OK sin haber tocado ningún indexer.
    assert update["generated_document_id"] is not None
    assert update["current_stage"] == "ETAPA_5"


async def test_generation_indexer_failure_does_not_break_response() -> None:
    """Si el indexer falla, el flujo del agente igual cierra OK.

    `index_document_background` swallow excepciones — el usuario ve el
    doc creado aunque el RAG no se haya enterado. Se puede reintentar
    con `scripts/reindex_all.py`.
    """
    state = _state_with_classification()
    state.free_capture_blocks = ["x"]
    indexer = _FakeIndexer(should_fail=True)
    node = make_generation_node(
        gateway=_FakeGateway(),  # type: ignore[arg-type]
        document_repo=_FakeDocRepo(),  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
    )
    update = await node(state)

    # El doc se creó, el response salió.
    assert update["generated_document_id"] is not None
    assert update["current_stage"] == "ETAPA_5"
    # El indexer fue intentado.
    assert len(indexer.calls) == 1
    # NO hay last_error — la indexación es no-bloqueante.
    assert "last_error" not in update or not update.get("last_error")
