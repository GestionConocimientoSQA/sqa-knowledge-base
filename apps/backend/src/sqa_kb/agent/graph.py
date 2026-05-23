"""Construcción del grafo principal del agente (LangGraph).

Topología en 2.4 (subset del §16.3 del ROADMAP):

    START
      │
      ▼
  stage_dispatcher  ── decide qué nodo correr según `current_stage` + `mode`
      │
      ├─► welcome              (sesión nueva, sin mensajes de agente)
      ├─► identification       (ETAPA_0 → ETAPA_1, modo capture)
      ├─► free_capture         (ETAPA_1 → ETAPA_2, después de confirmar clasificación)
      ├─► deep_dive            (ETAPA_2 → ETAPA_3, después de captura libre)
      ├─► validation_summary   (ETAPA_3 → ETAPA_4, después de respuestas dirigidas)
      ├─► generation           (ETAPA_4 → ETAPA_5, finaliza con score + index)
      └─► END                  (consult / ingest aún no implementados — Fase 2.5)

**Patrón**: cada nodo es "una vuelta del agente". Toda invocación nueva
del grafo entra por START, el dispatcher elige el nodo apropiado según el
estado restaurado del checkpointer, ese nodo emite su mensaje y termina
en END. El SSE orquestador (Fase 2.6) re-invoca con cada nuevo mensaje
del usuario.

`generation` es la única cadena interna (sin pause): emite el documento
generado, scorea y persiste de un tirón antes de cerrar la sesión.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from sqa_kb.agent.nodes import (
    make_deep_dive_node,
    make_free_capture_node,
    make_generation_node,
    make_identification_node,
    make_validation_summary_node,
    make_welcome_node,
)
from sqa_kb.agent.state import AgentState
from sqa_kb.ports.gateways import LlmGateway
from sqa_kb.ports.repositories import DocumentRepository

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph


# ===========================================================================
# Dispatcher
# ===========================================================================


def _has_agent_msg(state: AgentState) -> bool:
    return any(m.get("role") == "agent" for m in state.messages)


# Mapping: cuando un nodo emite un mensaje y queda esperando respuesta del
# usuario, el `awaiting_confirmation` indica qué nodo debe procesar la
# próxima entrada. Este es el routing principal del grafo turno a turno.
_AWAITING_TO_NODE: dict[str, str] = {
    "mode_choice": "identification",      # welcome → identificar topic
    "topic": "identification",            # identification preguntó el topic
    "classification": "free_capture",     # identification propuso → confirmar
    "update_decision": "free_capture",    # duplicate → decidir update/complement
    "free_capture_more": "free_capture",  # free_capture pidió contenido
    "deep_dive_answers": "deep_dive",     # deep_dive emitió preguntas
    "summary": "validation_summary",      # validation mostró resumen → confirmar
}


def _stage_dispatcher(state: AgentState) -> str:
    """Decide el próximo nodo según `awaiting_confirmation` (source of truth
    de qué nodo está esperando la entrada del usuario).

    Lógica:
    - Sin mensajes de agente todavía → `welcome` (entrada inicial).
    - Modos B/C: salimos a END en 2.4 (branches en 2.5).
    - `awaiting_confirmation` mapeado → ese nodo procesa la respuesta.
    - Sin awaiting (estado intermedio post-chain) → derivamos del stage:
      ETAPA_4 sin awaiting ⇒ summary ya fue validado, toca `generation`.
    - Cualquier otro caso → END (sesión cerrada o estado inesperado).
    """
    if not _has_agent_msg(state):
        return "welcome"

    if state.mode != "capture":
        return END

    awaiting = state.awaiting_confirmation
    if awaiting is not None and awaiting in _AWAITING_TO_NODE:
        return _AWAITING_TO_NODE[awaiting]
    if awaiting == "error":
        return END

    # Sin awaiting explícito: chequeamos si quedó algún stage pendiente.
    if state.current_stage == "ETAPA_4" and not state.summary_validated:
        return "validation_summary"

    return END


# Mapeo identidad — el dispatcher devuelve el nombre del nodo y LangGraph
# necesita el dict explícito en `add_conditional_edges`. Solo nodos a los
# que el dispatcher puede saltar directo (NO `generation`, que se alcanza
# vía `Command(goto=...)` desde `validation_summary`).
_DISPATCH_MAP = {
    "welcome": "welcome",
    "identification": "identification",
    "free_capture": "free_capture",
    "deep_dive": "deep_dive",
    "validation_summary": "validation_summary",
    END: END,
}


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
    graph.add_node("free_capture", make_free_capture_node())
    graph.add_node("deep_dive", make_deep_dive_node())
    graph.add_node("validation_summary", make_validation_summary_node())
    graph.add_node(
        "generation",
        make_generation_node(gateway=gateway, document_repo=document_repo),
    )

    # Routing: START → dispatcher → nodo correspondiente → END (una vuelta).
    graph.add_conditional_edges(START, _stage_dispatcher, _DISPATCH_MAP)
    graph.add_edge("welcome", END)
    graph.add_edge("identification", END)
    graph.add_edge("free_capture", END)
    graph.add_edge("deep_dive", END)
    graph.add_edge("validation_summary", END)
    graph.add_edge("generation", END)

    return graph.compile(checkpointer=checkpointer)
