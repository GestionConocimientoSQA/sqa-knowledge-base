"""Nodos del grafo del agente.

Cada nodo es un *factory* (`make_<nombre>_node(...)`) que devuelve una
callable async compatible con LangGraph:

    async def node(state: AgentState) -> dict[str, Any]: ...

El factory permite inyectar dependencias (LLM gateway, repos) sin
acoplarlas a un singleton global — los tests pasan fakes y el grafo se
arma en `graph.py` con las instancias reales.

Nodos por sub-fase:
- 2.3: welcome (ETAPA 0), identification (ETAPA 1).
- 2.4: free_capture (ETAPA 2), deep_dive (ETAPA 3),
  validation_summary (ETAPA 4), generation (ETAPA 5, cadena interna).
- 2.5: consult_search (modo B), synthesize_answer (modo B),
  ingestion_extract (modo C), classify_ingest (modo C), etc.
"""

from sqa_kb.agent.nodes.deep_dive import make_deep_dive_node
from sqa_kb.agent.nodes.free_capture import make_free_capture_node
from sqa_kb.agent.nodes.generation import make_generation_node
from sqa_kb.agent.nodes.identification import make_identification_node
from sqa_kb.agent.nodes.validation_summary import make_validation_summary_node
from sqa_kb.agent.nodes.welcome import make_welcome_node

__all__ = [
    "make_deep_dive_node",
    "make_free_capture_node",
    "make_generation_node",
    "make_identification_node",
    "make_validation_summary_node",
    "make_welcome_node",
]
