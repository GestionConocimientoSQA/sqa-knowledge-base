"""Construcción del grafo principal del agente (LangGraph).

Topología en 2.5 (cubre los 3 modos):

    START → stage_dispatcher → {
      welcome              (sin agent msg todavía)
      ┌── Modo A (capture)
      │   identification    (ETAPA 0 → 1)
      │   free_capture      (ETAPA 1 → 2)        ─┐ Command(goto)
      │   deep_dive         (ETAPA 2 → 3)        ─┤ chain en mismo turno
      │   validation_summary(ETAPA 3 → 4)        ─┤
      │   generation        (ETAPA 4 → 5, final) ─┘
      ├── Modo B (consultation)
      │   consultation      (single node, loop por turno)
      └── Modo C (ingestion)
          ingestion_classify       ─┐ chain
          ingestion_traceability   ─┤ Command(goto)
          index_ingestion          ─┘
    }

Cada nodo termina en END (una vuelta por invoke). El dispatcher routea
por `awaiting_confirmation` (source of truth de qué nodo está esperando
al usuario). Las transiciones intra-turno usan `Command(goto=...)`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from sqa_kb.agent.nodes import (
    make_consultation_node,
    make_deep_dive_node,
    make_free_capture_node,
    make_generation_node,
    make_identification_node,
    make_index_ingestion_node,
    make_ingestion_classify_node,
    make_ingestion_traceability_node,
    make_validation_summary_node,
    make_welcome_node,
)
from sqa_kb.agent.state import AgentState
from sqa_kb.ports.gateways import LlmGateway
from sqa_kb.ports.repositories import (
    DocumentRepository,
    IngestionRepository,
)

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph


# ===========================================================================
# Routing
# ===========================================================================


def _has_agent_msg(state: AgentState) -> bool:
    return any(m.get("role") == "agent" for m in state.messages)


# Modo A (capture): awaiting_confirmation → nodo.
_CAPTURE_AWAITING_TO_NODE: dict[str, str] = {
    "mode_choice": "identification",
    "topic": "identification",
    "classification": "free_capture",
    "update_decision": "free_capture",
    "free_capture_more": "free_capture",
    "deep_dive_answers": "deep_dive",
    "summary": "validation_summary",
}

# Modo B (consultation): awaiting → nodo.
_CONSULT_AWAITING_TO_NODE: dict[str, str] = {
    "mode_choice": "consultation",
    "consult_more": "consultation",
}

# Modo C (ingestion): awaiting → nodo.
_INGEST_AWAITING_TO_NODE: dict[str, str] = {
    "mode_choice": "ingestion_classify",
    "ingest_meta": "ingestion_traceability",
}


def _stage_dispatcher(state: AgentState) -> str:
    """Decide el próximo nodo según `mode` + `awaiting_confirmation`.

    - Sin agent msg → welcome (entrada inicial).
    - `awaiting=error` → END (sesión cerrada por error).
    - Por modo, mapeo awaiting → nodo. Si no matchea → END.

    Caso especial Modo A: stage=ETAPA_4 sin summary_validated y sin
    awaiting → re-emite el resumen (post-checkpoint resume edge).
    """
    if not _has_agent_msg(state):
        return "welcome"

    awaiting = state.awaiting_confirmation
    if awaiting == "error":
        return END

    if state.mode == "consultation":
        if awaiting is not None and awaiting in _CONSULT_AWAITING_TO_NODE:
            return _CONSULT_AWAITING_TO_NODE[awaiting]
        return END

    if state.mode == "ingestion":
        if awaiting is not None and awaiting in _INGEST_AWAITING_TO_NODE:
            return _INGEST_AWAITING_TO_NODE[awaiting]
        return END

    # Modo A — capture
    if awaiting is not None and awaiting in _CAPTURE_AWAITING_TO_NODE:
        return _CAPTURE_AWAITING_TO_NODE[awaiting]
    # Fallback: stage=ETAPA_4 sin validar → re-emite resumen.
    if state.current_stage == "ETAPA_4" and not state.summary_validated:
        return "validation_summary"
    return END


# Mapeo identidad — los nodos a los que el dispatcher salta directo. Los
# nodos alcanzados solo vía `Command(goto=...)` (generation, index_ingestion)
# NO van acá.
_DISPATCH_MAP = {
    "welcome": "welcome",
    "identification": "identification",
    "free_capture": "free_capture",
    "deep_dive": "deep_dive",
    "validation_summary": "validation_summary",
    "consultation": "consultation",
    "ingestion_classify": "ingestion_classify",
    "ingestion_traceability": "ingestion_traceability",
    END: END,
}


# ===========================================================================
# Builder
# ===========================================================================


def build_graph(
    *,
    gateway: LlmGateway,
    document_repo: DocumentRepository,
    ingestion_repo: IngestionRepository | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Construye y compila el grafo del agente.

    `ingestion_repo` es opcional para que tests de Modo A no necesiten
    inyectarlo. Si el grafo se invoca en modo C sin repo, el nodo
    `index_ingestion` falla con last_error.

    `checkpointer` opcional para tests unitarios — en runtime se pasa el
    `AsyncPostgresSaver` del lifespan.
    """
    graph = StateGraph(AgentState)

    # Modo A
    graph.add_node("welcome", make_welcome_node())
    graph.add_node(
        "identification",
        make_identification_node(gateway=gateway, document_repo=document_repo),
    )
    graph.add_node("free_capture", make_free_capture_node())
    graph.add_node("deep_dive", make_deep_dive_node())
    graph.add_node("validation_summary", make_validation_summary_node())
    graph.add_node(
        "generation",
        make_generation_node(gateway=gateway, document_repo=document_repo),
    )

    # Modo B
    graph.add_node(
        "consultation",
        make_consultation_node(gateway=gateway, document_repo=document_repo),
    )

    # Modo C
    graph.add_node(
        "ingestion_classify",
        make_ingestion_classify_node(gateway=gateway),
    )
    graph.add_node(
        "ingestion_traceability",
        make_ingestion_traceability_node(),
    )
    if ingestion_repo is not None:
        graph.add_node(
            "index_ingestion",
            make_index_ingestion_node(
                document_repo=document_repo, ingestion_repo=ingestion_repo
            ),
        )

    # Routing
    graph.add_conditional_edges(START, _stage_dispatcher, _DISPATCH_MAP)
    for node_name in (
        "welcome",
        "identification",
        "free_capture",
        "deep_dive",
        "validation_summary",
        "generation",
        "consultation",
        "ingestion_classify",
        "ingestion_traceability",
    ):
        graph.add_edge(node_name, END)
    if ingestion_repo is not None:
        graph.add_edge("index_ingestion", END)

    return graph.compile(checkpointer=checkpointer)
