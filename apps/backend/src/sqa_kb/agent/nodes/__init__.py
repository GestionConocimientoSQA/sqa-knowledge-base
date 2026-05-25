"""Nodos del grafo del agente.

Cada nodo es un *factory* (`make_<nombre>_node(...)`) que devuelve una
callable async compatible con LangGraph:

    async def node(state: AgentState) -> dict[str, Any] | Command: ...

Nodos por sub-fase:
- 2.3: welcome (ETAPA 0), identification (ETAPA 1).
- 2.4: free_capture (ETAPA 2), deep_dive (ETAPA 3),
  validation_summary (ETAPA 4), generation (ETAPA 5).
- 2.5: consultation (modo B), ingestion_classify + ingestion_traceability
  + index_ingestion (modo C, cadena).
"""

from sqa_kb.agent.nodes.consultation import make_consultation_node
from sqa_kb.agent.nodes.deep_dive import make_deep_dive_node
from sqa_kb.agent.nodes.free_capture import make_free_capture_node
from sqa_kb.agent.nodes.generation import make_generation_node
from sqa_kb.agent.nodes.identification import make_identification_node
from sqa_kb.agent.nodes.index_ingestion import make_index_ingestion_node
from sqa_kb.agent.nodes.ingestion_classify import make_ingestion_classify_node
from sqa_kb.agent.nodes.ingestion_traceability import (
    make_ingestion_traceability_node,
)
from sqa_kb.agent.nodes.validation_summary import make_validation_summary_node
from sqa_kb.agent.nodes.welcome import make_welcome_node

__all__ = [
    "make_consultation_node",
    "make_deep_dive_node",
    "make_free_capture_node",
    "make_generation_node",
    "make_identification_node",
    "make_index_ingestion_node",
    "make_ingestion_classify_node",
    "make_ingestion_traceability_node",
    "make_validation_summary_node",
    "make_welcome_node",
]
