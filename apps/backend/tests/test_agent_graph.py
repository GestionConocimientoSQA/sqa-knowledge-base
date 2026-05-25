"""Tests del grafo del agente — Fase 2.4 (dispatcher por current_stage).

El grafo ahora entra por START → dispatcher → un nodo → END (una vuelta
por invoke). Estos tests cubren:

- `_stage_dispatcher` para cada combinación de mode + current_stage.
- `_has_agent_msg` helper.
- `build_graph` compila con y sin checkpointer.
- Flujo end-to-end multi-turno (capture): welcome → identification →
  free_capture → deep_dive → validation_summary → generation.
- Modo B y C: solo welcome, después END (2.5 los completa).

LLM mockeado — sin tocar Anthropic.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END

from sqa_kb.agent.graph import _has_agent_msg, _stage_dispatcher, build_graph
from sqa_kb.agent.state import AgentState, initial_state
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
    search_docs: list[Document] = field(default_factory=list)
    created: list[Document] = field(default_factory=list)

    async def search(  # noqa: PLR0913
        self, **kwargs  # type: ignore[no-untyped-def]
    ) -> tuple[Sequence[Document], int]:
        return list(self.search_docs), len(self.search_docs)

    async def create(self, document: Document) -> Document:
        self.created.append(document)
        return document


@dataclass
class _FakeGateway:
    classify_response: str = (
        '{"category":"TEC","document_type":"MTEC",'
        '"confidence":0.85,"reasoning":"técnico"}'
    )
    score_response: str = (
        '{"specificity":4,"depth":4,"reusability":3,"uniqueness":4,'
        '"value_score":3.8,"observations":"buena"}'
    )
    calls: list[str] = field(default_factory=list)

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        metadata: Mapping[str, str] | None = None,
    ) -> LlmCompletion:
        # Diferencia clasificación vs scoring por contenido del prompt.
        is_scoring = any("evaluador del valor" in m.content for m in messages)
        text = self.score_response if is_scoring else self.classify_response
        self.calls.append("score" if is_scoring else "classify")
        return LlmCompletion(
            text=text,
            input_tokens=1,
            output_tokens=1,
            cost_usd=0.0,
            model=model or "claude-sonnet-4-5",
        )

    async def stream(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError


def _state(mode: str, **overrides) -> AgentState:  # type: ignore[no-untyped-def]
    state = initial_state(
        session_id="s", user_id="o", user_name="n", mode=mode  # type: ignore[arg-type]
    )
    for k, v in overrides.items():
        setattr(state, k, v)
    return state


# ===========================================================================
# _has_agent_msg
# ===========================================================================


def test_has_agent_msg_true_when_present() -> None:
    state = _state("capture")
    state.messages = [{"role": "agent", "content": "hi"}]
    assert _has_agent_msg(state) is True


def test_has_agent_msg_false_when_only_user_messages() -> None:
    state = _state("capture")
    state.messages = [{"role": "user", "content": "hi"}]
    assert _has_agent_msg(state) is False


def test_has_agent_msg_false_when_empty() -> None:
    state = _state("capture")
    assert _has_agent_msg(state) is False


# ===========================================================================
# _stage_dispatcher
# ===========================================================================


def test_dispatcher_routes_to_welcome_when_no_agent_msg() -> None:
    """Sesión nueva sin saludo previo → welcome."""
    state = _state("capture")
    assert _stage_dispatcher(state) == "welcome"


def test_dispatcher_routes_to_welcome_even_in_other_modes_if_first_turn() -> None:
    state = _state("consultation")
    assert _stage_dispatcher(state) == "welcome"


def test_dispatcher_routes_consultation_after_welcome_to_end() -> None:
    """Modo B post-welcome no tiene branch en 2.4 → END."""
    state = _state("consultation")
    state.messages = [{"role": "agent", "content": "hi", "stage": "ETAPA_0"}]
    state.current_stage = "ETAPA_0"
    assert _stage_dispatcher(state) == END


def test_dispatcher_routes_consultation_with_mode_choice_to_consultation() -> None:
    """En 2.5 modo B: awaiting=mode_choice + mode=consultation → consultation."""
    state = _state("consultation")
    state.messages = [{"role": "agent", "content": "hi", "stage": "ETAPA_0"}]
    state.awaiting_confirmation = "mode_choice"
    assert _stage_dispatcher(state) == "consultation"


def test_dispatcher_routes_consultation_with_consult_more() -> None:
    state = _state("consultation")
    state.messages = [{"role": "agent", "content": "hi", "stage": "consult_search"}]
    state.awaiting_confirmation = "consult_more"
    assert _stage_dispatcher(state) == "consultation"


def test_dispatcher_routes_consultation_unknown_awaiting_to_end() -> None:
    state = _state("consultation")
    state.messages = [{"role": "agent", "content": "hi", "stage": "x"}]
    state.awaiting_confirmation = "weird"
    assert _stage_dispatcher(state) == END


def test_dispatcher_routes_ingestion_after_welcome_to_classify() -> None:
    """En 2.5 modo C: awaiting=mode_choice + mode=ingestion → ingestion_classify."""
    state = _state("ingestion")
    state.messages = [{"role": "agent", "content": "hi", "stage": "ETAPA_0"}]
    state.awaiting_confirmation = "mode_choice"
    assert _stage_dispatcher(state) == "ingestion_classify"


def test_dispatcher_routes_ingestion_with_meta_to_traceability() -> None:
    state = _state("ingestion")
    state.messages = [{"role": "agent", "content": "hi", "stage": "classify_ingest"}]
    state.awaiting_confirmation = "ingest_meta"
    assert _stage_dispatcher(state) == "ingestion_traceability"


def test_dispatcher_routes_ingestion_unknown_awaiting_to_end() -> None:
    state = _state("ingestion")
    state.messages = [{"role": "agent", "content": "hi", "stage": "x"}]
    state.awaiting_confirmation = "weird"
    assert _stage_dispatcher(state) == END


@pytest.mark.parametrize(
    "awaiting,expected",
    [
        ("mode_choice", "identification"),
        ("topic", "identification"),
        ("classification", "free_capture"),
        ("update_decision", "free_capture"),
        ("free_capture_more", "free_capture"),
        ("deep_dive_answers", "deep_dive"),
        ("summary", "validation_summary"),
    ],
)
def test_dispatcher_routes_capture_by_awaiting(awaiting: str, expected: str) -> None:
    """El dispatcher routea por `awaiting_confirmation` (no por stage)."""
    state = _state("capture")
    state.messages = [{"role": "agent", "content": "hi", "stage": "ETAPA_X"}]
    state.awaiting_confirmation = awaiting
    assert _stage_dispatcher(state) == expected


def test_dispatcher_error_awaiting_ends() -> None:
    state = _state("capture")
    state.messages = [{"role": "agent", "content": "hi", "stage": "ETAPA_4"}]
    state.awaiting_confirmation = "error"
    assert _stage_dispatcher(state) == END


def test_dispatcher_no_awaiting_and_finished_ends() -> None:
    """Estado terminal (post-generation): awaiting=None, stage=ETAPA_5."""
    state = _state("capture")
    state.messages = [{"role": "agent", "content": "hi", "stage": "ETAPA_5"}]
    state.current_stage = "ETAPA_5"
    state.summary_validated = True
    assert _stage_dispatcher(state) == END


def test_dispatcher_unknown_awaiting_ends() -> None:
    state = _state("capture")
    state.messages = [{"role": "agent", "content": "hi", "stage": "X"}]
    state.awaiting_confirmation = "WEIRD_AWAIT_99"
    assert _stage_dispatcher(state) == END


def test_dispatcher_fallback_for_unvalidated_etapa_4() -> None:
    """Edge: state quedó en ETAPA_4 sin summary_validated y sin awaiting.
    Re-emite el resumen para que el usuario lo vea de nuevo."""
    state = _state("capture")
    state.messages = [{"role": "agent", "content": "hi", "stage": "ETAPA_4"}]
    state.current_stage = "ETAPA_4"
    state.summary_validated = False
    state.awaiting_confirmation = None
    assert _stage_dispatcher(state) == "validation_summary"


# ===========================================================================
# build_graph
# ===========================================================================


def test_build_graph_compiles_without_checkpointer() -> None:
    gateway = _FakeGateway()
    repo = _FakeDocRepo()
    graph = build_graph(gateway=gateway, document_repo=repo)  # type: ignore[arg-type]
    assert graph is not None


def test_build_graph_compiles_with_in_memory_checkpointer() -> None:
    gateway = _FakeGateway()
    repo = _FakeDocRepo()
    graph = build_graph(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
        checkpointer=InMemorySaver(),
    )
    assert graph is not None


# ===========================================================================
# End-to-end multi-turno (capture)
# ===========================================================================


async def test_capture_flow_first_turn_runs_welcome_only() -> None:
    """Primera invocación con state inicial → solo welcome, END."""
    gateway = _FakeGateway()
    repo = _FakeDocRepo()
    graph = build_graph(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
        checkpointer=InMemorySaver(),
    )
    state = initial_state(
        session_id="ses-flow", user_id="o", user_name="Andrés", mode="capture"
    )
    config = {"configurable": {"thread_id": "ses-flow"}}
    result = await graph.ainvoke(state, config=config)

    agent_msgs = [m for m in result["messages"] if m.get("role") == "agent"]
    assert len(agent_msgs) == 1
    assert agent_msgs[0]["stage"] == "ETAPA_0"
    # Identification NO se ejecutó (no había user msg). topic puede no estar
    # presente en el dict de salida (defaults del Pydantic dict).
    assert result.get("topic") is None
    assert result.get("classification") is None


async def test_capture_flow_multi_turn_reaches_generation() -> None:
    """Simula los turnos del happy path completo de captura.

    Las transiciones intermedias (free_capture→deep_dive,
    deep_dive→validation_summary, validation_summary→generation) usan
    `Command(goto=...)` y encadenan dentro del mismo turno — el usuario
    no manda mensajes sentinel.
    """
    gateway = _FakeGateway()
    repo = _FakeDocRepo()
    checkpointer = InMemorySaver()
    graph = build_graph(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
        checkpointer=checkpointer,
    )
    config = {"configurable": {"thread_id": "ses-multi"}}

    # Turno 0: arranque (solo welcome)
    initial = initial_state(
        session_id="ses-multi", user_id="oid-1", user_name="Andrés", mode="capture"
    )
    await graph.ainvoke(initial, config=config)

    # Turno 1: user manda el topic → identification corre
    await graph.ainvoke(
        {"messages": [{"role": "user", "content": "flaky tests en CI", "stage": None}]},
        config=config,
    )
    state_1 = await graph.aget_state(config)
    assert state_1.values["current_stage"] == "ETAPA_1"
    assert state_1.values["topic"] == "flaky tests en CI"
    assert state_1.values["classification"] is not None

    # Turno 2: user confirma clasificación → free_capture emite prompt
    await graph.ainvoke(
        {"messages": [{"role": "user", "content": "ok dale", "stage": None}]},
        config=config,
    )
    state_2 = await graph.aget_state(config)
    assert state_2.values["current_stage"] == "ETAPA_2"
    assert state_2.values["classification_confirmed"] is True
    assert state_2.values["awaiting_confirmation"] == "free_capture_more"

    # Turno 3: user manda contenido libre → free_capture guarda y Command-chain
    # delega a deep_dive en el mismo turno. State final: ETAPA_3.
    await graph.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Los flaky son tests intermitentes.",
                    "stage": None,
                }
            ]
        },
        config=config,
    )
    state_3 = await graph.aget_state(config)
    assert state_3.values["current_stage"] == "ETAPA_3"
    assert (
        "Los flaky son tests intermitentes." in state_3.values["free_capture_blocks"]
    )
    assert state_3.values["awaiting_confirmation"] == "deep_dive_answers"

    # Turno 4: user responde las preguntas dirigidas → deep_dive almacena y
    # Command-chain delega a validation_summary. State final: ETAPA_4.
    await graph.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "fue race condition, retry no funcionó",
                    "stage": None,
                }
            ]
        },
        config=config,
    )
    state_4 = await graph.aget_state(config)
    assert state_4.values["current_stage"] == "ETAPA_4"
    assert len(state_4.values["deep_dive_qa"]) == 1
    assert state_4.values["awaiting_confirmation"] == "summary"

    # Turno 5: user confirma el resumen → validation_summary marca validated
    # y Command-chain delega a generation. State final: ETAPA_5 con doc creado.
    await graph.ainvoke(
        {"messages": [{"role": "user", "content": "sí dale", "stage": None}]},
        config=config,
    )
    final = await graph.aget_state(config)
    assert final.values["current_stage"] == "ETAPA_5"
    assert final.values["summary_validated"] is True
    assert final.values["generated_document_id"] is not None
    # El repo recibió el doc
    assert len(repo.created) == 1
    # El gateway fue llamado para classify Y para score
    assert "classify" in gateway.calls
    assert "score" in gateway.calls


async def test_consultation_flow_invokes_consultation_node() -> None:
    """Modo B en 2.5: después de welcome, el dispatcher routea a `consultation`
    cuando el usuario manda su pregunta."""
    gateway = _FakeGateway()
    repo = _FakeDocRepo()
    graph = build_graph(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
        checkpointer=InMemorySaver(),
    )
    state = initial_state(
        session_id="ses-b", user_id="o", user_name="A", mode="consultation"
    )
    config = {"configurable": {"thread_id": "ses-b"}}

    # Turno 0: welcome
    await graph.ainvoke(state, config=config)
    # Turno 1: user pregunta → dispatcher routea a consultation
    await graph.ainvoke(
        {"messages": [{"role": "user", "content": "qué es flaky", "stage": None}]},
        config=config,
    )
    final = await graph.aget_state(config)
    agent_stages = [
        m.get("stage") for m in final.values["messages"] if m.get("role") == "agent"
    ]
    assert "ETAPA_0" in agent_stages
    assert "consult_search" in agent_stages
    assert final.values["current_query"] == "qué es flaky"


# ===========================================================================
# Reducer sanity
# ===========================================================================


def test_messages_field_has_reducer_for_concat() -> None:
    """Sanity: el campo messages tiene metadata Annotated con operator.add."""
    import operator
    from typing import get_type_hints

    hints = get_type_hints(AgentState, include_extras=True)
    msg_hint = hints["messages"]
    metadata = msg_hint.__metadata__
    assert operator.add in metadata
