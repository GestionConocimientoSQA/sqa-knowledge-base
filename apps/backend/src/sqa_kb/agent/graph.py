"""Construcción del grafo principal del agente (LangGraph).

Topología en 2.3 (subset del §16.3 del ROADMAP):

       START
         │
         ▼
      welcome ── (mode != capture) ──► END  (modos B y C en 2.5)
         │
         │ (mode == capture)
         ▼
    identification
         │
         ▼
        END  (pausa esperando user input — el orquestador SSE
              reanudará con el nuevo mensaje en 2.6)

Diseño:
- **Factory** `build_graph(...)`: el caller (lifespan del app o tests)
  pasa el `gateway`, `document_repo`, `checkpointer` ya inicializados.
- **`route_by_mode`** es un conditional edge desde welcome — decide qué
  rama tomar según `state.mode`.
- **Sin interrupts explícitos**: cada nodo setea `needs_user_input=True`
  y el grafo llega a END. El orquestador externo (2.6) lo reanuda con
  un nuevo `graph.ainvoke({"messages": [user_msg]}, config=...)` cuando
  llega un mensaje. El checkpointer restaura el state automáticamente.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from sqa_kb.agent.nodes import make_identification_node, make_welcome_node
from sqa_kb.agent.state import AgentState
from sqa_kb.ports.gateways import LlmGateway
from sqa_kb.ports.repositories import DocumentRepository

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph


# ===========================================================================
# Routing
# ===========================================================================


def _route_by_mode(state: AgentState) -> str:
    """Decide la rama post-welcome según el modo de la sesión.

    En 2.3 solo `capture` tiene rama implementada — `consultation` e
    `ingestion` van a END (Fase 2.5 los completa).
    """
    if state.mode == "capture":
        return "identification"
    # Modos B y C: pausa en END hasta que 2.5 implemente sus branches.
    return END


# ===========================================================================
# Builder
# ===========================================================================


def build_graph(
    *,
    gateway: LlmGateway,
    document_repo: DocumentRepository,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Construye y compila el grafo del agente.

    `checkpointer` opcional para tests unitarios — en runtime se pasa el
    `AsyncPostgresSaver` del lifespan del app.
    """
    graph = StateGraph(AgentState)

    # Nodos
    graph.add_node("welcome", make_welcome_node())
    graph.add_node(
        "identification",
        make_identification_node(gateway=gateway, document_repo=document_repo),
    )

    # Edges
    graph.add_edge(START, "welcome")
    graph.add_conditional_edges(
        "welcome",
        _route_by_mode,
        {
            "identification": "identification",
            END: END,
        },
    )
    graph.add_edge("identification", END)

    return graph.compile(checkpointer=checkpointer)
