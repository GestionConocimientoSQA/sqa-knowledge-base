"""Tests del grafo principal del agente (Fase 2.3).

Cubren:
- Compila sin checkpointer (in-memory por default de LangGraph).
- Route by mode: capture → identification, otros → END.
- Flujo end-to-end con LLM mockeado: START → welcome → identification.

Sin tocar Anthropic ni Postgres real.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from langgraph.checkpoint.memory import InMemorySaver

from sqa_kb.agent.graph import _route_by_mode, build_graph
from sqa_kb.agent.state import AgentState, initial_state
from sqa_kb.domain.entities import Document
from sqa_kb.domain.value_objects import CategoryCode, DocStatus, DocTypeCode
from sqa_kb.ports.gateways import ChatMessage, LlmCompletion

# ===========================================================================
# Fakes (compactos — los nodos ya tienen sus propios tests detallados)
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
    docs_to_return: list[Document]

    async def search(  # noqa: PLR0913
        self,
        *,
        query: str | None = None,
        carpetas: object = None,
        tipos: object = None,
        estados: object = None,
        autoritativo: object = None,
        anonimizado: object = None,
        min_score: object = None,
        date_from: object = None,
        date_to: object = None,
        author_oid: object = None,
        sort_by: object = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Document], int]:
        return list(self.docs_to_return), len(self.docs_to_return)


@dataclass
class _FakeGateway:
    response_text: str = (
        '{"category":"TEC","document_type":"MTEC",'
        '"confidence":0.8,"reasoning":"ok"}'
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
            text=self.response_text,
            input_tokens=1,
            output_tokens=1,
            cost_usd=0.0,
            model=model or "claude-sonnet-4-5",
        )

    async def stream(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError


# ===========================================================================
# route_by_mode
# ===========================================================================


def _state(mode: str) -> AgentState:
    return initial_state(
        session_id="s", user_id="o", user_name="n", mode=mode  # type: ignore[arg-type]
    )


def test_route_by_mode_capture() -> None:
    assert _route_by_mode(_state("capture")) == "identification"


def test_route_by_mode_consultation_goes_to_end() -> None:
    """Modo B aún no implementado en 2.3 — va a END."""
    from langgraph.graph import END

    assert _route_by_mode(_state("consultation")) == END


def test_route_by_mode_ingestion_goes_to_end() -> None:
    from langgraph.graph import END

    assert _route_by_mode(_state("ingestion")) == END


# ===========================================================================
# build_graph (compilación)
# ===========================================================================


def test_build_graph_compiles_without_checkpointer() -> None:
    gateway = _FakeGateway()
    repo = _FakeDocRepo(docs_to_return=[])
    graph = build_graph(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
    )
    assert graph is not None


def test_build_graph_compiles_with_in_memory_checkpointer() -> None:
    gateway = _FakeGateway()
    repo = _FakeDocRepo(docs_to_return=[])
    graph = build_graph(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
        checkpointer=InMemorySaver(),
    )
    assert graph is not None


# ===========================================================================
# End-to-end (capture mode flow)
# ===========================================================================


async def test_invoke_capture_mode_flows_welcome_then_identification() -> None:
    """Sesión nueva en modo capture con un user msg: welcome emite saludo,
    router va a identification, identification emite propuesta."""
    gateway = _FakeGateway()
    repo = _FakeDocRepo(docs_to_return=[])
    graph = build_graph(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
        checkpointer=InMemorySaver(),
    )

    initial = initial_state(
        session_id="ses-1", user_id="o", user_name="Andrés", mode="capture"
    )
    # Simulamos que el usuario ya mandó el topic.
    initial.messages = [
        {"role": "user", "content": "flaky tests en CI", "stage": None}
    ]
    config = {"configurable": {"thread_id": "ses-1"}}

    result = await graph.ainvoke(initial, config=config)

    # Final state debería tener:
    # - 2 mensajes nuevos: welcome (ETAPA_0) + identification (ETAPA_1).
    #   Más el user msg inicial → total 3.
    assert len(result["messages"]) >= 3
    stages = [m.get("stage") for m in result["messages"] if m.get("role") == "agent"]
    assert "ETAPA_0" in stages
    assert "ETAPA_1" in stages
    # Topic extraído
    assert result["topic"] == "flaky tests en CI"
    # Classification asignada
    assert result["classification"] is not None


async def test_invoke_consultation_mode_stops_after_welcome() -> None:
    """Modo B: 2.3 NO implementa consult_search → debería parar después de
    welcome sin entrar a identification."""
    gateway = _FakeGateway()
    repo = _FakeDocRepo(docs_to_return=[])
    graph = build_graph(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
        checkpointer=InMemorySaver(),
    )

    initial = initial_state(
        session_id="ses-2",
        user_id="o",
        user_name="A",
        mode="consultation",
    )
    config = {"configurable": {"thread_id": "ses-2"}}

    result = await graph.ainvoke(initial, config=config)

    # Solo welcome corrió (ETAPA_0) — identification NO.
    agent_msgs = [m for m in result["messages"] if m.get("role") == "agent"]
    stages = [m.get("stage") for m in agent_msgs]
    assert "ETAPA_0" in stages
    assert "ETAPA_1" not in stages


async def test_invoke_ingestion_mode_stops_after_welcome() -> None:
    gateway = _FakeGateway()
    repo = _FakeDocRepo(docs_to_return=[])
    graph = build_graph(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
        checkpointer=InMemorySaver(),
    )

    initial = initial_state(
        session_id="ses-3", user_id="o", user_name="A", mode="ingestion"
    )
    config = {"configurable": {"thread_id": "ses-3"}}

    result = await graph.ainvoke(initial, config=config)

    agent_msgs = [m for m in result["messages"] if m.get("role") == "agent"]
    stages = [m.get("stage") for m in agent_msgs]
    assert "ETAPA_0" in stages
    assert "ETAPA_1" not in stages


async def test_invoke_capture_with_duplicate_match_emits_duplicate_found() -> None:
    """Si el repo devuelve un doc, el stub linear le da distance=0.30 (<0.55).
    El nodo de identification debería emitir el mensaje de duplicate."""
    gateway = _FakeGateway()
    repo = _FakeDocRepo(docs_to_return=[_doc("TEC-x-2026-01-01")])
    graph = build_graph(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
        checkpointer=InMemorySaver(),
    )

    initial = initial_state(
        session_id="ses-4", user_id="o", user_name="A", mode="capture"
    )
    initial.messages = [{"role": "user", "content": "x", "stage": None}]
    config = {"configurable": {"thread_id": "ses-4"}}

    result = await graph.ainvoke(initial, config=config)

    assert result["awaiting_confirmation"] == "update_decision"
    # El mensaje de identification debería contener el filename del doc.
    agent_msgs = [m for m in result["messages"] if m.get("role") == "agent"]
    last_agent = agent_msgs[-1]
    assert "TEC-x-2026-01-01" in last_agent["content"]


async def test_invoke_capture_persists_state_to_checkpointer() -> None:
    """Después de ainvoke, el checkpointer debe tener un snapshot del state."""
    gateway = _FakeGateway()
    repo = _FakeDocRepo(docs_to_return=[])
    checkpointer = InMemorySaver()
    graph = build_graph(
        gateway=gateway,  # type: ignore[arg-type]
        document_repo=repo,  # type: ignore[arg-type]
        checkpointer=checkpointer,
    )

    initial = initial_state(
        session_id="ses-5", user_id="o", user_name="A", mode="capture"
    )
    initial.messages = [{"role": "user", "content": "topic", "stage": None}]
    config = {"configurable": {"thread_id": "ses-5"}}
    await graph.ainvoke(initial, config=config)

    saved = await checkpointer.aget_tuple(config)
    assert saved is not None
    # El checkpoint serializado debe incluir nuestro topic.
    assert "topic" in saved.checkpoint["channel_values"]


# ===========================================================================
# State reducer (operator.add para messages) sanity
# ===========================================================================


def test_messages_field_has_reducer_for_concat() -> None:
    """Sanity: el campo messages tiene metadata Annotated con operator.add."""
    import operator
    from typing import get_type_hints

    hints = get_type_hints(AgentState, include_extras=True)
    msg_hint = hints["messages"]
    # Annotated[list[...], operator.add] — el segundo elemento debe ser add.
    metadata = msg_hint.__metadata__
    assert operator.add in metadata
